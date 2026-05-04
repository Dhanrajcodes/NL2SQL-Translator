"""
Module for generating contextual prompts that incorporate schema information
to improve SQL generation quality.
"""
from typing import Dict, Any, List
import json
from .schema_extractor import format_schema_for_prompt
from .relationship_mapper import format_join_suggestions_for_prompt, RelationshipMapper


class ContextualPrompter:
    """
    Class to generate enhanced prompts with schema and context information
    """
    
    def __init__(self, schema: Dict[str, Any], relationship_mapper: RelationshipMapper = None):
        """
        Initialize the contextual prompter
        
        Args:
            schema: The database schema dictionary
            relationship_mapper: Optional relationship mapper instance
        """
        self.schema = schema
        self.relationship_mapper = relationship_mapper or RelationshipMapper(schema)
    
    def generate_enhanced_prompt(
        self, 
        natural_language_question: str, 
        entities_mentioned: List[str] = None
    ) -> str:
        """
        Generate an enhanced prompt with schema and relationship information
        
        Args:
            natural_language_question: The natural language question to convert to SQL
            entities_mentioned: Optional list of entities mentioned in the question
            
        Returns:
            Enhanced prompt string with schema and relationship context
        """
        # Format the schema information
        schema_text = format_schema_for_prompt(self.schema)
        
        # Get join suggestions if entities are provided
        join_suggestions_text = ""
        if entities_mentioned:
            join_suggestions = self.relationship_mapper.suggest_joins_for_query(entities_mentioned)
            join_suggestions_text = format_join_suggestions_for_prompt(join_suggestions)
        
        # Construct the enhanced prompt
        prompt_parts = []
        
        # System instruction
        prompt_parts.append("You are an expert SQL generator that converts natural language questions into valid SQL queries.")
        prompt_parts.append("Only output SQL code with no additional text or explanations.\n")
        
        # Schema information
        prompt_parts.append(schema_text)
        prompt_parts.append("")
        
        # Join suggestions if available
        if join_suggestions_text and "No specific join suggestions" not in join_suggestions_text:
            prompt_parts.append(join_suggestions_text)
            prompt_parts.append("")
        
        # Few-shot examples with schema context
        prompt_parts.append("EXAMPLES WITH SCHEMA CONTEXT:")
        prompt_parts.append("=============================")
        
        # Example 1: Simple query
        prompt_parts.append("\nExample 1:")
        prompt_parts.append("Question: List all employees")
        prompt_parts.append("Tables involved: employees")
        prompt_parts.append("SQL: SELECT * FROM employees;")
        
        # Example 2: Query with condition
        prompt_parts.append("\nExample 2:")
        prompt_parts.append("Question: Show employees with salary greater than 50000")
        prompt_parts.append("Tables involved: employees")
        prompt_parts.append("SQL: SELECT * FROM employees WHERE salary > 50000;")
        
        # Example 3: Query with JOIN
        if "departments" in self.schema["tables"] and "employees" in self.schema["tables"]:
            prompt_parts.append("\nExample 3:")
            prompt_parts.append("Question: Show all employees and their department names")
            prompt_parts.append("Tables involved: employees, departments")
            prompt_parts.append("Suggested JOIN: employees.department_id = departments.id")
            prompt_parts.append("SQL: SELECT e.name, d.name AS department_name FROM employees e JOIN departments d ON e.department_id = d.id;")
        
        prompt_parts.append("")
        
        # The actual question
        prompt_parts.append("NOW PROCESS THE FOLLOWING QUESTION:")
        prompt_parts.append("==================================")
        prompt_parts.append(f"Question: {natural_language_question}")
        
        if entities_mentioned:
            prompt_parts.append(f"Entities identified: {', '.join(entities_mentioned)}")
        
        # Request for SQL output
        prompt_parts.append("SQL Query:")
        
        return "\n".join(prompt_parts)
    
    def generate_structured_prompt(
        self,
        question: str,
        required_tables: List[str] = None,
        required_columns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured prompt with specific requirements
        
        Args:
            question: The natural language question
            required_tables: Specific tables that should be involved
            required_columns: Specific columns that should be selected
            
        Returns:
            Dictionary containing the structured prompt and metadata
        """
        # Identify tables that might be relevant
        available_tables = list(self.schema["tables"].keys())
        
        # Filter to only required tables if specified
        if required_tables:
            relevant_tables = {name: self.schema["tables"][name] 
                             for name in required_tables 
                             if name in self.schema["tables"]}
        else:
            relevant_tables = self.schema["tables"]
        
        # Generate table-specific information
        table_info = {}
        for table_name, table_schema in relevant_tables.items():
            table_info[table_name] = {
                "columns": [col["name"] for col in table_schema["columns"]],
                "primary_key": table_schema["primary_key"],
                "foreign_keys": [fk["from_column"] for fk in table_schema["foreign_keys"]]
            }
        
        # Create the structured prompt
        structured_prompt = {
            "instruction": "Convert the following natural language question to SQL.",
            "context": {
                "available_tables": available_tables,
                "relevant_tables": list(relevant_tables.keys()),
                "table_details": table_info,
                "relationships": self.schema["relationships"]
            },
            "question": question,
            "requirements": {
                "required_tables": required_tables,
                "required_columns": required_columns
            },
            "examples": [
                {
                    "question": "Show all records from employees table",
                    "sql": "SELECT * FROM employees;"
                },
                {
                    "question": "Find employees with salary more than 50000",
                    "sql": "SELECT * FROM employees WHERE salary > 50000;"
                }
            ],
            "output_format": "Return only the SQL query without any additional text or explanations."
        }
        
        return structured_prompt
    
    def construct_api_prompt(
        self,
        question: str,
        schema_filter: List[str] = None
    ) -> str:
        """
        Construct a prompt specifically formatted for API consumption
        
        Args:
            question: The natural language question
            schema_filter: Optional list of table names to limit schema information
            
        Returns:
            String formatted for API consumption
        """
        # Limit schema to specific tables if filter is provided
        filtered_schema = self.schema
        if schema_filter:
            filtered_tables = {name: self.schema["tables"][name] 
                             for name in schema_filter 
                             if name in self.schema["tables"]}
            filtered_schema = {
                "database_type": self.schema["database_type"],
                "tables": filtered_tables,
                "relationships": [
                    rel for rel in self.schema["relationships"] 
                    if rel["from_table"] in filtered_tables and rel["to_table"] in filtered_tables
                ]
            }
        
        # Format the schema for the prompt
        schema_text = format_schema_for_prompt(filtered_schema)
        
        # Create the API-friendly prompt
        api_prompt = (
            f"### SCHEMA ###\n{schema_text}\n\n"
            f"### INSTRUCTION ###\n"
            f"Convert the following natural language question into a valid SQL query.\n"
            f"Only output the SQL query with no additional text.\n\n"
            f"### QUESTION ###\n"
            f"{question}\n\n"
            f"### SQL QUERY ###"
        )
        
        return api_prompt


def create_contextual_prompter_for_db(db_path: str, db_type: str = "sqlite") -> ContextualPrompter:
    """
    Create a ContextualPrompter instance for a specific database
    
    Args:
        db_path: Path to the database file
        db_type: Type of database
        
    Returns:
        Initialized ContextualPrompter instance
    """
    from .schema_extractor import extract_schema_from_db
    from .relationship_mapper import RelationshipMapper
    
    schema = extract_schema_from_db(db_path, db_type)
    relationship_mapper = RelationshipMapper(schema)
    
    return ContextualPrompter(schema, relationship_mapper)


if __name__ == "__main__":
    # Example usage
    import sqlite3
    import os
    
    # Create a sample database for testing
    sample_db_path = "sample_prompt_test.db"
    
    # Create sample database with related tables
    conn = sqlite3.connect(sample_db_path)
    cursor = conn.cursor()
    
    # Create departments table
    cursor.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL
        );
    """)
    
    # Create employees table with foreign key to departments
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER,
            salary REAL,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        );
    """)
    
    conn.commit()
    conn.close()
    
    # Create contextual prompter for the sample database
    prompter = create_contextual_prompter_for_db(sample_db_path)
    
    # Generate an enhanced prompt
    question = "Show all employees and their department names"
    entities = ["employees", "departments"]
    
    enhanced_prompt = prompter.generate_enhanced_prompt(question, entities)
    print("Enhanced Prompt:")
    print("=" * 50)
    print(enhanced_prompt)
    
    print("\n\nStructured Prompt:")
    print("=" * 50)
    structured = prompter.generate_structured_prompt(
        question, 
        required_tables=["employees", "departments"]
    )
    print(json.dumps(structured, indent=2))
    
    # Clean up
    os.remove(sample_db_path)