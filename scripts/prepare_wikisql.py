"""
Script to download and prepare WikiSQL dataset for fine-tuning Gemma3 model
"""

import json
import os
import requests
import zipfile
from tqdm import tqdm

def download_wikisql():
    """
    Download WikiSQL dataset
    """
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # WikiSQL dataset URL
    url = "https://github.com/salesforce/WikiSQL/raw/master/data.tar.bz2"
    
    print("Downloading WikiSQL dataset...")
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open('data/wikisql.tar.bz2', 'wb') as file, tqdm(
            desc="Downloading WikiSQL",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    progress_bar.update(len(chunk))
        
        print("WikiSQL dataset downloaded successfully!")
        return True
    except Exception as e:
        print(f"Error downloading WikiSQL dataset: {e}")
        return False

def prepare_wikisql_data():
    """
    Prepare WikiSQL data for fine-tuning
    """
    # For now, we'll create a sample dataset to demonstrate the structure
    # In a real implementation, you would extract and process the actual WikiSQL data
    
    sample_data = [
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
        },
        {
            "question": "Get the highest paid employee",
            "sql": "SELECT * FROM employee ORDER BY salary DESC LIMIT 1;"
        }
    ]
    
    # Save sample training data
    with open('data/wikisql_train.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    # Save sample test data
    with open('data/wikisql_test.json', 'w') as f:
        json.dump(sample_data[:2], f, indent=2)
    
    print("Sample WikiSQL data prepared!")
    print(f"Training examples: {len(sample_data)}")
    print(f"Test examples: {len(sample_data[:2])}")

def main():
    print("Preparing WikiSQL dataset for fine-tuning...")
    
    # In a real implementation, you would download and process the actual dataset
    # download_wikisql()
    
    # For now, we'll just create sample data to demonstrate the structure
    prepare_wikisql_data()
    
    print("\nTo use the actual WikiSQL dataset:")
    print("1. Visit: https://github.com/salesforce/WikiSQL")
    print("2. Download the dataset")
    print("3. Extract and process the data according to the WikiSQL format")
    print("4. Replace the sample data with the actual processed data")

if __name__ == "__main__":
    main()