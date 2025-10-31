"""
Script to guide the download and processing of real datasets for NL2SQL fine-tuning
"""

import os
import json

def print_spider_instructions():
    """
    Print detailed instructions for downloading Spider dataset
    """
    print("SPIDER DATASET DOWNLOAD INSTRUCTIONS")
    print("=" * 40)
    print("1. Visit the official Spider dataset repository:")
    print("   https://github.com/taoyds/spider")
    print("\n2. Download the dataset:")
    print("   - Click on the Google Drive link in the README")
    print("   - Download the 'spider.zip' file")
    print("   - Direct link: https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV")
    print("\n3. Extract the dataset:")
    print("   - Save the file as 'spider_dataset.zip'")
    print("   - Extract to 'data/spider/' directory")
    print("\n4. After extraction, your directory should contain:")
    print("   data/spider/")
    print("     database/ (directory with SQLite databases)")
    print("     train_spider.json")
    print("     train_others.json")
    print("     dev.json")
    print("     tables.json")

def print_wikisql_instructions():
    """
    Print detailed instructions for downloading WikiSQL dataset
    """
    print("\n\nWIKISQL DATASET DOWNLOAD INSTRUCTIONS")
    print("=" * 40)
    print("1. Visit the official WikiSQL dataset repository:")
    print("   https://github.com/salesforce/WikiSQL")
    print("\n2. Download the dataset:")
    print("   - Follow the download instructions in the README")
    print("   - Download the 'data.tar.bz2' file")
    print("\n3. Extract the dataset:")
    print("   - Extract 'data.tar.bz2' to 'data/wikisql/' directory")
    print("\n4. After extraction, your directory should contain:")
    print("   data/wikisql/")
    print("     data/")
    print("       train.jsonl")
    print("       dev.jsonl")
    print("       test.jsonl")
    print("     *.tables.jsonl")

def create_sample_data():
    """
    Create sample data for demonstration while waiting for real datasets
    """
    print("\n\nCREATING SAMPLE DATA FOR DEMONSTRATION")
    print("=" * 40)
    
    # Create sample Spider data
    sample_spider = [
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
            "question": "Count employees in each department",
            "sql": "SELECT department, COUNT(*) FROM employee GROUP BY department;"
        },
        {
            "question": "Get the highest paid employee",
            "sql": "SELECT * FROM employee ORDER BY salary DESC LIMIT 1;"
        }
    ]
    
    # Create sample WikiSQL data
    sample_wikisql = [
        {
            "question": "Show all students with grade above 80",
            "sql": "SELECT * FROM student WHERE grade > 80;"
        },
        {
            "question": "List all courses",
            "sql": "SELECT * FROM course;"
        },
        {
            "question": "Find the average grade of all students",
            "sql": "SELECT AVG(grade) FROM student;"
        },
        {
            "question": "Count students in each course",
            "sql": "SELECT course, COUNT(*) FROM student GROUP BY course;"
        },
        {
            "question": "Get the highest grade student",
            "sql": "SELECT * FROM student ORDER BY grade DESC LIMIT 1;"
        }
    ]
    
    # Save sample data
    os.makedirs('data', exist_ok=True)
    
    with open('data/spider_train.json', 'w') as f:
        json.dump(sample_spider, f, indent=2)
    
    with open('data/spider_test.json', 'w') as f:
        json.dump(sample_spider[:2], f, indent=2)
    
    with open('data/wikisql_train.json', 'w') as f:
        json.dump(sample_wikisql, f, indent=2)
    
    with open('data/wikisql_test.json', 'w') as f:
        json.dump(sample_wikisql[:2], f, indent=2)
    
    print("Sample data created successfully!")
    print("Files created:")
    print("  - data/spider_train.json")
    print("  - data/spider_test.json")
    print("  - data/wikisql_train.json")
    print("  - data/wikisql_test.json")

def print_next_steps():
    """
    Print next steps after downloading datasets
    """
    print("\n\nNEXT STEPS AFTER DOWNLOADING DATASETS")
    print("=" * 40)
    print("1. Process the datasets:")
    print("   python scripts/download_spider_real.py")
    print("   python scripts/download_wikisql_real.py")
    print("\n2. Prepare data for fine-tuning:")
    print("   python scripts/prepare_finetuning.py")
    print("\n3. Fine-tune the model:")
    print("   python scripts/finetune_with_datasets.py")
    print("\n4. Or create an Ollama-based enhanced model:")
    print("   ollama create gemma3-nl2sql -f Modelfile")

def main():
    print("NL2SQL Real Dataset Download Guide")
    print("=" * 40)
    
    print_spider_instructions()
    print_wikisql_instructions()
    create_sample_data()
    print_next_steps()
    
    print("\n\nNote: The sample data is provided for demonstration purposes.")
    print("For actual fine-tuning, please download the real datasets using the instructions above.")

if __name__ == "__main__":
    main()