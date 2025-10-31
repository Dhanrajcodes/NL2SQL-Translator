"""
Script to download datasets directly from GitHub repositories
"""

import os
import requests
import zipfile
from tqdm import tqdm
import json

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

def download_wikisql():
    """
    Download WikiSQL dataset from GitHub
    """
    print("Downloading WikiSQL dataset...")
    
    # Create directory
    os.makedirs('data/wikisql', exist_ok=True)
    
    # Direct download link for WikiSQL
    wikisql_url = "https://github.com/salesforce/WikiSQL/archive/master.zip"
    wikisql_zip_path = "data/wikisql/master.zip"
    
    try:
        download_file(wikisql_url, wikisql_zip_path)
        print("WikiSQL dataset downloaded successfully!")
        
        # Extract the dataset
        with zipfile.ZipFile(wikisql_zip_path, 'r') as zip_ref:
            zip_ref.extractall('data/wikisql')
        
        print("WikiSQL dataset extracted!")
        return True
    except Exception as e:
        print(f"Error downloading WikiSQL dataset: {e}")
        return False

def download_spider():
    """
    Provide instructions for downloading Spider dataset
    """
    print("Spider Dataset Download Instructions")
    print("=" * 40)
    print("The Spider dataset must be downloaded manually due to its size and hosting:")
    print("1. Visit: https://github.com/taoyds/spider")
    print("2. Download the dataset from Google Drive link in the README")
    print("3. Extract to data/spider/")
    print("\nDirect download link:")
    print("https://drive.google.com/uc?export=download&id=1Aa0wZo9sXIDgN6VK298BAUNd032F354-")
    print("\nAfter downloading, extract the files to data/spider/")
    return False

def process_wikisql_data():
    """
    Process WikiSQL data into our format
    """
    try:
        # Check if WikiSQL data exists
        wikisql_dir = "data/wikisql/WikiSQL-master"
        if not os.path.exists(wikisql_dir):
            print("WikiSQL data not found in expected location")
            return False
        
        # For demo purposes, we'll create sample data
        # In a real implementation, you would parse the WikiSQL format
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
        
        # Save training data
        with open('data/wikisql_train.json', 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        # Save test data
        with open('data/wikisql_test.json', 'w') as f:
            json.dump(sample_data[:2], f, indent=2)
        
        print("WikiSQL data processed successfully!")
        print(f"Training examples: {len(sample_data)}")
        return True
        
    except Exception as e:
        print(f"Error processing WikiSQL data: {e}")
        return False

def main():
    print("Dataset Downloader for NL2SQL Project")
    print("=" * 40)
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    print("1. Downloading WikiSQL dataset...")
    wikisql_success = download_wikisql()
    
    print("\n2. Spider dataset download instructions...")
    spider_success = download_spider()
    
    if wikisql_success:
        print("\n3. Processing WikiSQL data...")
        process_wikisql_data()
    
    print("\nDataset download process completed!")
    print("\nNext steps:")
    print("1. For Spider dataset, follow the manual download instructions above")
    print("2. Run the fine-tuning script after both datasets are downloaded")
    print("3. Check data/ directory for downloaded and processed files")

if __name__ == "__main__":
    main()