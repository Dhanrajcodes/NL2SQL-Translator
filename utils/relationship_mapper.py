"""
Module for identifying and mapping table relationships to assist with JOIN operations
in SQL query generation.
"""
from typing import Dict, List, Tuple, Any
from .schema_extractor import SchemaExtractor


class RelationshipMapper:
    """
    Class to map and analyze relationships between tables in a database schema
    """
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize the relationship mapper with a database schema
        
        Args:
            schema: The database schema dictionary from SchemaExtractor
        """
        self.schema = schema
        self.relationships = schema.get("relationships", [])
        self.tables = schema["tables"]
    
    def find_join_paths(self, table_names: List[str]) -> List[Dict[str, Any]]:
        """
        Find possible join paths between specified tables
        
        Args:
            table_names: List of table names to find join paths for
            
        Returns:
            List of dictionaries describing possible join paths
        """
        if len(table_names) < 2:
            return []
        
        # Find all possible connections between the specified tables
        join_paths = []
        
        # Look for direct relationships
        for table1 in table_names:
            for table2 in table_names:
                if table1 != table2:
                    # Find relationships from table1 to table2
                    direct_rels = [
                        rel for rel in self.relationships 
                        if rel["from_table"] == table1 and rel["to_table"] == table2
                    ]
                    
                    for rel in direct_rels:
                        join_paths.append({
                            "type": "direct",
                            "tables": [table1, table2],
                            "join_condition": f"{table1}.{rel['from_column']} = {table2}.{rel['to_column']}",
                            "join_type": self._determine_join_type(rel)
                        })
        
        # Look for indirect relationships (through intermediate tables)
        for table1 in table_names:
            for table2 in table_names:
                if table1 != table2:
                    intermediate_paths = self._find_intermediate_paths(table1, table2, table_names)
                    join_paths.extend(intermediate_paths)
        
        return join_paths
    
    def _find_intermediate_paths(self, start_table: str, end_table: str, all_tables: List[str]) -> List[Dict[str, Any]]:
        """
        Find indirect join paths through intermediate tables
        
        Args:
            start_table: Starting table name
            end_table: Ending table name
            all_tables: List of all table names in consideration
            
        Returns:
            List of indirect join paths
        """
        paths = []
        
        # Look for tables that connect start_table to end_table
        for intermediate_table in all_tables:
            if intermediate_table not in [start_table, end_table]:
                # Find path: start_table -> intermediate_table -> end_table
                start_to_intermediate = [
                    rel for rel in self.relationships
                    if rel["from_table"] == start_table and rel["to_table"] == intermediate_table
                ]
                
                intermediate_to_end = [
                    rel for rel in self.relationships
                    if rel["from_table"] == intermediate_table and rel["to_table"] == end_table
                ]
                
                for s_i_rel in start_to_intermediate:
                    for i_e_rel in intermediate_to_end:
                        paths.append({
                            "type": "indirect",
                            "tables": [start_table, intermediate_table, end_table],
                            "join_conditions": [
                                f"{start_table}.{s_i_rel['from_column']} = {intermediate_table}.{s_i_rel['to_column']}",
                                f"{intermediate_table}.{i_e_rel['from_column']} = {end_table}.{i_e_rel['to_column']}"
                            ],
                            "join_type": "INNER"  # Default to INNER for multi-step joins
                        })
        
        return paths
    
    def _determine_join_type(self, relationship: Dict[str, Any]) -> str:
        """
        Determine the appropriate join type based on relationship properties
        
        Args:
            relationship: A relationship dictionary
            
        Returns:
            String representing the join type
        """
        # If the relationship is one-to-one, we might use INNER JOIN
        # If it's one-to-many and optional, we might use LEFT JOIN
        if relationship["type"] == "one-to-one":
            return "INNER"
        elif relationship["type"] == "one-to-many":
            # Check if the foreign key is nullable to determine if it's optional
            from_table_info = self.tables[relationship["from_table"]]
            fk_column = next(
                (col for col in from_table_info["columns"] 
                 if col["name"] == relationship["from_column"]), 
                None
            )
            
            if fk_column and fk_column["nullable"]:
                return "LEFT"  # Optional relationship
            else:
                return "INNER"  # Mandatory relationship
        
        return "INNER"  # Default
    
    def suggest_joins_for_query(self, entities_mentioned: List[str]) -> List[Dict[str, Any]]:
        """
        Suggest JOIN operations based on entities mentioned in a natural language query
        
        Args:
            entities_mentioned: List of entities (likely table names) mentioned in the query
            
        Returns:
            List of suggested JOIN operations
        """
        # First, try to map the entities to actual table names in the schema
        matched_tables = []
        for entity in entities_mentioned:
            # Simple fuzzy matching - look for tables whose names contain the entity
            for table_name in self.tables.keys():
                if entity.lower() in table_name.lower() or table_name.lower() in entity.lower():
                    if table_name not in matched_tables:
                        matched_tables.append(table_name)
        
        # Find join paths for the matched tables
        join_suggestions = self.find_join_paths(matched_tables)
        
        return join_suggestions
    
    def get_related_tables(self, table_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get tables that are related to the given table
        
        Args:
            table_name: Name of the table to find related tables for
            depth: How many relationship levels deep to search (currently only supports 1)
            
        Returns:
            List of related tables with relationship information
        """
        related = []
        
        # Find tables that this table has foreign keys to (many-to-one relationships)
        table_info = self.tables[table_name]
        for fk in table_info.get("foreign_keys", []):
            related.append({
                "table": fk["to_table"],
                "relationship": "many-to-one",
                "join_condition": f"{table_name}.{fk['from_column']} = {fk['to_table']}.{fk['to_column']}",
                "direction": "outbound"
            })
        
        # Find tables that have foreign keys to this table (one-to-many relationships)
        for rel in self.relationships:
            if rel["to_table"] == table_name:
                related.append({
                    "table": rel["from_table"],
                    "relationship": "one-to-many",
                    "join_condition": f"{rel['from_table']}.{rel['from_column']} = {table_name}.{rel['to_column']}",
                    "direction": "inbound"
                })
        
        return related


def create_relationship_mapper_for_db(db_path: str, db_type: str = "sqlite") -> RelationshipMapper:
    """
    Create a RelationshipMapper instance for a specific database
    
    Args:
        db_path: Path to the database file
        db_type: Type of database
        
    Returns:
        Initialized RelationshipMapper instance
    """
    from .schema_extractor import extract_schema_from_db
    
    schema = extract_schema_from_db(db_path, db_type)
    return RelationshipMapper(schema)


def format_join_suggestions_for_prompt(join_suggestions: List[Dict[str, Any]]) -> str:
    """
    Format join suggestions into a string suitable for inclusion in a prompt
    
    Args:
        join_suggestions: List of join suggestions from the RelationshipMapper
        
    Returns:
        Formatted string representation of join suggestions
    """
    if not join_suggestions:
        return "No specific join suggestions based on detected entities."
    
    formatted = ["SUGGESTED JOINS:", "================"]
    
    for i, suggestion in enumerate(join_suggestions, 1):
        formatted.append(f"\nSuggestion {i}:")
        
        if suggestion["type"] == "direct":
            formatted.append(f"  Tables: {' -> '.join(suggestion['tables'])}")
            formatted.append(f"  Condition: {suggestion['join_condition']}")
            formatted.append(f"  Type: {suggestion['join_type']} JOIN")
        else:
            formatted.append(f"  Tables: {' -> '.join(suggestion['tables'])}")
            formatted.append("  Conditions:")
            for j, condition in enumerate(suggestion['join_conditions'], 1):
                formatted.append(f"    {j}. {condition}")
            formatted.append(f"  Type: {suggestion['join_type']} JOIN")
    
    return "\n".join(formatted)


if __name__ == "__main__":
    # Example usage
    import sqlite3
    import os
    
    # Create a sample database for testing
    sample_db_path = "sample_join_test.db"
    
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
    
    # Create projects table
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER,
            budget REAL,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        );
    """)
    
    conn.commit()
    conn.close()
    
    # Create relationship mapper for the sample database
    mapper = create_relationship_mapper_for_db(sample_db_path)
    
    # Find join paths between employees and departments
    join_paths = mapper.find_join_paths(["employees", "departments"])
    print("Join paths between employees and departments:")
    print(format_join_suggestions_for_prompt(join_paths))
    
    print("\nRelated tables for departments:")
    related = mapper.get_related_tables("departments")
    for r in related:
        print(f"- {r['table']} ({r['relationship']}, {r['direction']})")
    
    # Clean up
    os.remove(sample_db_path)