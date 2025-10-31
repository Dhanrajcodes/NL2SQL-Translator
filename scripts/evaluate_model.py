"""
Script to evaluate the NL2SQL model performance
"""

import json
import os
import re
from tqdm import tqdm
import ollama

def calculate_exact_match(predicted, actual):
    """
    Calculate exact match accuracy between predicted and actual SQL queries
    
    Args:
        predicted (str): Predicted SQL query
        actual (str): Actual SQL query
        
    Returns:
        bool: True if exact match, False otherwise
    """
    # Normalize both queries by removing extra whitespace and converting to lowercase
    pred_normalized = re.sub(r'\s+', ' ', predicted.strip().lower())
    actual_normalized = re.sub(r'\s+', ' ', actual.strip().lower())
    
    return pred_normalized == actual_normalized

def calculate_bleu_score(predicted, actual):
    """
    Calculate a simple BLEU-like score between predicted and actual SQL queries
    
    Args:
        predicted (str): Predicted SQL query
        actual (str): Actual SQL query
        
    Returns:
        float: BLEU score (simplified)
    """
    # Tokenize by splitting on whitespace and common SQL delimiters
    pred_tokens = re.findall(r'\w+|[^\w\s]', predicted.lower())
    actual_tokens = re.findall(r'\w+|[^\w\s]', actual.lower())
    
    # For simplicity, we'll use a basic n-gram matching approach
    if not actual_tokens:
        return 0.0
    
    # Count matching tokens
    matching_tokens = sum(1 for token in pred_tokens if token in actual_tokens)
    total_tokens = len(actual_tokens)
    
    return matching_tokens / total_tokens if total_tokens > 0 else 0.0

def format_enhanced_prompt(question, schema_info=None, examples=None):
    """
    Format an enhanced prompt for better SQL generation
    
    Args:
        question (str): Natural language question
        schema_info (dict): Database schema information
        examples (list): List of example question-SQL pairs
        
    Returns:
        str: Enhanced prompt
    """
    prompt = "You are an expert SQL generator that converts natural language questions into valid SQL queries.\n"
    prompt += "You should only output SQL code and nothing else. Do not include explanations or markdown formatting.\n\n"
    
    # Add examples if provided
    if examples:
        prompt += "Examples:\n"
        for example in examples:
            prompt += f"Natural Language: {example['question']}\n"
            prompt += f"SQL: {example['sql']}\n\n"
    
    # Add schema information if provided
    if schema_info:
        prompt += "Database Schema:\n"
        for table_name, table_info in schema_info.items():
            prompt += f"Table: {table_name}\n"
            prompt += "Columns:\n"
            for column in table_info.get('columns', []):
                prompt += f"  - {column['name']} ({column['type']})\n"
            if 'foreign_keys' in table_info:
                prompt += "Foreign Keys:\n"
                for fk in table_info['foreign_keys']:
                    prompt += f"  - {fk}\n"
        prompt += "\n"
    
    prompt += f"Natural Language: {question}\n"
    prompt += "SQL:"
    
    return prompt

def generate_sql_with_ollama(question, schema_info=None):
    """
    Generate SQL from natural language question using Ollama Gemma3 model with enhanced prompting
    
    Args:
        question (str): Natural language question
        schema_info (dict): Database schema information (optional)
        
    Returns:
        str: Generated SQL query
    """
    try:
        # Sample examples for few-shot learning
        examples = [
            {
                "question": "Show all employees in the Sales department.",
                "sql": "SELECT * FROM employees WHERE department = 'Sales';"
            },
            {
                "question": "List the names of students who scored more than 90.",
                "sql": "SELECT name FROM students WHERE score > 90;"
            },
            {
                "question": "Find the total salary of all employees.",
                "sql": "SELECT SUM(salary) FROM employees;"
            }
        ]
        
        # Format the enhanced prompt
        prompt = format_enhanced_prompt(question, schema_info, examples)
        
        # Generate response using Ollama
        response = ollama.generate(
            model="gemma3:1b",
            prompt=prompt,
            options={
                "temperature": 0.2,  # Low temperature for more deterministic results
                "top_p": 0.9,
                "stop": ["\n\n"]
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

def load_test_data():
    """
    Load test data from available datasets
    
    Returns:
        list: List of test examples
    """
    test_examples = []
    
    # Check for Spider dev dataset
    spider_dev_path = 'data/spider/dev.json'
    if os.path.exists(spider_dev_path):
        with open(spider_dev_path, 'r') as f:
            spider_dev = json.load(f)
            # Limit to first 10 examples for demo
            for item in spider_dev[:10]:
                test_examples.append({
                    'question': item['question'],
                    'sql': item['query']
                })
        print(f"Loaded {len(test_examples)} examples from Spider dev set")
    
    # If no Spider data, use sample data
    if not test_examples:
        test_examples = [
            {
                "question": "Show all employees with salary above 50000",
                "sql": "SELECT * FROM employee WHERE salary > 50000;"
            },
            {
                "question": "List all departments",
                "sql": "SELECT * FROM department;"
            },
            {
                "question": "Find the average salary of all employees",
                "sql": "SELECT AVG(salary) FROM employee;"
            }
        ]
        print("Using sample test data")
    
    return test_examples

def evaluate_model():
    """
    Evaluate the model performance
    """
    print("Evaluating NL2SQL Model Performance")
    print("=" * 40)
    
    # Load test data
    test_data = load_test_data()
    
    # Initialize metrics
    exact_matches = 0
    total_bleu_score = 0
    total_examples = len(test_data)
    
    # Sample schema for testing
    schema_info = {
        "employee": {
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "department", "type": "TEXT"},
                {"name": "salary", "type": "INTEGER"}
            ]
        },
        "department": {
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "budget", "type": "INTEGER"}
            ]
        }
    }
    
    print(f"\nEvaluating {total_examples} examples...")
    
    # Evaluate each example
    for i, example in enumerate(tqdm(test_data, desc="Evaluating")):
        question = example['question']
        actual_sql = example['sql']
        
        # Generate SQL using our model
        predicted_sql = generate_sql_with_ollama(question, schema_info)
        
        # Calculate metrics
        if calculate_exact_match(predicted_sql, actual_sql):
            exact_matches += 1
        
        bleu_score = calculate_bleu_score(predicted_sql, actual_sql)
        total_bleu_score += bleu_score
        
        # Print first few examples for inspection
        if i < 3:
            print(f"\nExample {i+1}:")
            print(f"Question: {question}")
            print(f"Actual SQL: {actual_sql}")
            print(f"Predicted SQL: {predicted_sql}")
            print(f"Exact Match: {calculate_exact_match(predicted_sql, actual_sql)}")
            print(f"BLEU Score: {bleu_score:.3f}")
    
    # Calculate final metrics
    exact_match_accuracy = exact_matches / total_examples if total_examples > 0 else 0
    avg_bleu_score = total_bleu_score / total_examples if total_examples > 0 else 0
    
    print(f"\nEvaluation Results:")
    print(f"Total Examples: {total_examples}")
    print(f"Exact Match Accuracy: {exact_match_accuracy:.3f} ({exact_matches}/{total_examples})")
    print(f"Average BLEU Score: {avg_bleu_score:.3f}")
    
    # Save results to file
    results = {
        "total_examples": total_examples,
        "exact_match_accuracy": exact_match_accuracy,
        "exact_matches": exact_matches,
        "average_bleu_score": avg_bleu_score
    }
    
    with open('evaluation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to evaluation_results.json")
    return results

def main():
    """
    Main function to run evaluation
    """
    try:
        results = evaluate_model()
        print("\nEvaluation completed successfully!")
    except Exception as e:
        print(f"Error during evaluation: {e}")

if __name__ == "__main__":
    main()