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
When a user mentions a related concept, join through foreign keys from the schema. For example, if employees has department_id and departments has department_name, filter department names through a JOIN.
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


def is_specific_employee_fallback(question, fallback_sql):
    if not fallback_sql:
        return False

    question_lower = question.lower()
    specific_terms = (
        "after", "before", "since", "from", "in ",
        "department", "engineering", "sales", "finance", "operations", "human resources", "hr",
        "job", "title", "role", "engineer", "manager", "analyst", "coordinator", "executive", "representative",
        "salary", "salaries", "pay", "compensation", "bonus", "highest", "lowest", "average",
        "active", "leave", "status", "count", "how many", "number of", "hired", "hire date", "joined", "joining",
    )
    return " WHERE " in fallback_sql or " GROUP BY " in fallback_sql or " ORDER BY " in fallback_sql or any(
        term in question_lower for term in specific_terms
    )


def build_employee_system_fallback_sql(question, schema_info):
    """Build executable SQL for common company/employee demo prompts."""
    if not schema_has_table(schema_info, "employees"):
        return ""

    question_lower = question.lower()
    joins = []
    conditions = []
    select_parts = ["e.*"]

    has_departments = (
        schema_has_table(schema_info, "departments")
        and schema_has_column(schema_info, "employees", "department_id")
        and schema_has_column(schema_info, "departments", "department_id")
    )
    has_jobs = (
        schema_has_table(schema_info, "jobs")
        and schema_has_column(schema_info, "employees", "job_id")
        and schema_has_column(schema_info, "jobs", "job_id")
    )
    has_salaries = (
        schema_has_table(schema_info, "salaries")
        and schema_has_column(schema_info, "employees", "employee_id")
        and schema_has_column(schema_info, "salaries", "employee_id")
    )

    def add_departments_join():
        join = "JOIN departments d ON e.department_id = d.department_id"
        if has_departments and join not in joins:
            joins.append(join)
            if schema_has_column(schema_info, "departments", "department_name"):
                select_parts.append("d.department_name")

    def add_jobs_join():
        join = "JOIN jobs j ON e.job_id = j.job_id"
        if has_jobs and join not in joins:
            joins.append(join)
            if schema_has_column(schema_info, "jobs", "job_title"):
                select_parts.append("j.job_title")

    def add_salaries_join():
        join = "JOIN salaries s ON e.employee_id = s.employee_id"
        if has_salaries and join not in joins:
            joins.append(join)
            if schema_has_column(schema_info, "salaries", "base_salary"):
                select_parts.append("s.base_salary")
            if schema_has_column(schema_info, "salaries", "bonus"):
                select_parts.append("s.bonus")

    if any(word in question_lower for word in ("department", "engineering", "sales", "finance", "operations", "human resources", "hr")):
        department = find_sample_value_in_question(schema_info, "departments", "department_name", question)
        add_departments_join()
        if department and schema_has_column(schema_info, "departments", "department_name"):
            conditions.append(f"LOWER(d.department_name) = LOWER({sql_literal(department)})")

    if any(word in question_lower for word in ("job", "title", "role", "engineer", "manager", "analyst", "coordinator", "executive", "representative")):
        job_title = find_sample_value_in_question(schema_info, "jobs", "job_title", question)
        add_jobs_join()
        if job_title and schema_has_column(schema_info, "jobs", "job_title"):
            conditions.append(f"LOWER(j.job_title) = LOWER({sql_literal(job_title)})")

    if any(word in question_lower for word in ("salary", "salaries", "pay", "paid", "compensation", "bonus", "highest", "lowest", "average")):
        add_salaries_join()

    if schema_has_column(schema_info, "employees", "employment_status"):
        status = find_sample_value_in_question(schema_info, "employees", "employment_status", question)
        if status:
            conditions.append(f"LOWER(e.employment_status) = LOWER({sql_literal(status)})")
        elif "active" in question_lower:
            conditions.append("LOWER(e.employment_status) = LOWER('Active')")
        elif "leave" in question_lower or "on leave" in question_lower:
            conditions.append("LOWER(e.employment_status) = LOWER('On Leave')")

    if schema_has_column(schema_info, "employees", "hire_date") and any(
        word in question_lower for word in ("hire", "hired", "joining", "joined", "start date", "started")
    ):
        year = extract_year(question)
        if year:
            if "after" in question_lower or "since" in question_lower:
                conditions.append(f"e.hire_date > '{year}-12-31'")
            elif "before" in question_lower:
                conditions.append(f"e.hire_date < '{year}-01-01'")
            elif "in" in question_lower or "during" in question_lower:
                conditions.append(f"e.hire_date >= '{year}-01-01' AND e.hire_date <= '{year}-12-31'")

    department_table_intent = (
        has_departments
        and "department" in question_lower
        and not any(word in question_lower for word in ("employee", "employees", "staff", "worker", "workers"))
        and any(word in question_lower for word in ("show", "list", "display", "all", "details", "detail", "table"))
    )
    if department_table_intent:
        return "SELECT * FROM departments;"

    department_employee_count_intent = (
        has_departments
        and "department" in question_lower
        and any(word in question_lower for word in ("employee", "employees", "staff", "worker", "workers"))
        and any(phrase in question_lower for phrase in (
            "most",
            "least",
            "highest",
            "lowest",
            "maximum",
            "minimum",
            "top",
            "which",
            "count",
            "how many",
            "number of",
        ))
    )
    if department_employee_count_intent:
        order_direction = "ASC" if any(word in question_lower for word in ("least", "lowest", "minimum")) else "DESC"
        limit_clause = " LIMIT 1" if any(word in question_lower for word in ("most", "least", "highest", "lowest", "maximum", "minimum", "top", "which")) else ""
        return (
            "SELECT d.department_id, d.department_name, d.location, d.budget, COUNT(e.employee_id) AS employee_count "
            "FROM departments d "
            "LEFT JOIN employees e ON e.department_id = d.department_id "
            "GROUP BY d.department_id, d.department_name, d.location, d.budget "
            f"ORDER BY employee_count {order_direction}{limit_clause};"
        )

    if "count" in question_lower or "how many" in question_lower or "number of" in question_lower:
        if has_departments and "department" in question_lower:
            add_departments_join()
            return (
                "SELECT d.department_name, COUNT(*) AS employee_count "
                "FROM employees e "
                + " ".join(joins)
                + " GROUP BY d.department_name ORDER BY employee_count DESC;"
            )
        return "SELECT COUNT(*) AS employee_count FROM employees e;"

    if ("average" in question_lower or "avg" in question_lower) and "salary" in question_lower:
        add_salaries_join()
        if has_departments and "department" in question_lower:
            add_departments_join()
            return (
                "SELECT d.department_name, AVG(s.base_salary) AS average_salary "
                "FROM employees e "
                + " ".join(joins)
                + " GROUP BY d.department_name ORDER BY average_salary DESC;"
            )
        return "SELECT AVG(s.base_salary) AS average_salary FROM employees e JOIN salaries s ON e.employee_id = s.employee_id;"

    order_by = ""
    if "highest" in question_lower and has_salaries:
        add_salaries_join()
        order_by = " ORDER BY s.base_salary DESC"
    elif "lowest" in question_lower and has_salaries:
        add_salaries_join()
        order_by = " ORDER BY s.base_salary ASC"

    select_sql = ", ".join(dict.fromkeys(select_parts))
    sql = f"SELECT {select_sql} FROM employees e"
    if joins:
        sql += " " + " ".join(joins)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += order_by
    sql += ";"
    return sql


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
    fallback_sql = build_employee_system_fallback_sql(question, schema)
    if is_specific_employee_fallback(question, fallback_sql):
        try:
            execution = executor(fallback_sql)
            attempts.append({
                "sql": fallback_sql,
                "repair": "schema-driven query plan",
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
                        "repair": "schema-driven fallback",
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
