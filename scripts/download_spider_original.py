"""
Script to download and process the original Spider dataset
"""

import os
import requests
import zipfile
import json
from tqdm import tqdm

def download_spider_dataset():
    """
    Download the original Spider dataset
    """
    print("Original Spider Dataset Downloader")
    print("=" * 35)
    
    # Create directory
    os.makedirs('data/spider', exist_ok=True)
    
    # Official download link from the original Spider repository
    url = "https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV"
    filename = "data/spider/spider.zip"
    
    print("To download the Spider dataset:")
    print("1. Visit: https://github.com/taoyds/spider")
    print("2. Download the dataset from the Google Drive link in the README:")
    print("   https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV")
    print("3. Save the file as 'spider.zip' in the 'data/spider/' directory")
    print("4. Extract the contents")
    
    print("\nDirectory structure after extraction should be:")
    print("data/spider/")
    print("  database/ (directory with SQLite databases)")
    print("  train_spider.json")
    print("  train_others.json")
    print("  dev.json")
    print("  tables.json")
    
    return False

def process_spider_dataset():
    """
    Process the Spider dataset into our training format
    """
    spider_dir = 'data/spider'
    
    # Check if required files exist
    train_file = os.path.join(spider_dir, 'train_spider.json')
    
    if not os.path.exists(train_file):
        print("Spider dataset not found. Please download it first.")
        print("Run 'python scripts/download_spider_proper.py' for instructions.")
        return False
    
    try:
        # Load the training data
        with open(train_file, 'r') as f:
            train_data = json.load(f)
        
        # Process into our format
        processed_train = []
        for item in train_data[:1000]:  # Limit to 1000 examples
            processed_train.append({
                "question": item["question"],
                "sql": item["query"]
            })
        
        # Save processed training data
        with open('data/spider_train.json', 'w') as f:
            json.dump(processed_train, f, indent=2)
        
        # Process dev data for testing
        dev_file = os.path.join(spider_dir, 'dev.json')
        if os.path.exists(dev_file):
            with open(dev_file, 'r') as f:
                dev_data = json.load(f)
            
            processed_test = []
            for item in dev_data[:100]:  # Take first 100 for testing
                processed_test.append({
                    "question": item["question"],
                    "sql": item["query"]
                })
            
            with open('data/spider_test.json', 'w') as f:
                json.dump(processed_test, f, indent=2)
        
        print(f"Spider dataset processed successfully!")
        print(f"Training examples: {len(processed_train)}")
        print(f"Test examples: {len(processed_test) if 'processed_test' in locals() else 0}")
        return True
        
    except Exception as e:
        print(f"Error processing Spider dataset: {e}")
        return False

def main():
    print("Original Spider Dataset Download and Processing")
    print("=" * 50)
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Download dataset
    download_success = download_spider_dataset()
    
    if not download_success:
        print("\nAfter manually downloading the Spider dataset, run this script again to process it.")
        print("To process the dataset, place the extracted files in the 'data/spider/' directory.")
    
    # Try to process if files exist
    process_spider_dataset()
    
    print("\nNext steps:")
    print("1. Run 'python scripts/prepare_finetuning.py' to prepare data for fine-tuning")
    print("2. Run 'python scripts/finetune_with_datasets.py' to fine-tune the model")

if __name__ == "__main__":
    main()