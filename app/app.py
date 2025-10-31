"""
Flask Backend for NL2SQL System
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import ollama
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def create_prompt(question, schema=None):
    """
    Create an enhanced prompt for the SQL generation task
    """
    prompt = f"Convert this natural language question to a SQL query:\nQuestion: {question}\n\n"
    
    if schema:
        prompt += "Database Schema:\n"
        for table_name, table_info in schema.items():
            prompt += f"Table: {table_name}\n"
            for column in table_info.get("columns", []):
                prompt += f"  - {column['name']} ({column['type']})\n"
        prompt += "\n"
    
    prompt += "SQL Query:"
    return prompt

def extract_sql_from_response(response_text):
    """
    Extract SQL query from the model response
    """
    # Remove any markdown code block indicators
    response_text = re.sub(r'```sql\s*', '', response_text, flags=re.IGNORECASE)
    response_text = re.sub(r'```', '', response_text)
    
    # Extract the SQL query (everything up to the first empty line or end of text)
    lines = response_text.strip().split('\n')
    sql_lines = []
    for line in lines:
        if line.strip() == '' and sql_lines:
            break
        sql_lines.append(line)
    
    sql_query = '\n'.join(sql_lines).strip()
    
    # Ensure the query ends with a semicolon
    if sql_query and not sql_query.endswith(';'):
        sql_query += ';'
    
    return sql_query

@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.get_json()
        question = data.get('question')
        schema = data.get('schema')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Create the prompt
        prompt = create_prompt(question, schema)
        
        # Use the enhanced model
        model = "gemma3-nl2sql"
        
        # Generate SQL using Ollama
        response = ollama.generate(model=model, prompt=prompt)
        
        # Extract SQL from response
        sql_query = extract_sql_from_response(response['response'])
        
        return jsonify({
            'sql_query': sql_query,
            'model_used': model
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)