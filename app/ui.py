import streamlit as st
import requests
import json

# Set up the Streamlit app
st.set_page_config(page_title="NL2SQL Query Generator", page_icon="🔍", layout="wide")
st.title("Natural Language to SQL Query Generator")

# Sidebar for model selection
st.sidebar.header("Model Configuration")
model_option = st.sidebar.selectbox(
    "Select Model:",
    ("gemma3:1b", "gemma3-nl2sql")
)

# Main content area
st.markdown("""
This application converts natural language questions into SQL queries using advanced AI models.
Simply describe what data you want to retrieve, and the system will generate the appropriate SQL query.
""")

# Create two columns for input and output
col1, col2 = st.columns(2)

with col1:
    st.subheader("Input")
    question = st.text_area("Enter your question:", height=100, 
                           placeholder="e.g., Show all employees with salary above 50000")
    
    # Database schema input
    with st.expander("Database Schema (Optional)"):
        schema_input = st.text_area("Enter database schema:", height=150,
                                   placeholder="""{
    "employees": {
        "columns": [
            {"name": "id", "type": "INTEGER"},
            {"name": "name", "type": "TEXT"},
            {"name": "salary", "type": "INTEGER"}
        ]
    }
}""")
    
    # Generate button
    if st.button("Generate SQL", type="primary", use_container_width=True):
        if question:
            # Prepare the request data
            data = {"question": question}
            if schema_input:
                try:
                    schema = json.loads(schema_input)
                    data["schema"] = schema
                except json.JSONDecodeError:
                    st.error("Invalid JSON in schema input")
                    st.stop()
            
            # Send request to backend
            try:
                response = requests.post(
                    "http://localhost:5000/translate",
                    json=data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    sql_query = result.get("sql_query", "No SQL query generated")
                    
                    with col2:
                        st.subheader("Generated SQL")
                        st.code(sql_query, language="sql")
                        
                        # Show model info
                        st.info(f"Generated using: {model_option}")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend service. Please ensure the API is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter a question.")

# Additional information
st.markdown("---")
st.markdown("""
### Tips for Better Results:
- Be specific about what data you want to retrieve
- Include relevant details like table names and column names when possible
- Use the database schema section to provide context about your data structure
- For the best results, select the 'gemma3-nl2sql' model which has been enhanced with domain-specific training

### How It Works:
1. Your question is processed and enhanced with context
2. The selected AI model converts your natural language into SQL
3. The generated SQL query is returned for your use
""")