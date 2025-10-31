"""
Script to download and process the real WikiSQL dataset
"""

import os
import requests
import json
from tqdm import tqdm

def download_wikisql_dataset():
    """
    Provide instructions for downloading the WikiSQL dataset
    """
    print("WikiSQL Dataset Download Instructions")
    print("=" * 40)
    print("The WikiSQL dataset must be downloaded manually:")
    print("\nOfficial Source:")
    print("1. Visit: https://github.com/salesforce/WikiSQL")
    print("2. Follow the download instructions in the README")
    print("3. The dataset files are:")
    print("   - data.tar.bz2 (contains the main dataset)")
    print("   - *.tables.jsonl (schema information)")
    print("4. Save and extract to 'data/wikisql/' directory")
    
    print("\nDirectory structure after extraction should be:")
    print("data/wikisql/")
    print("  data/")
    print("    train.jsonl")
    print("    dev.jsonl")
    print("    test.jsonl")
    print("  *.tables.jsonl")
    
    # Create directory if it doesn't exist
    os.makedirs('data/wikisql', exist_ok=True)
    
    return False

def process_wikisql_dataset():
    """
    Process the WikiSQL dataset into our training format
    """
    wikisql_dir = 'data/wikisql'
    data_dir = os.path.join(wikisql_dir, 'data')
    
    # Check if required files exist
    train_file = os.path.join(data_dir, 'train.jsonl')
    
    if not os.path.exists(train_file):
        print("WikiSQL dataset not found. Please download it first.")
        return False
    
    try:
        # Process training data
        processed_train = []
        with open(train_file, 'r') as f:
            # Process first 1000 examples for training
            for i, line in enumerate(f):
                if i >= 1000:  # Limit to 1000 examples
                    break
                item = json.loads(line.strip())
                processed_train.append({
                    "question": item["question"],
                    "sql": f"SELECT {item['sql']['sel']} FROM table"  # Simplified SQL
                })
        
        # Save processed training data
        with open('data/wikisql_train.json', 'w') as f:
            json.dump(processed_train, f, indent=2)
        
        # Process dev data for testing
        dev_file = os.path.join(data_dir, 'dev.jsonl')
        if os.path.exists(dev_file):
            processed_test = []
            with open(dev_file, 'r') as f:
                # Process first 100 examples for testing
                for i, line in enumerate(f):
                    if i >= 100:  # Limit to 100 examples
                        break
                    item = json.loads(line.strip())
                    processed_test.append({
                        "question": item["question"],
                        "sql": f"SELECT {item['sql']['sel']} FROM table"  # Simplified SQL
                    })
            
            with open('data/wikisql_test.json', 'w') as f:
                json.dump(processed_test, f, indent=2)
        
        print(f"WikiSQL dataset processed successfully!")
        print(f"Training examples: {len(processed_train)}")
        print(f"Test examples: {min(len(processed_test), 100) if 'processed_test' in locals() else 0}")
        return True
        
    except Exception as e:
        print(f"Error processing WikiSQL dataset: {e}")
        return False

def main():
    print("WikiSQL Dataset Downloader and Processor")
    print("=" * 45)
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Download dataset
    download_success = download_wikisql_dataset()
    
    if not download_success:
        print("\nAfter manually downloading the WikiSQL dataset, run this script again to process it.")
        print("To process the dataset, place the extracted files in the 'data/wikisql/' directory.")
    
    # Try to process if files exist
    process_wikisql_dataset()

if __name__ == "__main__":
    main()