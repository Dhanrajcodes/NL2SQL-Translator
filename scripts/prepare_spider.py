"""
Script to prepare Spider dataset for fine-tuning Gemma3 model
"""

import json
import os

def prepare_spider_data():
    """
    Prepare Spider data for fine-tuning (sample structure)
    """
    # Create sample Spider dataset structure
    # In a real implementation, you would download and process the actual Spider dataset
    
    sample_data = [
        {
            "question": "Find the name of the student who has taken the most courses",
            "sql": "SELECT T1.name FROM Student AS T1 JOIN Enrollments AS T2 ON T1.id = T2.student_id GROUP BY T1.id ORDER BY COUNT(*) DESC LIMIT 1;"
        },
        {
            "question": "List all students and their advisors",
            "sql": "SELECT T1.name, T2.name FROM Student AS T1 JOIN Faculty AS T2 ON T1.advisor_id = T2.id;"
        },
        {
            "question": "Show the average grade for each course",
            "sql": "SELECT T1.course_name, AVG(T2.grade) FROM Courses AS T1 JOIN Enrollments AS T2 ON T1.id = T2.course_id GROUP BY T1.id;"
        },
        {
            "question": "Find students who have taken courses in both Spring and Fall semesters",
            "sql": "SELECT T1.name FROM Student AS T1 WHERE T1.id IN (SELECT T2.student_id FROM Enrollments AS T2 WHERE T2.semester = 'Spring') AND T1.id IN (SELECT T3.student_id FROM Enrollments AS T3 WHERE T3.semester = 'Fall');"
        }
    ]
    
    # Save sample training data
    with open('data/spider_train.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    # Save sample test data
    with open('data/spider_test.json', 'w') as f:
        json.dump(sample_data[:2], f, indent=2)
    
    print("Sample Spider data prepared!")
    print(f"Training examples: {len(sample_data)}")
    print(f"Test examples: {len(sample_data[:2])}")

def main():
    print("Preparing Spider dataset for fine-tuning...")
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Prepare sample Spider data
    prepare_spider_data()
    
    print("\nTo use the actual Spider dataset:")
    print("1. Visit: https://github.com/taoyds/spider")
    print("2. Download the dataset")
    print("3. Extract and process the data according to the Spider format")
    print("4. Replace the sample data with the actual processed data")

if __name__ == "__main__":
    main()