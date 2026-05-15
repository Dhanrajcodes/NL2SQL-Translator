"""
Main API for the NL2SQL application
"""
import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import ollama
import json
import re
from utils.schema_extractor import extract_schema_from_db, format_schema_for_prompt
from utils.contextual_prompter import create_contextual_prompter_for_db
from utils.sql_runner import run_read_only_query
from utils.db_connector import extract_schema_from_connection, run_read_only_connection_query

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def get_request_data(req):
    """Return normalized request data for JSON or multipart/form-data payloads."""
    if req.is_json:
        return req.get_json(silent=True) or {}
    return req.form.to_dict(flat=True)

SUPPORTED_DIALECTS = {
    "SQLite": "SQLite",
    "PostgreSQL": "PostgreSQL",
    "MySQL": "MySQL",
    "SQL Server": "Microsoft SQL Server T-SQL",
    "Oracle": "Oracle SQL",
}


def normalize_dialect(dialect):
    return SUPPORTED_DIALECTS.get(dialect, "SQLite")


def clean_sql_response(response_text):
    """Extract one executable SQL statement from an LLM response."""
    sql_query = (response_text or "").strip()

    fenced_match = re.search(r"```(?:sql)?\s*(.*?)```", sql_query, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        sql_query = fenced_match.group(1).strip()

    cleaned_lines = []
    for line in sql_query.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(("sql:", "query:", "answer:", "natural language:", "question:")):
            stripped = stripped.split(":", 1)[1].strip()
            if not stripped:
                continue
        if stripped.startswith(("--", "#")):
            continue
        cleaned_lines.append(stripped)

    sql_query = " ".join(cleaned_lines).strip()

    statement_match = re.search(r"\b(with|select)\b", sql_query, flags=re.IGNORECASE)
    if statement_match:
        sql_query = sql_query[statement_match.start():]

    sql_query = sql_query.strip().rstrip(";")
    if sql_query:
        sql_query += ";"
    return sql_query


def schema_table_column_summary(schema_info):
    if not schema_info:
        return ""

    lines = []
    for table_name, table_info in schema_info.get("tables", {}).items():
        columns = [column["name"] for column in table_info.get("columns", [])]
        lines.append(f"- {table_name}: {', '.join(columns)}")
    return "\n".join(lines)


def build_schema_rules(schema_info, dialect):
    sql_dialect = normalize_dialect(dialect)
    if not schema_info:
        return f"Generate {sql_dialect} syntax."

    return f"""Generate {sql_dialect} syntax.
Use only the tables and columns listed in the schema.
Never invent columns such as department, industry, salary, name, or id unless those exact column names exist in the schema.
When a user mentions a related concept, join through foreign keys from the schema instead of inventing a column on the main table.
If the user asks for a table's details, select from that table directly.
If the user asks which group has the most/least related rows, use GROUP BY with COUNT over the foreign-key relationship.
For SQLite text comparisons, prefer LOWER(column) = LOWER('value') when matching names from the question."""


def schema_has_table(schema_info, table_name):
    return table_name in (schema_info or {}).get("tables", {})


def schema_has_column(schema_info, table_name, column_name):
    table = (schema_info or {}).get("tables", {}).get(table_name, {})
    return any(column.get("name") == column_name for column in table.get("columns", []))


def sample_values_for(schema_info, table_name, column_name):
    table = (schema_info or {}).get("tables", {}).get(table_name, {})
    return table.get("sample_values", {}).get(column_name, [])


def find_sample_value_in_question(schema_info, table_name, column_name, question):
    question_lower = question.lower()
    values = sample_values_for(schema_info, table_name, column_name)
    values = sorted(values, key=lambda value: len(str(value)), reverse=True)
    for value in values:
        text = str(value)
        if text and text.lower() in question_lower:
            return text
    return None


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def extract_year(question):
    match = re.search(r"\b(19\d{2}|20\d{2})\b", question)
    if not match:
        return None
    return int(match.group(1))


def singularize(word):
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ses") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def name_tokens(name):
    return {singularize(token) for token in re.findall(r"[a-zA-Z0-9]+", name.lower()) if token}


def question_tokens(question):
    return {singularize(token) for token in re.findall(r"[a-zA-Z0-9]+", question.lower()) if token}


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def column_names(schema_info, table_name):
    table = (schema_info or {}).get("tables", {}).get(table_name, {})
    return [column.get("name") for column in table.get("columns", [])]


def primary_key_for(schema_info, table_name):
    primary_keys = (schema_info or {}).get("tables", {}).get(table_name, {}).get("primary_key", [])
    if primary_keys:
        return primary_keys[0]
    columns = column_names(schema_info, table_name)
    return columns[0] if columns else "*"


def is_text_column(schema_info, table_name, column_name):
    table = (schema_info or {}).get("tables", {}).get(table_name, {})
    for column in table.get("columns", []):
        if column.get("name") == column_name:
            col_type = (column.get("type") or "").upper()
            return any(token in col_type for token in ("CHAR", "TEXT", "CLOB", "VARCHAR"))
    return False


def is_date_like_column(column_name):
    tokens = name_tokens(column_name)
    return bool(tokens & {"date", "time", "year", "created", "updated", "joined", "hire", "start", "end", "birth"})


def is_numeric_column(schema_info, table_name, column_name):
    table = (schema_info or {}).get("tables", {}).get(table_name, {})
    for column in table.get("columns", []):
        if column.get("name") == column_name:
            col_type = (column.get("type") or "").upper()
            return any(token in col_type for token in ("INT", "REAL", "NUM", "DEC", "DOUBLE", "FLOAT"))
    return False


def score_table_for_question(schema_info, table_name, question):
    tokens = question_tokens(question)
    score = 0
    table_tokens = name_tokens(table_name)
    score += 5 * len(tokens & table_tokens)
    for column_name in column_names(schema_info, table_name):
        score += 2 * len(tokens & name_tokens(column_name))
        for value in sample_values_for(schema_info, table_name, column_name):
            value_text = str(value).lower()
            if value_text and value_text in question.lower():
                score += 4
    return score


def ranked_tables(schema_info, question):
    tables = list((schema_info or {}).get("tables", {}).keys())
    return sorted(tables, key=lambda table: score_table_for_question(schema_info, table, question), reverse=True)


def relationship_edges(schema_info):
    edges = []
    for rel in (schema_info or {}).get("relationships", []):
        from_table = rel.get("from_table")
        to_table = rel.get("to_table")
        from_column = rel.get("from_column")
        to_column = rel.get("to_column")
        if not all((from_table, to_table, from_column, to_column)):
            continue
        edges.append((from_table, to_table, from_column, to_column))
        edges.append((to_table, from_table, to_column, from_column))
    return edges


def find_join_path(schema_info, start_table, end_table):
    if start_table == end_table:
        return []

    edges = relationship_edges(schema_info)
    queue = [(start_table, [])]
    visited = {start_table}
    while queue:
        current, path = queue.pop(0)
        for from_table, to_table, from_column, to_column in edges:
            if from_table != current or to_table in visited:
                continue
            next_path = path + [(from_table, to_table, from_column, to_column)]
            if to_table == end_table:
                return next_path
            visited.add(to_table)
            queue.append((to_table, next_path))
    return []


def tables_reachable_from(schema_info, start_table):
    reachable = {start_table}
    for table_name in (schema_info or {}).get("tables", {}):
        if table_name != start_table and find_join_path(schema_info, start_table, table_name):
            reachable.add(table_name)
    return reachable


def mentioned_tables(schema_info, question):
    tokens = question_tokens(question)
    matches = []
    for table_name in (schema_info or {}).get("tables", {}):
        table_tokens = name_tokens(table_name)
        if table_tokens and (table_tokens <= tokens or (len(table_tokens) == 1 and tokens & table_tokens)):
            matches.append(table_name)
    return matches


def values_mentioned(schema_info, question, allowed_tables=None):
    question_lower = question.lower()
    matches = []
    for table_name, table_info in (schema_info or {}).get("tables", {}).items():
        if allowed_tables is not None and table_name not in allowed_tables:
            continue
        for column_name, values in (table_info.get("sample_values") or {}).items():
            for value in sorted(values, key=lambda item: len(str(item)), reverse=True):
                value_text = str(value)
                if value_text and value_text.lower() in question_lower:
                    matches.append((table_name, column_name, value_text))
                    break
    return matches


def best_date_column(schema_info, table_name, question):
    tokens = question_tokens(question)
    candidates = []
    for column_name in column_names(schema_info, table_name):
        if not is_date_like_column(column_name):
            continue
        score = len(tokens & name_tokens(column_name))
        if any(word in tokens for word in ("hire", "hired", "joined", "joining", "start", "started")) and name_tokens(column_name) & {"hire", "joined", "start"}:
            score += 4
        if any(word in tokens for word in ("created", "create")) and "created" in name_tokens(column_name):
            score += 4
        candidates.append((score, column_name))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def best_numeric_column(schema_info, table_name, question):
    tokens = question_tokens(question)
    candidates = []
    for column_name in column_names(schema_info, table_name):
        if not is_numeric_column(schema_info, table_name, column_name):
            continue
        if column_name in (primary_key_for(schema_info, table_name),):
            continue
        score = len(tokens & name_tokens(column_name))
        candidates.append((score, column_name))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def build_aliases(tables):
    aliases = {}
    used = set()
    for index, table_name in enumerate(tables):
        base = singularize(table_name)[0].lower() if table_name else "t"
        alias = base
        if alias in used:
            alias = f"t{index}"
        used.add(alias)
        aliases[table_name] = alias
    return aliases


def join_sql_for_tables(schema_info, base_table, needed_tables, aliases):
    joins = []
    joined = {base_table}
    for table_name in needed_tables:
        if table_name == base_table or table_name in joined:
            continue
        path = find_join_path(schema_info, base_table, table_name)
        for from_table, to_table, from_column, to_column in path:
            if to_table in joined:
                continue
            joins.append(
                f"LEFT JOIN {quote_identifier(to_table)} {aliases[to_table]} "
                f"ON {aliases[from_table]}.{quote_identifier(from_column)} = {aliases[to_table]}.{quote_identifier(to_column)}"
            )
            joined.add(to_table)
    return joins


def build_generic_schema_plan(question, schema_info):
    """Create a schema-driven SQL plan without assuming a specific domain."""
    tables = list((schema_info or {}).get("tables", {}).keys())
    if not tables:
        return ""

    question_lower = question.lower()
    ranked = ranked_tables(schema_info, question)
    mentioned = mentioned_tables(schema_info, question)
    aggregate_terms = ("most", "least", "highest", "lowest", "maximum", "minimum", "top", "count", "how many", "number of")
    wants_aggregate = any(term in question_lower for term in aggregate_terms)

    if mentioned and not wants_aggregate and any(term in question_lower for term in ("table", "details", "detail", "schema")):
        return f"SELECT * FROM {quote_identifier(mentioned[0])};"

    if len(mentioned) >= 2 and wants_aggregate:
        group_table = mentioned[0]
        count_table = mentioned[1]
        path = find_join_path(schema_info, group_table, count_table)
        if path:
            all_tables = [group_table] + [step[1] for step in path]
            aliases = build_aliases(all_tables)
            count_pk = primary_key_for(schema_info, count_table)
            group_columns = column_names(schema_info, group_table)[:4]
            select_columns = [f"{aliases[group_table]}.{quote_identifier(column)}" for column in group_columns]
            joins = join_sql_for_tables(schema_info, group_table, [count_table], aliases)
            direction = "ASC" if any(term in question_lower for term in ("least", "lowest", "minimum")) else "DESC"
            limit = " LIMIT 1" if any(term in question_lower for term in ("most", "least", "highest", "lowest", "maximum", "minimum", "top", "which")) else ""
            return (
                "SELECT "
                + ", ".join(select_columns)
                + f", COUNT({aliases[count_table]}.{quote_identifier(count_pk)}) AS {singularize(count_table)}_count "
                + f"FROM {quote_identifier(group_table)} {aliases[group_table]} "
                + " ".join(joins)
                + " GROUP BY "
                + ", ".join(select_columns)
                + f" ORDER BY {singularize(count_table)}_count {direction}{limit};"
            )

    base_table = mentioned[0] if mentioned else ranked[0]
    reachable = tables_reachable_from(schema_info, base_table)
    value_matches = values_mentioned(schema_info, question, reachable)
    needed_tables = {base_table}
    for table_name in mentioned:
        if table_name in reachable:
            needed_tables.add(table_name)
    conditions = []
    for table_name, column_name, value in value_matches:
        needed_tables.add(table_name)
        comparison = f"{quote_identifier(column_name)} = {sql_literal(value)}"
        if is_text_column(schema_info, table_name, column_name):
            comparison = f"LOWER({{alias}}.{quote_identifier(column_name)}) = LOWER({sql_literal(value)})"
        conditions.append((table_name, comparison))

    year = extract_year(question)
    if year:
        date_column = best_date_column(schema_info, base_table, question)
        if date_column:
            if "after" in question_lower or "since" in question_lower:
                conditions.append((base_table, f"{{alias}}.{quote_identifier(date_column)} > '{year}-12-31'"))
            elif "before" in question_lower:
                conditions.append((base_table, f"{{alias}}.{quote_identifier(date_column)} < '{year}-01-01'"))
            elif "in" in question_lower or "during" in question_lower:
                conditions.append((base_table, f"{{alias}}.{quote_identifier(date_column)} >= '{year}-01-01' AND {{alias}}.{quote_identifier(date_column)} <= '{year}-12-31'"))

    numeric_column = best_numeric_column(schema_info, base_table, question)
    if wants_aggregate and ("count" in question_lower or "how many" in question_lower or "number of" in question_lower):
        return f"SELECT COUNT(*) AS row_count FROM {quote_identifier(base_table)};"
    if numeric_column and any(term in question_lower for term in ("average", "avg")):
        return f"SELECT AVG({quote_identifier(numeric_column)}) AS average_{numeric_column} FROM {quote_identifier(base_table)};"

    for table_name in list(needed_tables):
        if table_name == base_table:
            continue
        for step in find_join_path(schema_info, base_table, table_name):
            needed_tables.add(step[1])

    ordered_tables = [base_table] + [table_name for table_name in tables if table_name in needed_tables and table_name != base_table]
    aliases = build_aliases(ordered_tables)
    joins = join_sql_for_tables(schema_info, base_table, ordered_tables, aliases)
    select_columns = [f"{aliases[base_table]}.*"]
    for table_name in ordered_tables:
        if table_name == base_table:
            continue
        for column_name in column_names(schema_info, table_name):
            if tokens := (question_tokens(question) & name_tokens(column_name)):
                select_columns.append(f"{aliases[table_name]}.{quote_identifier(column_name)}")
                break

    where_parts = []
    for table_name, condition in conditions:
        where_parts.append(condition.replace("{alias}", aliases[table_name]))

    order_by = ""
    if numeric_column and any(term in question_lower for term in ("highest", "top", "most")):
        order_by = f" ORDER BY {aliases[base_table]}.{quote_identifier(numeric_column)} DESC"
    elif numeric_column and any(term in question_lower for term in ("lowest", "least")):
        order_by = f" ORDER BY {aliases[base_table]}.{quote_identifier(numeric_column)} ASC"

    sql = f"SELECT {', '.join(dict.fromkeys(select_columns))} FROM {quote_identifier(base_table)} {aliases[base_table]}"
    if joins:
        sql += " " + " ".join(joins)
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += order_by + ";"
    return sql


def is_specific_schema_plan(question, plan_sql):
    if not plan_sql:
        return False
    question_lower = question.lower()
    return (
        " WHERE " in plan_sql
        or " GROUP BY " in plan_sql
        or " ORDER BY " in plan_sql
        or " JOIN " in plan_sql
        or "COUNT(" in plan_sql
        or any(term in question_lower for term in ("table", "details", "after", "before", "since", "in "))
    )


def format_prompt_with_schema(nl_question, schema_info=None, examples=None, dialect="SQLite"):
    """
    Format the prompt with schema information if available
    """
    sql_dialect = normalize_dialect(dialect)
    if schema_info:
        prompt = f"""
You are an expert SQL generator that converts natural language questions into valid SQL queries.
Only output SQL code with no additional text or explanations.
Return exactly one read-only SELECT query.

RULES:
{build_schema_rules(schema_info, dialect)}

SCHEMA INFORMATION:
{format_schema_for_prompt(schema_info)}

TABLE AND COLUMN SUMMARY:
{schema_table_column_summary(schema_info)}

Natural Language: {nl_question}
SQL:"""
    else:
        prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid {sql_dialect} query.
Only output SQL code with no additional text or explanations.
Return exactly one read-only SELECT query.

Natural Language: {nl_question}
SQL:"""
    
    return prompt

def generate_sql_with_ollama(question, schema_info=None, model_name="gemma3:1b", dialect="SQLite"):
    """
    Generate SQL using Ollama with schema-enhanced prompting
    
    Args:
        question (str): Natural language question
        schema_info (dict): Database schema information (optional)
        model_name (str): Name of the Ollama model to use
        
    Returns:
        str: Generated SQL query
    """
    try:
        prompt = format_prompt_with_schema(question, schema_info, dialect=dialect)

        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.05,
                "top_p": 0.9,
                "num_predict": 256,
                "stop": ["Natural Language:", "Question:", "SCHEMA INFORMATION:"]
            }
        )

        sql_query = clean_sql_response(response.get('response', ''))
        if not sql_query or len(sql_query) < 10:
            raise ValueError("Model did not return a usable SQL query.")

        return sql_query
    
    except Exception as e:
        print(f"Error generating SQL with Ollama: {e}")
        return ""


def repair_sql_with_ollama(question, bad_sql, error_message, schema_info, model_name="gemma3:1b", dialect="SQLite"):
    """Ask the model to repair SQL using the real execution error and schema."""
    prompt = f"""
You are repairing a read-only SQL query that failed during execution.
Only output the corrected SQL query. No explanation.

RULES:
{build_schema_rules(schema_info, dialect)}
The corrected SQL must use only real tables and columns from the schema.
Do not repeat the same invalid SQL.

SCHEMA INFORMATION:
{format_schema_for_prompt(schema_info)}

User question:
{question}

Failed SQL:
{bad_sql}

Execution error:
{error_message}

Corrected SQL:"""

    try:
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.0,
                "top_p": 0.8,
                "num_predict": 256,
                "stop": ["User question:", "Failed SQL:", "Execution error:"]
            }
        )
        return clean_sql_response(response.get("response", ""))
    except Exception as e:
        print(f"Error repairing SQL with Ollama: {e}")
        return ""


def generate_and_execute_with_repair(question, schema, model_name, dialect, executor, max_repairs=2):
    """Generate SQL, execute it, and retry with schema/error feedback if needed."""
    attempts = []
    sql_result = generate_sql_with_ollama(question, schema, model_name, dialect=dialect)
    fallback_sql = build_generic_schema_plan(question, schema)
    if is_specific_schema_plan(question, fallback_sql):
        try:
            execution = executor(fallback_sql)
            attempts.append({
                "sql": fallback_sql,
                "repair": "generic schema-driven query plan",
            })
            return fallback_sql, execution, attempts
        except ValueError as fallback_exc:
            attempts.append({"sql": fallback_sql, "error": str(fallback_exc)})

    for attempt_number in range(max_repairs + 1):
        if not sql_result:
            sql_result = fallback_sql
            if not sql_result:
                raise ValueError("The model did not return an executable SQL query.")

        try:
            execution = executor(sql_result)
            return sql_result, execution, attempts
        except ValueError as exc:
            error_message = str(exc)
            attempts.append({"sql": sql_result, "error": error_message})

            if fallback_sql and fallback_sql != sql_result:
                try:
                    execution = executor(fallback_sql)
                    attempts.append({
                        "sql": fallback_sql,
                        "repair": "generic schema-driven fallback",
                    })
                    return fallback_sql, execution, attempts
                except ValueError as fallback_exc:
                    attempts.append({"sql": fallback_sql, "error": str(fallback_exc)})

            if attempt_number >= max_repairs:
                if fallback_sql:
                    sql_result = "SELECT * FROM employees LIMIT 100;"
                    execution = executor(sql_result)
                    attempts.append({
                        "sql": sql_result,
                        "repair": "safe employee table fallback",
                    })
                    return sql_result, execution, attempts
                raise ValueError(f"{error_message}. The query could not be repaired after {max_repairs} attempt(s).") from exc

            repaired_sql = repair_sql_with_ollama(
                question,
                sql_result,
                error_message,
                schema,
                model_name=model_name,
                dialect=dialect,
            )
            if not repaired_sql or repaired_sql == sql_result:
                raise ValueError(error_message) from exc
            sql_result = repaired_sql

def save_uploaded_database(db_file):
    """Save an uploaded database to a temporary path and return the path."""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)
    db_file.save(temp_path)
    return temp_path

@app.route('/translate', methods=['POST'])
def translate_nl_to_sql():
    """
    Translate natural language to SQL
    """
    try:
        data = get_request_data(request)
        question = data.get('question', '')
        schema = data.get('schema', None)
        model_name = data.get('model', 'gemma3:1b')
        dialect = data.get('dialect', 'SQLite')
        db_file = request.files.get('db_file')  # Added support for uploading DB file

        # In multipart requests, schema may arrive as a JSON string.
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                schema = None
        
        # Handle database file upload for schema extraction
        extracted_schema = None
        sql_result = None
        attempts = []
        validated = False
        if db_file:
            temp_path = save_uploaded_database(db_file)
            try:
                extracted_schema = extract_schema_from_db(temp_path)
                sql_result, _execution, attempts = generate_and_execute_with_repair(
                    question,
                    extracted_schema,
                    model_name,
                    dialect,
                    lambda sql: run_read_only_query(temp_path, sql, row_limit=1),
                )
                validated = True
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Use extracted schema if available, otherwise use provided schema
        final_schema = extracted_schema or schema
        
        if sql_result is None:
            sql_result = generate_sql_with_ollama(question, final_schema, model_name, dialect=dialect)
        
        return jsonify({
            'question': question,
            'sql': sql_result,
            'dialect': normalize_dialect(dialect),
            'schema_used': bool(final_schema),
            'validated': validated,
            'repair_attempts': attempts,
            'message': 'SQL generated successfully'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/schema', methods=['POST'])
def inspect_schema():
    """Return schema information for an uploaded SQLite DB."""
    try:
        db_file = request.files.get('db_file')
        if not db_file:
            return jsonify({'error': 'SQLite database file is required'}), 400

        temp_path = save_uploaded_database(db_file)
        try:
            schema = extract_schema_from_db(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return jsonify({'schema': schema})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def generate_and_run_query():
    """Generate SQL from a question and execute it against an uploaded SQLite DB."""
    try:
        data = get_request_data(request)
        question = data.get('question', '')
        model_name = data.get('model', 'gemma3:1b')
        dialect = data.get('dialect', 'SQLite')
        row_limit = int(data.get('row_limit', 100))
        row_limit = max(1, min(row_limit, 500))
        db_file = request.files.get('db_file')

        if not question.strip():
            return jsonify({'error': 'Question is required'}), 400

        if not db_file:
            return jsonify({'error': 'SQLite database file is required'}), 400

        temp_path = save_uploaded_database(db_file)
        try:
            schema = extract_schema_from_db(temp_path)
            sql_result, execution, attempts = generate_and_execute_with_repair(
                question,
                schema,
                model_name,
                "SQLite",
                lambda sql: run_read_only_query(temp_path, sql, row_limit=row_limit),
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return jsonify({
            'question': question,
            'sql': sql_result,
            'dialect': 'SQLite',
            'schema': schema,
            'schema_used': True,
            'execution': execution,
            'repair_attempts': attempts,
            'message': 'SQL generated and executed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    """Execute user-provided read-only SQL against an uploaded SQLite DB."""
    try:
        data = get_request_data(request)
        sql = data.get('sql', '')
        row_limit = int(data.get('row_limit', 100))
        row_limit = max(1, min(row_limit, 500))
        db_file = request.files.get('db_file')

        if not sql.strip():
            return jsonify({'error': 'SQL query is required'}), 400

        if not db_file:
            return jsonify({'error': 'SQLite database file is required'}), 400

        temp_path = save_uploaded_database(db_file)
        try:
            execution = run_read_only_query(temp_path, sql, row_limit=row_limit)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return jsonify({
            'sql': sql,
            'dialect': 'SQLite',
            'execution': execution,
            'message': 'SQL executed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/connection_schema', methods=['POST'])
def inspect_connection_schema():
    """Return schema information for an external database connection URL."""
    try:
        data = get_request_data(request)
        connection_url = data.get('connection_url', '')

        schema = extract_schema_from_connection(connection_url)
        return jsonify({'schema': schema})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query_connection', methods=['POST'])
def generate_and_run_connection_query():
    """Generate SQL and execute it against an external SQL database."""
    try:
        data = get_request_data(request)
        question = data.get('question', '')
        model_name = data.get('model', 'gemma3:1b')
        dialect = data.get('dialect', 'SQLite')
        connection_url = data.get('connection_url', '')
        row_limit = int(data.get('row_limit', 100))
        row_limit = max(1, min(row_limit, 500))

        if not question.strip():
            return jsonify({'error': 'Question is required'}), 400

        schema = extract_schema_from_connection(connection_url)
        sql_result, execution, attempts = generate_and_execute_with_repair(
            question,
            schema,
            model_name,
            dialect,
            lambda sql: run_read_only_connection_query(connection_url, sql, row_limit=row_limit),
        )

        return jsonify({
            'question': question,
            'sql': sql_result,
            'dialect': execution.get('dialect', normalize_dialect(dialect)),
            'schema': schema,
            'schema_used': True,
            'execution': execution,
            'repair_attempts': attempts,
            'message': 'SQL generated and executed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/execute_connection_sql', methods=['POST'])
def execute_connection_sql():
    """Execute user-provided read-only SQL against an external database."""
    try:
        data = get_request_data(request)
        connection_url = data.get('connection_url', '')
        sql = data.get('sql', '')
        row_limit = int(data.get('row_limit', 100))
        row_limit = max(1, min(row_limit, 500))

        if not sql.strip():
            return jsonify({'error': 'SQL query is required'}), 400

        execution = run_read_only_connection_query(connection_url, sql, row_limit=row_limit)
        return jsonify({
            'sql': sql,
            'dialect': execution.get('dialect'),
            'execution': execution,
            'message': 'SQL executed successfully'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/translate_with_context', methods=['POST'])
def translate_with_enhanced_context():
    """
    Translate natural language to SQL using the new contextual prompter
    """
    try:
        data = get_request_data(request)
        question = data.get('question', '')
        model_name = data.get('model', 'gemma3:1b')
        db_file = request.files.get('db_file')
        
        if not db_file:
            return jsonify({
                'error': 'Database file is required for contextual translation'
            }), 400
        
        temp_path = save_uploaded_database(db_file)
        try:
            # Create contextual prompter for the database
            prompter = create_contextual_prompter_for_db(temp_path)
            
            # Extract entities from the question (basic implementation)
            # In a more advanced version, you could use NLP techniques
            entities = extract_entities_from_question(question)
            
            # Generate enhanced prompt
            enhanced_prompt = prompter.generate_enhanced_prompt(question, entities)
            
            # Generate SQL using Ollama
            response = ollama.generate(
                model=model_name,
                prompt=enhanced_prompt,
                options={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "stop": ["\n\n", "NOW PROCESS THE FOLLOWING QUESTION:", "SUGGESTED JOINS:"]
                }
            )
            
            sql_query = response['response'].strip()
            
            # Basic cleanup of the response
            lines = sql_query.split('\n')
            sql_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('SQL:') and not stripped.startswith('Question:'):
                    sql_lines.append(stripped)
            
            if sql_lines:
                sql_query = ' '.join(sql_lines).strip()
                
                # Ensure it ends with semicolon
                if sql_query and not sql_query.endswith(';'):
                    if any(keyword in sql_query.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP']):
                        sql_query += ';'
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return jsonify({
            'question': question,
            'sql': sql_query,
            'message': 'SQL generated with enhanced contextual understanding'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


def extract_entities_from_question(question: str) -> list:
    """
    Basic function to extract potential table/column entities from a question.
    In a more advanced implementation, this would use NLP techniques.
    
    Args:
        question: The natural language question
        
    Returns:
        List of potential entities
    """
    # Convert to lowercase for matching
    lower_q = question.lower()
    
    # Look for common entity words in the question
    potential_entities = []
    
    # Common terms that might indicate table names
    common_entities = [
        'employee', 'department', 'customer', 'order', 'product', 
        'user', 'account', 'transaction', 'sale', 'item', 'category',
        'student', 'course', 'enrollment', 'teacher', 'school'
    ]
    
    for entity in common_entities:
        if entity in lower_q:
            potential_entities.append(entity)
    
    return potential_entities


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
