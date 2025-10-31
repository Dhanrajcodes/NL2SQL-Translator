"""
Script to download and process the Spider dataset from the official GitHub repository
"""

import os
import json
import requests
import zipfile
from tqdm import tqdm
import sqlite3

def download_file(url, filename):
    """
    Download a file with progress bar
    """
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

def create_sample_spider_data():
    """
    Create sample Spider data for demonstration
    """
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
        }
    ]
    
    # Save as JSON
    with open('data/spider_train.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    with open('data/spider_test.json', 'w') as f:
        json.dump(sample_data[:2], f, indent=2)
    
    print("Sample Spider data created for demonstration!")
    print(f"Training examples: {len(sample_data)}")
    return sample_data

def main():
    print("Spider Dataset Processor")
    print("=" * 30)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/spider', exist_ok=True)
    
    # Check if Spider dataset exists
    spider_data_path = 'data/spider/train_spider.json'
    
    if not os.path.exists(spider_data_path):
        print("Spider Dataset Downloader")
        print("=" * 30)
        print("The Spider dataset needs to be downloaded manually:")
        print("1. Visit: https://github.com/taoyds/spider")
        print("2. Download the dataset files from: https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV")
        print("   (This is the official Spider dataset link)")
        print("3. Extract the files to data/spider/")
        print("\nDataset structure should be:")
        print("data/spider/")
        print("  train_spider.json")
        print("  dev.json")
        print("  database/ (directory with SQLite databases)")
        
        # Create sample data for demonstration
        print("\nCreating sample data for demonstration...")
        create_sample_spider_data()
    else:
        print("Spider dataset found. Processing...")
        # Process the actual Spider dataset
        process_spider_dataset()

def process_spider_dataset():
    """
    Process the Spider dataset into our format
    """
    try:
        # Load the Spider training data
        with open('data/spider/train_spider.json', 'r') as f:
            spider_data = json.load(f)
        
        # Process into our format
        processed_data = []
        for item in spider_data[:100]:  # Limit to first 100 for demo
            processed_data.append({
                "question": item["question"],
                "sql": item["query"]
            })
        
        # Save processed data
        with open('data/spider_train.json', 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        # Process dev data for testing
        with open('data/spider/dev.json', 'r') as f:
            dev_data = json.load(f)
        
        test_data = []
        for item in dev_data[:20]:  # Limit to first 20 for test set
            test_data.append({
                "question": item["question"],
                "sql": item["query"]
            })
        
        with open('data/spider_test.json', 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"Spider dataset processed successfully!")
        print(f"Training examples: {len(processed_data)}")
        print(f"Test examples: {len(test_data)}")
        
    except Exception as e:
        print(f"Error processing Spider dataset: {e}")
        print("Creating sample data instead...")
        create_sample_spider_data()

if __name__ == "__main__":
    main()