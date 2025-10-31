"""
Few-shot learning component for NL2SQL
"""

import json
import random
from typing import List, Dict, Tuple

class FewShotNL2SQL:
    """
    Few-shot learning component for NL2SQL translation
    """
    
    def __init__(self, examples_file: str = None):
        """
        Initialize the few-shot component
        
        Args:
            examples_file (str): Path to file with example pairs
        """
        self.examples = []
        if examples_file:
            self.load_examples(examples_file)
    
    def load_examples(self, examples_file: str):
        """
        Load example pairs from file
        
        Args:
            examples_file (str): Path to examples file
        """
        try:
            with open(examples_file, 'r') as f:
                data = json.load(f)
                self.examples = data if isinstance(data, list) else [data]
        except FileNotFoundError:
            print(f"Examples file {examples_file} not found.")
        except json.JSONDecodeError:
            print(f"Error parsing JSON in {examples_file}")
    
    def add_example(self, question: str, sql: str):
        """
        Add an example pair to the collection
        
        Args:
            question (str): Natural language question
            sql (str): Corresponding SQL query
        """
        self.examples.append({
            "question": question,
            "sql": sql
        })
    
    def get_examples(self, n: int = 3) -> List[Dict]:
        """
        Get n random examples
        
        Args:
            n (int): Number of examples to return
            
        Returns:
            List[Dict]: List of example pairs
        """
        if len(self.examples) <= n:
            return self.examples
        return random.sample(self.examples, n)
    
    def format_prompt(self, question: str, n_examples: int = 3) -> str:
        """
        Format a prompt with examples for few-shot learning
        
        Args:
            question (str): Question to translate
            n_examples (int): Number of examples to include
            
        Returns:
            str: Formatted prompt
        """
        examples = self.get_examples(n_examples)
        
        prompt = "Translate natural language to SQL:\n\n"
        
        # Add examples
        for example in examples:
            prompt += f"Question: {example['question']}\n"
            prompt += f"SQL: {example['sql']}\n\n"
        
        # Add the target question
        prompt += f"Question: {question}\n"
        prompt += "SQL:"
        
        return prompt
    
    def generate_sql(self, question: str, n_examples: int = 3) -> str:
        """
        Generate SQL using few-shot approach (mock implementation)
        
        Args:
            question (str): Natural language question
            n_examples (int): Number of examples to include
            
        Returns:
            str: Generated SQL query
        """
        # In a real implementation, this would use an LLM
        # For demonstration, we'll use rule-based approach
        
        # Format the prompt (for display purposes)
        prompt = self.format_prompt(question, n_examples)
        
        # Simple rule-based translation for demonstration
        question_lower = question.lower()
        
        if "show all" in question_lower and "salary" in question_lower and "above" in question_lower:
            return "SELECT * FROM employees WHERE salary > 50000;"
        elif "show all" in question_lower and "employees" in question_lower:
            return "SELECT * FROM employees;"
        elif "count" in question_lower and "employees" in question_lower:
            return "SELECT COUNT(*) FROM employees;"
        elif "average" in question_lower and "salary" in question_lower:
            return "SELECT AVG(salary) FROM employees;"
        elif "list" in question_lower and "departments" in question_lower:
            return "SELECT * FROM departments;"
        else:
            # Default query pattern
            return "SELECT * FROM table_name WHERE condition;"
    
    def save_examples(self, filename: str):
        """
        Save examples to file
        
        Args:
            filename (str): Path to save examples
        """
        with open(filename, 'w') as f:
            json.dump(self.examples, f, indent=2)

def create_sample_examples():
    """
    Create sample examples for demonstration
    """
    examples = [
        {
            "question": "Show all employees with salary above 50000",
            "sql": "SELECT * FROM employees WHERE salary > 50000;"
        },
        {
            "question": "List all departments",
            "sql": "SELECT * FROM departments;"
        },
        {
            "question": "Count the number of employees",
            "sql": "SELECT COUNT(*) FROM employees;"
        },
        {
            "question": "What is the average salary of employees?",
            "sql": "SELECT AVG(salary) FROM employees;"
        },
        {
            "question": "Find employees in the IT department",
            "sql": "SELECT * FROM employees WHERE department = 'IT';"
        }
    ]
    
    with open("../data/sample_examples.json", 'w') as f:
        json.dump(examples, f, indent=2)
    
    print("Sample examples saved to ../data/sample_examples.json")

def main():
    """
    Main function to demonstrate few-shot component
    """
    print("Few-Shot NL2SQL Component")
    print("========================")
    
    # Create sample examples
    create_sample_examples()
    
    # Initialize few-shot component
    few_shot = FewShotNL2SQL("../data/sample_examples.json")
    
    # Test with a question
    question = "Show all employees with salary above 50000"
    prompt = few_shot.format_prompt(question)
    sql = few_shot.generate_sql(question)
    
    print(f"Question: {question}")
    print(f"Prompt:\n{prompt}")
    print(f"Generated SQL: {sql}")

if __name__ == "__main__":
    main()