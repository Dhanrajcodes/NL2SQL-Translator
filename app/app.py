"""
Main API for the NL2SQL application
"""
import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import ollama
import sqlite3
import json
from utils.schema_extractor import extract_schema_from_db, format_schema_for_prompt
from utils.contextual_prompter import create_contextual_prompter_for_db
from utils.relationship_mapper import create_relationship_mapper_for_db

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def get_request_data(req):
    """Return normalized request data for JSON or multipart/form-data payloads."""
    if req.is_json:
        return req.get_json(silent=True) or {}
    return req.form.to_dict(flat=True)

def format_prompt_with_schema(nl_question, schema_info=None, examples=None):
    """
    Format the prompt with schema information if available
    """
    if schema_info:
        # Use the enhanced schema-aware prompt
        prompt = f"""
You are an expert SQL generator that converts natural language questions into valid SQL queries.
Only output SQL code with no additional text or explanations.

SCHEMA INFORMATION:
{format_schema_for_prompt(schema_info)}

EXAMPLES:
Natural Language: Show all employees in the Sales department.
SQL: SELECT * FROM employees WHERE department = 'Sales';

Natural Language: List the names of students who scored more than 90.
SQL: SELECT name FROM students WHERE score > 90;

Natural Language: Find the total salary of all employees.
SQL: SELECT SUM(salary) FROM employees;

Natural Language: {nl_question}
SQL:"""
    else:
        # Fallback to basic prompt
        prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid SQL query.

Examples:
Natural Language: Show all employees in the Sales department.
SQL: SELECT * FROM employees WHERE department = 'Sales';

Natural Language: List the names of students who scored more than 90.
SQL: SELECT name FROM students WHERE score > 90;

Natural Language: Find the total salary of all employees.
SQL: SELECT SUM(salary) FROM employees;

Natural Language: {nl_question}
SQL:"""
    
    return prompt

def generate_sql_with_ollama(question, schema_info=None, model_name="gemma3:1b"):
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
        # Format the prompt with schema information if available
        prompt = format_prompt_with_schema(question, schema_info)
        
        # Generate response using Ollama
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.2,  # Low temperature for more deterministic results
                "top_p": 0.9,
                "stop": ["\n\n", "Natural Language:", "Examples:", "SCHEMA INFORMATION:"]
            }
        )
        
        # Extract and clean the SQL query
        sql_query = response['response'].strip()
        
        # Remove markdown code blocks if present
        if "```sql" in sql_query:
            parts = sql_query.split("```sql")
            if len(parts) > 1:
                sql_part = parts[1].split("```")[0].strip()
                sql_query = sql_part
        elif sql_query.startswith("```"):
            lines = sql_query.split("\n")
            code_lines = [line for line in lines if not line.startswith("```")]
            if code_lines:
                sql_query = "\n".join(code_lines).strip()
        
        # Clean up extra whitespace
        lines = [line.strip() for line in sql_query.split("\n") if line.strip()]
        if lines:
            sql_query = " ".join(lines)
        
        # Ensure it ends with semicolon
        if sql_query and not sql_query.endswith(';'):
            if any(keyword in sql_query.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP']):
                sql_query += ';'
        
        # Validate that we have a reasonable SQL query
        if not sql_query or len(sql_query) < 10:
            return "SELECT * FROM table_name WHERE condition;"
            
        return sql_query
    
    except Exception as e:
        print(f"Error generating SQL with Ollama: {e}")
        return "SELECT * FROM table_name WHERE condition;"

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
        db_file = request.files.get('db_file')  # Added support for uploading DB file

        # In multipart requests, schema may arrive as a JSON string.
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                schema = None
        
        # Handle database file upload for schema extraction
        extracted_schema = None
        if db_file:
            # Save uploaded file temporarily
            temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
            try:
                db_file.save(temp_path)
                # Extract schema from uploaded database
                extracted_schema = extract_schema_from_db(temp_path)
            finally:
                os.close(temp_fd)
                os.remove(temp_path)
        
        # Use extracted schema if available, otherwise use provided schema
        final_schema = extracted_schema or schema
        
        # Generate SQL using Ollama with enhanced prompting
        sql_result = generate_sql_with_ollama(question, final_schema, model_name)
        
        return jsonify({
            'question': question,
            'sql': sql_result,
            'schema_used': bool(final_schema),
            'message': 'SQL generated successfully'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

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
        
        # Save uploaded file temporarily
        temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
        try:
            db_file.save(temp_path)
            
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
            os.close(temp_fd)
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