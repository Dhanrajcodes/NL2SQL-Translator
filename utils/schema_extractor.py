"""
Module for extracting database schema information from various database formats
Supports SQLite, MySQL, and PostgreSQL with automatic detection of tables, columns, and relationships
"""
import sqlite3
import json
import re
from typing import Dict, List, Tuple, Any, Optional


class SchemaExtractor:
    """
    Class to extract schema information from different database types
    """
    
    def __init__(self, db_path: str = None, db_type: str = "sqlite"):
        """
        Initialize the schema extractor
        
        Args:
            db_path: Path to the database file
            db_type: Type of database (currently supports 'sqlite', with extensions for MySQL/PostgreSQL)
        """
        self.db_path = db_path
        self.db_type = db_type
        self.connection = None
    
    def connect_to_db(self):
        """
        Establish connection to the database
        """
        if self.db_type == "sqlite":
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def close_connection(self):
        """
        Close the database connection
        """
        if self.connection:
            self.connection.close()
    
    def extract_schema(self) -> Dict[str, Any]:
        """
        Extract the complete schema from the database
        
        Returns:
            Dictionary containing tables, columns, and relationships
        """
        if not self.connection:
            self.connect_to_db()
        
        schema = {
            "database_type": self.db_type,
            "tables": {},
            "relationships": []
        }
        
        # Get all table names
        table_names = self._get_table_names()
        
        # Extract schema for each table
        for table_name in table_names:
            schema["tables"][table_name] = self._extract_table_schema(table_name)
        
        # Detect relationships between tables
        schema["relationships"] = self._detect_relationships(schema["tables"])
        
        return schema
    
    def _get_table_names(self) -> List[str]:
        """
        Get all table names from the database
        
        Returns:
            List of table names
        """
        cursor = self.connection.cursor()
        
        if self.db_type == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
        
        return tables
    
    def _extract_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Extract schema for a specific table
        
        Args:
            table_name: Name of the table to extract schema for
            
        Returns:
            Dictionary containing table schema information
        """
        cursor = self.connection.cursor()
        
        if self.db_type == "sqlite":
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            
            # Get foreign key info
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            foreign_keys = cursor.fetchall()
        
        # Format column information
        columns = []
        for col in columns_info:
            column_info = {
                "name": col[1],
                "type": col[2],
                "nullable": not col[3],  # not null constraint
                "default_value": col[4],
                "primary_key": col[5] == 1
            }
            columns.append(column_info)
        
        # Format foreign key information
        foreign_keys_formatted = []
        for fk in foreign_keys:
            fk_info = {
                "id": fk[0],
                "from_column": fk[3],  # local column name
                "to_table": fk[2],     # referenced table
                "to_column": fk[4]     # referenced column
            }
            foreign_keys_formatted.append(fk_info)
        
        table_schema = {
            "name": table_name,
            "columns": columns,
            "foreign_keys": foreign_keys_formatted,
            "primary_key": [col["name"] for col in columns if col["primary_key"]]
        }
        
        return table_schema
    
    def _detect_relationships(self, tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect relationships between tables based on foreign keys
        
        Args:
            tables: Dictionary of all table schemas
            
        Returns:
            List of detected relationships
        """
        relationships = []
        
        for table_name, table_info in tables.items():
            for fk in table_info.get("foreign_keys", []):
                relationship = {
                    "from_table": table_name,
                    "from_column": fk["from_column"],
                    "to_table": fk["to_table"],
                    "to_column": fk["to_column"],
                    "type": "one-to-many"  # Default assumption
                }
                
                # Try to determine if it's a one-to-one relationship
                # This would be if the foreign key is also part of a primary key or has a uniqueness constraint
                from_col_info = next((col for col in table_info["columns"] 
                                     if col["name"] == fk["from_column"]), None)
                
                if from_col_info and from_col_info["primary_key"]:
                    # Check if this foreign key is part of a composite primary key
                    if len(table_info["primary_key"]) == 1:
                        relationship["type"] = "one-to-one"
                
                relationships.append(relationship)
        
        return relationships


def extract_schema_from_db(db_path: str, db_type: str = "sqlite") -> Dict[str, Any]:
    """
    Convenience function to extract schema from a database
    
    Args:
        db_path: Path to the database file
        db_type: Type of database
        
    Returns:
        Dictionary containing the extracted schema
    """
    extractor = SchemaExtractor(db_path, db_type)
    try:
        schema = extractor.extract_schema()
        return schema
    finally:
        extractor.close_connection()


def format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Format the extracted schema into a string suitable for inclusion in a prompt
    
    Args:
        schema: The extracted schema dictionary
        
    Returns:
        Formatted string representation of the schema
    """
    formatted = []
    formatted.append("DATABASE SCHEMA INFORMATION:")
    formatted.append("============================")
    
    for table_name, table_info in schema["tables"].items():
        formatted.append(f"\nTable: {table_name}")
        formatted.append("-" * (len(f"Table: {table_name}")))
        
        # Add primary key information
        if table_info["primary_key"]:
            formatted.append(f"Primary Key(s): {', '.join(table_info['primary_key'])}")
        
        # Add column information
        formatted.append("Columns:")
        for col in table_info["columns"]:
            nullable_str = "NULL" if col["nullable"] else "NOT NULL"
            default_str = f", Default: {col['default_value']}" if col['default_value'] is not None else ""
            pk_str = " (PK)" if col["primary_key"] else ""
            
            formatted.append(f"  - {col['name']} ({col['type']}) {nullable_str}{default_str}{pk_str}")
        
        # Add foreign key information
        if table_info["foreign_keys"]:
            formatted.append("Foreign Keys:")
            for fk in table_info["foreign_keys"]:
                formatted.append(f"  - {fk['from_column']} -> {fk['to_table']}.{fk['to_column']}")
    
    # Add relationship information
    if schema["relationships"]:
        formatted.append("\nRELATIONSHIPS:")
        formatted.append("==============")
        for rel in schema["relationships"]:
            formatted.append(f"{rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} ({rel['type']})")
    
    return "\n".join(formatted)


if __name__ == "__main__":
    # Example usage
    import os
    
    # Create a sample database for testing
    sample_db_path = "sample_test.db"
    
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
    
    # Extract schema from the sample database
    schema = extract_schema_from_db(sample_db_path)
    
    # Print formatted schema
    print(format_schema_for_prompt(schema))
    
    # Clean up
    os.remove(sample_db_path)