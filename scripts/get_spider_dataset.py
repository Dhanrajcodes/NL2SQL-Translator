"""
Script to provide instructions for downloading the Spider dataset
"""

def get_spider_dataset_instructions():
    """
    Provide clear instructions for downloading the Spider dataset
    """
    print("SPIDER DATASET DOWNLOAD INSTRUCTIONS")
    print("=" * 40)
    
    print("\nOfficial Spider Dataset Repository:")
    print("GitHub: https://github.com/taoyds/spider")
    
    print("\nDownload Methods:")
    print("Method 1 - From GitHub Repository:")
    print("1. Visit: https://github.com/taoyds/spider")
    print("2. Look for the download link in the README (usually a Google Drive link)")
    print("3. Download the 'spider.zip' file")
    
    print("\nMethod 2 - Direct Google Drive Link (if the above doesn't work):")
    print("Try this link: https://drive.google.com/file/d/1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV/view?usp=sharing")
    print("1. Click on the link above")
    print("2. Click 'Download' button (the down arrow icon)")
    print("3. Save the file as 'spider.zip'")
    
    print("\nMethod 3 - Using gdown (if you have it installed):")
    print("1. Install gdown: pip install gdown")
    print("2. Run: gdown 1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV -O data/spider/spider.zip")
    
    print("\nAfter downloading, place the file in the correct location:")
    print("Save it to 'data/spider/spider.zip'")
    print("Then extract the contents to 'data/spider/'")
    
    print("\nAfter extraction, your directory should contain:")
    print("data/spider/")
    print("  database/ (directory with SQLite databases)")
    print("  train_spider.json")
    print("  train_others.json")
    print("  dev.json")
    print("  tables.json")
    
    print("\nTo process the dataset after downloading:")
    print("python scripts/download_spider_proper.py")

def main():
    get_spider_dataset_instructions()

if __name__ == "__main__":
    main()