"""
Script to download the Spider dataset using requests
"""

import os
import requests
from tqdm import tqdm

def download_spider_dataset():
    """
    Download the Spider dataset using requests
    """
    print("Spider Dataset Downloader using Requests")
    print("=" * 40)
    
    # Create directory
    os.makedirs('data/spider', exist_ok=True)
    
    # URL for the Spider dataset
    url = "https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV"
    filename = "data/spider/spider.zip"
    
    print("To download the Spider dataset:")
    print("1. Visit this URL in your browser:")
    print(f"   {url}")
    print("2. Click the 'Download' button to download the spider.zip file")
    print("3. Save it as 'spider.zip' in the 'data/spider/' directory")
    print("4. Extract the contents")
    
    print("\nAlternative method - try this URL:")
    print("   https://drive.google.com/file/d/1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV/view?usp=sharing")
    
    print("\nDirectory structure after extraction should be:")
    print("data/spider/")
    print("  database/ (directory with SQLite databases)")
    print("  train_spider.json")
    print("  train_others.json")
    print("  dev.json")
    print("  tables.json")
    
    return False

def main():
    download_spider_dataset()

if __name__ == "__main__":
    main()