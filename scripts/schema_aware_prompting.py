"""
Schema-aware prompting for improved SQL generation
"""

import json
import ollama

class SchemaAwareNL2SQL:
    def __init__(self):
        """
        Initialize schema-aware NL2SQL generator
        """
        pass
    
    def format_schema_prompt(self, question, schema_info=None):
        """
        Format prompt with schema information for better SQL generation
        
        Args:
            question (str): Natural language question
            schema_info (dict): Database schema information
            
        Returns:
            str: Formatted prompt
        """
        if schema_info:
            # Create schema description
            schema_description = "Database Schema:\n"
            for table_name, table_info in schema_info.items():
                schema_description += f"Table: {table_name}\n"
                schema_description += "Columns:\n"
                for column in table_info.get('columns', []):
                    schema_description += f"  - {column['name']} ({column['type']})\n"
                if 'foreign_keys' in table_info:
                    schema_description += "Foreign Keys:\n"
                    for fk in table_info['foreign_keys']:
                        schema_description += f"  - {fk}\n"
                schema_description += "\n"
            
            prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid SQL query using the provided database schema.

{schema_description}
Natural Language Question: {question}

Generate a SQL query to answer this question. Only provide the SQL query, nothing else.

SQL Query:"""
        else:
            # Fallback to basic prompt without schema
            prompt = f"""You are an expert SQL generator. Convert the following natural language question to a valid SQL query.

Examples:
Natural Language: Show all employees in the Sales department.
SQL: SELECT * FROM employees WHERE department = 'Sales';

Natural Language: List the names of students who scored more than 90.
SQL: SELECT name FROM students WHERE score > 90;

Natural Language: Find the total salary of all employees.
SQL: SELECT SUM(salary) FROM employees;

Natural Language: {question}
SQL:"""
        
        return prompt
    
    def generate_sql_with_schema(self, question, schema_info=None):
        """
        Generate SQL with schema awareness
        
        Args:
            question (str): Natural language question
            schema_info (dict): Database schema information
            
        Returns:
            str: Generated SQL query
        """
        try:
            # Format the prompt with schema information
            prompt = self.format_schema_prompt(question, schema_info)
            
            # Generate response using Ollama
            response = ollama.generate(
                model="gemma3:1b",
                prompt=prompt,
                options={
                    "temperature": 0.2,  # Low temperature for more deterministic results
                    "top_p": 0.9,
                    "stop": ["\n\n"]
                }
            )
            
            # Extract and clean the SQL query
            sql_query = response['response'].strip()
            
            # Remove markdown code blocks if present
            if "```sql" in sql_query:
                parts = sql_query.split("```sql")
                if len(parts) > 1:
                    sql_part = parts[1].split("```")[0].strip()
                    sql_query = sql_part
            elif sql_query.startswith("```"):
                lines = sql_query.split("\n")
                code_lines = [line for line in lines if not line.startswith("```")]
                if code_lines:
                    sql_query = "\n".join(code_lines).strip()
            
            # Clean up extra whitespace
            lines = [line.strip() for line in sql_query.split("\n") if line.strip()]
            if lines:
                sql_query = " ".join(lines)
            
            # Ensure it ends with semicolon
            if sql_query and not sql_query.endswith(';'):
                if any(keyword in sql_query.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP']):
                    sql_query += ';'
            
            return sql_query if sql_query else "SELECT * FROM table_name WHERE condition;"
        
        except Exception as e:
            print(f"Error generating SQL with schema: {e}")
            return "SELECT * FROM table_name WHERE condition;"

def load_sample_schema():
    """
    Load sample schema for demonstration
    """
    sample_schema = {
        "employees": {
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "department", "type": "TEXT"},
                {"name": "salary", "type": "INTEGER"}
            ]
        },
        "departments": {
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "budget", "type": "INTEGER"}
            ]
        },
        "enrollments": {
            "columns": [
                {"name": "student_id", "type": "INTEGER"},
                {"name": "course_id", "type": "INTEGER"},
                {"name": "semester", "type": "TEXT"},
                {"name": "grade", "type": "REAL"}
            ],
            "foreign_keys": [
                "student_id references students.id",
                "course_id references courses.id"
            ]
        }
    }
    return sample_schema

def main():
    # Initialize the schema-aware generator
    nl2sql = SchemaAwareNL2SQL()
    
    # Load sample schema
    schema = load_sample_schema()
    
    # Test questions
    questions = [
        "Show all employees with salary above 50000",
        "List all employees and their departments",
        "Find the average salary of employees in each department",
        "Get the top 5 students with highest grades"
    ]
    
    print("Testing Schema-Aware NL2SQL Generation")
    print("=" * 50)
    
    for question in questions:
        print(f"\nQuestion: {question}")
        sql = nl2sql.generate_sql_with_schema(question, schema)
        print(f"Generated SQL: {sql}")
        print("-" * 30)

if __name__ == "__main__":
    main()