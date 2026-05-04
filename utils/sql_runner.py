"""Safe SQLite query execution helpers."""

import sqlite3
import time
from pathlib import Path
from typing import Any


READ_ONLY_PREFIXES = ("select", "with")
BLOCKED_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
)


def is_read_only_sql(sql: str) -> bool:
    normalized = " ".join(sql.strip().lower().split())
    if not normalized:
        return False

    first_word = normalized.split(" ", 1)[0]
    if first_word not in READ_ONLY_PREFIXES:
        return False

    if ";" in normalized.rstrip(";"):
        return False

    padded = f" {normalized} "
    return not any(f" {keyword} " in padded for keyword in BLOCKED_KEYWORDS)


def run_read_only_query(db_path: str | Path, sql: str, row_limit: int = 100) -> dict[str, Any]:
    if not is_read_only_sql(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")

    query = sql.strip().rstrip(";")
    limited_query = f"SELECT * FROM ({query}) AS generated_query LIMIT ?"

    conn = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        started_at = time.perf_counter()
        cursor = conn.execute(limited_query, (row_limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        columns = [description[0] for description in cursor.description or []]
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "row_limit": row_limit,
            "elapsed_ms": elapsed_ms,
        }
    except sqlite3.Error as exc:
        raise ValueError(f"SQLite execution error: {exc}") from exc
    finally:
        conn.close()
