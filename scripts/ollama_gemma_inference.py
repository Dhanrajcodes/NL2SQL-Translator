"""
Inference script for using Gemma3 1B model via Ollama for NL2SQL task
"""

import ollama
import json
import re

def format_prompt(question):
    """
    Format the prompt for Gemma3 to convert NL to SQL
    
    Args:
        question (str): Natural language question
        
    Returns:
        str: Formatted prompt
    """
    prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid SQL query.

Examples:
Natural Language: Show all employees in the Sales department.
SQL: SELECT * FROM employees WHERE department = 'Sales';

Natural Language: List the names of students who scored more than 90.
SQL: SELECT name FROM students WHERE score > 90;

Natural Language: Find the total salary of all employees.
SQL: SELECT SUM(salary) FROM employees;

Natural Language: {question}
SQL:"""
    
    return prompt

def generate_sql_ollama(question, model_name="gemma3:1b"):
    """
    Generate SQL using Ollama Gemma3 model
    
    Args:
        question (str): Natural language question
        model_name (str): Name of the Ollama model to use
        
    Returns:
        str: Generated SQL query
    """
    try:
        # Format the prompt
        prompt = format_prompt(question)
        
        # Generate response using Ollama
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.3,  # Low temperature for more deterministic results
                "top_p": 0.9,
                "stop": ["\n\n", ";"]
            }
        )
        
        # Extract the SQL from the response
        sql_query = response['response'].strip()
        
        # Clean up the SQL query
        # Remove any extra text before the SQL
        sql_lines = sql_query.split('\n')
        cleaned_lines = []
        for line in sql_lines:
            if line.strip() and not line.startswith('#') and not line.startswith('--'):
                cleaned_lines.append(line)
        
        if cleaned_lines:
            sql_query = cleaned_lines[0].strip()
        
        # Ensure it ends with semicolon
        if not sql_query.endswith(';'):
            sql_query += ';'
            
        return sql_query
    
    except Exception as e:
        print(f"Error generating SQL with Ollama: {e}")
        return "SELECT * FROM table_name WHERE condition;"

def test_model():
    """
    Test the model with sample questions
    """
    test_questions = [
        "Show all employees with salary above 50000",
        "Get list of users from user table",
        "Find the average salary of all employees",
        "Count the number of customers in each city",
        "List all employees who work in either HR or Marketing"
    ]
    
    print("Testing Gemma3 1B model with Ollama for NL2SQL task")
    print("=" * 60)
    
    for question in test_questions:
        print(f"\nNatural Language: {question}")
        sql = generate_sql_ollama(question)
        print(f"Generated SQL: {sql}")
        print("-" * 40)

def interactive_mode():
    """
    Interactive mode to test the model
    """
    print("Interactive NL2SQL with Gemma3 1B (via Ollama)")
    print("Type 'quit' to exit")
    print("=" * 50)
    
    while True:
        question = input("\nEnter your natural language query: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not question:
            continue
            
        sql = generate_sql_ollama(question)
        print(f"Generated SQL: {sql}")

if __name__ == "__main__":
    # Test the model
    test_model()
    
    # Uncomment the line below for interactive mode
    # interactive_mode()