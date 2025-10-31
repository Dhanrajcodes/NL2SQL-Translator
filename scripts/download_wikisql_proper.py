"""
Script to download and process the WikiSQL dataset properly
"""

import os
import requests
import tarfile
import json
from tqdm import tqdm

def download_wikisql_dataset():
    """
    Download the WikiSQL dataset from the official GitHub repository
    """
    print("WikiSQL Dataset Downloader")
    print("=" * 30)
    
    # Create directory
    os.makedirs('data/wikisql', exist_ok=True)
    
    # Official download link from the WikiSQL repository
    url = "https://github.com/salesforce/WikiSQL/raw/master/data.tar.bz2"
    filename = "data/wikisql/data.tar.bz2"
    
    print("Downloading WikiSQL dataset...")
    print("URL:", url)
    
    try:
        # Download with progress bar
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
        
        print("Download completed successfully!")
        return True
    except Exception as e:
        print(f"Error downloading WikiSQL dataset: {e}")
        print("\nAlternative download instructions:")
        print("1. Visit: https://github.com/salesforce/WikiSQL")
        print("2. Download 'data.tar.bz2' manually")
        print("3. Place it in 'data/wikisql/' directory")
        print("4. Extract it with: tar xvjf data.tar.bz2")
        return False

def extract_wikisql_dataset():
    """
    Extract the downloaded WikiSQL dataset
    """
    try:
        print("Extracting WikiSQL dataset...")
        with tarfile.open("data/wikisql/data.tar.bz2", "r:bz2") as tar:
            tar.extractall(path="data/wikisql/")
        print("Extraction completed successfully!")
        return True
    except Exception as e:
        print(f"Error extracting WikiSQL dataset: {e}")
        return False

def process_wikisql_data():
    """
    Process WikiSQL data into our training format
    """
    try:
        print("Processing WikiSQL data...")
        
        # Process training data
        train_file = "data/wikisql/data/train.jsonl"
        processed_train = []
        
        if os.path.exists(train_file):
            with open(train_file, 'r') as f:
                # Process first 1000 examples for training
                for i, line in enumerate(f):
                    if i >= 1000:  # Limit to 1000 examples
                        break
                    item = json.loads(line.strip())
                    
                    # Convert to our format
                    processed_train.append({
                        "question": item["question"],
                        "sql": convert_wikisql_to_sql(item["sql"])
                    })
        
        # Save processed training data
        with open('data/wikisql_train.json', 'w') as f:
            json.dump(processed_train, f, indent=2)
        
        # Process dev data for testing
        dev_file = "data/wikisql/data/dev.jsonl"
        processed_test = []
        
        if os.path.exists(dev_file):
            with open(dev_file, 'r') as f:
                # Process first 100 examples for testing
                for i, line in enumerate(f):
                    if i >= 100:  # Limit to 100 examples
                        break
                    item = json.loads(line.strip())
                    
                    # Convert to our format
                    processed_test.append({
                        "question": item["question"],
                        "sql": convert_wikisql_to_sql(item["sql"])
                    })
            
            with open('data/wikisql_test.json', 'w') as f:
                json.dump(processed_test, f, indent=2)
        
        print(f"WikiSQL dataset processed successfully!")
        print(f"Training examples: {len(processed_train)}")
        print(f"Test examples: {len(processed_test)}")
        return True
        
    except Exception as e:
        print(f"Error processing WikiSQL dataset: {e}")
        return False

def convert_wikisql_to_sql(sql_obj):
    """
    Convert WikiSQL format to standard SQL
    
    Args:
        sql_obj (dict): WikiSQL format SQL object
        
    Returns:
        str: Standard SQL query
    """
    # WikiSQL format is simplified and doesn't represent full SQL
    # For demonstration, we'll create a basic representation
    agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
    cond_ops = ['=', '>', '<', 'OP']
    
    agg = agg_ops[sql_obj['agg']] if sql_obj['agg'] < len(agg_ops) else ''
    sel = sql_obj['sel']
    
    # Simple SQL representation
    if agg:
        sql = f"SELECT {agg}({sel}) FROM table"
    else:
        sql = f"SELECT {sel} FROM table"
    
    # Add conditions if present
    if sql_obj['conds']:
        conditions = []
        for cond in sql_obj['conds']:
            col, op, val = cond
            op_str = cond_ops[op] if op < len(cond_ops) else '='
            conditions.append(f"{col} {op_str} {val}")
        
        if conditions:
            sql += f" WHERE {' AND '.join(conditions)}"
    
    return sql + ";"

def main():
    print("WikiSQL Dataset Download and Processing")
    print("=" * 40)
    
    # Step 1: Download dataset
    download_success = download_wikisql_dataset()
    
    if not download_success:
        print("\nPlease download the dataset manually and try again.")
        return
    
    # Step 2: Extract dataset
    extract_success = extract_wikisql_dataset()
    
    if not extract_success:
        print("\nPlease extract the dataset manually and try again.")
        return
    
    # Step 3: Process dataset
    process_success = process_wikisql_data()
    
    if process_success:
        print("\nWikiSQL dataset is ready for use!")
        print("Files created:")
        print("  - data/wikisql_train.json")
        print("  - data/wikisql_test.json")
    else:
        print("\nError processing dataset. Please check the files and try again.")

if __name__ == "__main__":
    main()