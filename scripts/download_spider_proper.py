"""
Script to download and process the Spider dataset properly
"""

import os
import requests
import zipfile
import json
from tqdm import tqdm

# Global constants
DATA_DIR = 'data'
SPIDER_DIR = os.path.join(DATA_DIR, 'spider')
SPIDER_URL = "https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV"
CHUNK_SIZE = 32768  # 32KB chunks for efficient downloading

def download_file(url, filename):
    """
    Download a file from a given URL with progress bar
    """
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        print(f"Downloading file from {url}")
        print(f"Saving to: {filename}")
        
        # Start the download
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Get total file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
        
        # Write file in binary mode
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:  # Filter out keep-alive new chunks
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        progress_bar.close()
        print("Download completed successfully!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Network error during download: {e}")
        return False
    except Exception as e:
        print(f"Error during download: {e}")
        return False

def extract_zip(zip_path, extract_path):
    """
    Extract a zip file to the specified directory
    """
    try:
        print(f"Extracting zip file: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print("Extraction completed successfully!")
        return True
    except zipfile.BadZipFile:
        print("Error: The downloaded file is not a valid zip archive.")
        return False
    except Exception as e:
        print(f"Error during extraction: {e}")
        return False

def download_spider_dataset():
    """
    Download and extract the Spider dataset
    """
    print("Spider Dataset Download and Extraction")
    print("=" * 40)
    
    # Define file paths
    zip_path = os.path.join(SPIDER_DIR, 'spider.zip')
    
    # Download the dataset if not already present
    if not os.path.exists(zip_path):
        print("Initiating Spider dataset download...")
        if not download_file(SPIDER_URL, zip_path):
            print("Download failed. Please try again later.")
            return False
    else:
        print(f"Found existing Spider zip file at {zip_path}")
    
    # Extract the dataset
    if not extract_zip(zip_path, SPIDER_DIR):
        print("Extraction failed. Please verify the zip file is complete.")
        return False
    
    # Verify extracted files
    required_files = [
        'train_spider.json',
        'train_others.json',
        'dev.json',
        'tables.json',
        'database'
    ]
    
    print("\nVerifying extracted files...")
    all_present = True
    for item in required_files:
        item_path = os.path.join(SPIDER_DIR, item)
        if os.path.exists(item_path):
            print(f"✓ Found: {item}")
        else:
            print(f"✗ Missing: {item}")
            all_present = False
    
    if not all_present:
        print("\nWarning: Some required files are missing from the extraction.")
        print("The dataset may not be complete or may have been extracted incorrectly.")
    
    return True

def process_spider_dataset():
    """
    Process the Spider dataset into our training format
    """
    print("\nProcessing Spider Dataset")
    print("=" * 40)
    
    spider_dir = SPIDER_DIR
    
    # Check if required files exist
    train_file = os.path.join(spider_dir, 'train_spider.json')
    
    if not os.path.exists(train_file):
        print("Spider dataset not found. Please download it first.")
        return False
    
    try:
        # Load the training data
        print(f"Loading training data from {train_file}...")
        with open(train_file, 'r') as f:
            train_data = json.load(f)
        
        print(f"Found {len(train_data)} training examples")
        
        # Process into our format
        print("Processing training data...")
        processed_train = []
        for item in tqdm(train_data[:1000], total=1000):  # Limit to 1000 examples
            processed_train.append({
                "question": item["question"],
                "sql": item["query"]
            })
        
        # Save processed training data
        train_output_path = os.path.join(DATA_DIR, 'spider_train.json')
        print(f"Saving processed training data to {train_output_path}...")
        with open(train_output_path, 'w') as f:
            json.dump(processed_train, f, indent=2)
        
        # Process dev data for testing
        dev_file = os.path.join(spider_dir, 'dev.json')
        if os.path.exists(dev_file):
            print(f"Loading dev data from {dev_file}...")
            with open(dev_file, 'r') as f:
                dev_data = json.load(f)
            
            print(f"Found {len(dev_data)} dev examples")
            
            print("Processing dev data...")
            processed_test = []
            for item in tqdm(dev_data[:100], total=100):  # Take first 100 for testing
                processed_test.append({
                    "question": item["question"],
                    "sql": item["query"]
                })
            
            test_output_path = os.path.join(DATA_DIR, 'spider_test.json')
            print(f"Saving processed test data to {test_output_path}...")
            with open(test_output_path, 'w') as f:
                json.dump(processed_test, f, indent=2)
        
        print("\nSpider dataset processed successfully!")
        print(f"Training examples: {len(processed_train)}")
        print(f"Test examples: {len(processed_test) if 'processed_test' in locals() else 0}")
        return True
        
    except Exception as e:
        print(f"Error processing Spider dataset: {e}")
        return False

def main():
    print("Spider Dataset Download and Processing")
    print("=" * 40)
    
    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Download dataset
    print("Starting Spider dataset download and extraction...")
    download_success = download_spider_dataset()
    
    if not download_success:
        print("\nSpider dataset download or extraction failed.")
        print("Please verify your internet connection and try again.")
        print("If the problem persists, you can manually download the dataset from:")
        print("https://github.com/taoyds/spider")
    
    # Try to process if files exist
    print("\nStarting dataset processing...")
    process_success = process_spider_dataset()
    
    if process_success:
        print("\nAll operations completed successfully!")
        print(f"Processed training data saved to: {os.path.join(DATA_DIR, 'spider_train.json')}")
        print(f"Processed test data saved to: {os.path.join(DATA_DIR, 'spider_test.json')}")
    else:
        print("\nDataset processing failed.")
        print("The dataset may not be complete or may have issues with the file structure.")

if __name__ == "__main__":
    main()