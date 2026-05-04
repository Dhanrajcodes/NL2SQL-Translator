"""Database connection helpers for external SQL databases."""

from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from utils.sql_runner import is_read_only_sql


SUPPORTED_CONNECTION_DIALECTS = {
    "sqlite": "SQLite",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL/MariaDB",
    "mariadb": "MySQL/MariaDB",
    "mssql": "SQL Server",
    "oracle": "Oracle",
}


def create_db_engine(connection_url: str) -> Engine:
    if not connection_url.strip():
        raise ValueError("Database connection URL is required.")

    engine = create_engine(connection_url, pool_pre_ping=True)
    dialect_name = engine.dialect.name.lower()
    if dialect_name not in SUPPORTED_CONNECTION_DIALECTS:
        supported = ", ".join(sorted(set(SUPPORTED_CONNECTION_DIALECTS.values())))
        raise ValueError(f"Unsupported database dialect '{dialect_name}'. Supported: {supported}.")

    return engine


def extract_schema_from_connection(connection_url: str) -> dict[str, Any]:
    engine = create_db_engine(connection_url)
    inspector = inspect(engine)

    schema = {
        "database_type": SUPPORTED_CONNECTION_DIALECTS.get(engine.dialect.name, engine.dialect.name),
        "tables": {},
        "relationships": [],
    }

    try:
        table_names = inspector.get_table_names()

        for table_name in table_names:
            columns = []
            primary_key = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            foreign_keys_raw = inspector.get_foreign_keys(table_name)

            for column in inspector.get_columns(table_name):
                columns.append(
                    {
                        "name": column["name"],
                        "type": str(column.get("type", "")),
                        "nullable": column.get("nullable", True),
                        "default_value": str(column.get("default")) if column.get("default") is not None else None,
                        "primary_key": column["name"] in primary_key,
                    }
                )

            foreign_keys = []
            for index, fk in enumerate(foreign_keys_raw):
                referred_table = fk.get("referred_table")
                referred_columns = fk.get("referred_columns") or []
                constrained_columns = fk.get("constrained_columns") or []

                for from_column, to_column in zip(constrained_columns, referred_columns):
                    foreign_keys.append(
                        {
                            "id": index,
                            "from_column": from_column,
                            "to_table": referred_table,
                            "to_column": to_column,
                        }
                    )
                    schema["relationships"].append(
                        {
                            "from_table": table_name,
                            "from_column": from_column,
                            "to_table": referred_table,
                            "to_column": to_column,
                            "type": "many-to-one",
                        }
                    )

            schema["tables"][table_name] = {
                "name": table_name,
                "columns": columns,
                "foreign_keys": foreign_keys,
                "primary_key": primary_key,
            }

        return schema
    finally:
        engine.dispose()


def run_read_only_connection_query(
    connection_url: str,
    sql: str,
    row_limit: int = 100,
) -> dict[str, Any]:
    if not is_read_only_sql(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")

    engine = create_db_engine(connection_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql.strip().rstrip(";")))
            rows = [dict(row._mapping) for row in result.fetchmany(row_limit)]
            columns = list(result.keys())
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "row_limit": row_limit,
                "dialect": SUPPORTED_CONNECTION_DIALECTS.get(engine.dialect.name, engine.dialect.name),
            }
    except Exception as exc:
        raise ValueError(f"Database execution error: {exc}") from exc
    finally:
        engine.dispose()
