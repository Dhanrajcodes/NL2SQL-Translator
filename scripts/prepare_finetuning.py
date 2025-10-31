"""
Script to prepare data for fine-tuning Gemma model on NL2SQL task
"""

import json
import os

def load_training_data():
    """
    Load training data from Spider and WikiSQL datasets
    """
    training_examples = []
    
    # Check for Spider dataset
    spider_train_path = 'data/spider_train.json'
    if os.path.exists(spider_train_path):
        with open(spider_train_path, 'r') as f:
            spider_data = json.load(f)
            training_examples.extend(spider_data)
        print(f"Loaded {len(spider_data)} examples from Spider dataset")
    
    # Check for WikiSQL dataset
    wikisql_train_path = 'data/wikisql_train.json'
    if os.path.exists(wikisql_train_path):
        with open(wikisql_train_path, 'r') as f:
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
            }
        ]
        print("Using sample training data")
    
    print(f"Total training examples: {len(training_examples)}")
    return training_examples

def create_finetuning_dataset(training_examples, output_file='data/finetuning_dataset.jsonl'):
    """
    Create a dataset for fine-tuning in the format expected by training scripts
    """
    print("Creating fine-tuning dataset...")
    
    with open(output_file, 'w') as f:
        for example in training_examples:
            # Format as JSONL for training
            item = {
                "text": f"Question: {example['question']}\nSQL: {example['sql']}"
            }
            f.write(json.dumps(item) + '\n')
    
    print(f"Fine-tuning dataset created: {output_file}")
    return output_file

def main():
    print("NL2SQL Fine-tuning Data Preparation")
    print("=" * 40)
    
    # Load training data
    training_examples = load_training_data()
    
    # Create fine-tuning dataset
    dataset_file = create_finetuning_dataset(training_examples)
    
    print("\nDataset preparation completed!")
    print("\nTo fine-tune your Gemma model:")
    print("1. For Hugging Face approach:")
    print("   - Make sure you have access to the Gemma model on Hugging Face")
    print("   - Authenticate with: huggingface-cli login")
    print("   - Use a full fine-tuning script with QLoRA")
    print("\n2. For Ollama approach:")
    print("   - Use the Modelfile with the prepared dataset")
    print("   - Run: ollama create gemma3-nl2sql -f Modelfile")
    
    print("\nYour dataset is ready for fine-tuning!")

if __name__ == "__main__":
    main()