"""
Script to fine-tune the Gemma3 model via Ollama using the downloaded datasets
"""

import json
import os
import ollama
from tqdm import tqdm

def load_training_data():
    """
    Load training data from available datasets
    """
    training_examples = []
    
    # Check for Spider dataset
    spider_path = 'data/spider_train.json'
    if os.path.exists(spider_path):
        with open(spider_path, 'r') as f:
            spider_data = json.load(f)
            training_examples.extend(spider_data)
        print(f"Loaded {len(spider_data)} examples from Spider dataset")
    
    # Check for WikiSQL dataset
    wikisql_path = 'data/wikisql_train.json'
    if os.path.exists(wikisql_path):
        with open(wikisql_path, 'r') as f:
            wikisql_data = json.load(f)
            training_examples.extend(wikisql_data)
        print(f"Loaded {len(wikisql_data)} examples from WikiSQL dataset")
    
    # Add some sample data if no datasets are available
    if not training_examples:
        training_examples = [
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
            },
            {
                "question": "Count the number of employees in each department",
                "sql": "SELECT department, COUNT(*) FROM employee GROUP BY department;"
            }
        ]
        print("Using sample training data")
    
    print(f"Total training examples: {len(training_examples)}")
    return training_examples

def format_training_prompt(example):
    """
    Format a training example as a prompt for the model
    """
    prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid SQL query.

Examples:
Natural Language: Show all employees in the Sales department.
SQL: SELECT * FROM employees WHERE department = 'Sales';

Natural Language: List the names of students who scored more than 90.
SQL: SELECT name FROM students WHERE score > 90;

Natural Language: Find the total salary of all employees.
SQL: SELECT SUM(salary) FROM employees;

Natural Language: {example['question']}
SQL:"""
    
    return prompt

def create_finetuning_dataset(training_examples, output_file='data/finetuning_dataset.jsonl'):
    """
    Create a dataset for fine-tuning in the format expected by Ollama
    """
    print("Creating fine-tuning dataset...")
    
    with open(output_file, 'w') as f:
        for example in tqdm(training_examples, desc="Processing examples"):
            prompt = format_training_prompt(example)
            completion = example['sql']
            
            # Format as JSONL for Ollama
            item = {
                "prompt": prompt,
                "response": completion
            }
            f.write(json.dumps(item) + '\n')
    
    print(f"Fine-tuning dataset created: {output_file}")
    return output_file

def main():
    print("NL2SQL Fine-tuning with Ollama Gemma3")
    print("=" * 40)
    
    # Load training data
    training_examples = load_training_data()
    
    # Create fine-tuning dataset
    dataset_file = create_finetuning_dataset(training_examples)
    
    print("\nTo fine-tune your Gemma3 model with this dataset:")
    print("1. Make sure Ollama is running")
    print("2. Use the following command:")
    print(f"   ollama create gemma3-nl2sql -f {dataset_file}")
    print("\nOr for a more complete Modelfile approach, create a Modelfile with:")
    print("FROM gemma3:1b")
    print(f"ADAPTER {dataset_file}")
    
    # Test the model with a sample
    print("\nTesting current model...")
    try:
        response = ollama.generate(
            model="gemma3:1b",
            prompt="Convert this natural language query to SQL: Show all employees with salary above 50000",
            options={
                "temperature": 0.2,
                "top_p": 0.9
            }
        )
        print(f"Sample output: {response['response']}")
    except Exception as e:
        print(f"Error testing model: {e}")

if __name__ == "__main__":
    main()