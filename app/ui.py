import streamlit as st
import requests
import json
import tempfile
import os

# Page configuration
st.set_page_config(
    page_title="NL2SQL Translator",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 Natural Language to SQL Translator")
st.markdown("Convert natural language questions to SQL queries using AI")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection
    model_options = ["gemma3:1b", "gemma3-nl2sql:latest"]
    selected_model = st.selectbox("Select Model", options=model_options, index=0)
    
    # API endpoint
    api_endpoint = st.text_input("API Endpoint", value="http://localhost:5000/translate")
    
    # Database file upload for schema extraction
    db_file = st.file_uploader("Upload Database File for Schema Extraction", type=['db', 'sqlite', 'sqlite3'])

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Enter your question")
    user_question = st.text_area(
        "Natural language question:",
        height=150,
        placeholder="e.g., Show all employees with salary above 50000, List all departments, etc."
    )
    
    # Advanced options expander
    with st.expander("Advanced Options"):
        st.subheader("Database Schema (Optional)")
        schema_input = st.text_area(
            "Provide database schema information (JSON format):",
            height=200,
            placeholder='''{
  "employees": {
    "columns": [
      {"name": "id", "type": "INTEGER"},
      {"name": "name", "type": "TEXT"},
      {"name": "department_id", "type": "INTEGER"},
      {"name": "salary", "type": "INTEGER"}
    ]
  },
  "departments": {
    "columns": [
      {"name": "id", "type": "INTEGER"},
      {"name": "name", "type": "TEXT"}
    ]
  }
}'''
        )

with col2:
    st.header("Results")
    if st.button("Generate SQL", type="primary", use_container_width=True):
        if not user_question:
            st.error("Please enter a question")
        else:
            with st.spinner("Generating SQL query..."):
                try:
                    # Prepare the payload
                    payload = {
                        "question": user_question,
                        "model": selected_model
                    }
                    
                    # Add schema if provided
                    if schema_input.strip():
                        try:
                            schema_json = json.loads(schema_input)
                            payload["schema"] = schema_json
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format for schema")
                            st.stop()
                    
                    # Prepare files for upload
                    files = {}
                    if db_file is not None:
                        files['db_file'] = (db_file.name, db_file.getvalue(), db_file.type)

                    # Make the API request. Multipart requests must use form fields,
                    # not JSON payloads, when files are attached.
                    if files:
                        form_payload = {
                            "question": payload["question"],
                            "model": payload["model"]
                        }
                        if "schema" in payload:
                            form_payload["schema"] = json.dumps(payload["schema"])

                        response = requests.post(
                            api_endpoint,
                            data=form_payload,
                            files=files,
                            headers={'Accept': 'application/json'}
                        )
                    else:
                        response = requests.post(
                            api_endpoint,
                            json=payload,
                            headers={'Accept': 'application/json'}
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Display the results
                        st.success("✅ Query generated successfully!")
                        st.subheader("Generated SQL")
                        st.code(result['sql'], language='sql')
                        
                        if result.get('schema_used'):
                            st.info("ℹ️ Used schema information for generation")
                        
                        # Show the original question for reference
                        st.subheader("Original Question")
                        st.write(result['question'])
                        
                    else:
                        st.error(f"❌ API Error: {response.status_code}")
                        st.code(response.text)
                
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to the API. Please make sure the backend is running.")
                
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")

# Contextual Translation Tab
st.subheader("Advanced: Contextual Translation with Database Upload")
st.markdown("For more accurate results, upload your database file to enable schema extraction and relationship mapping.")

with st.form(key='contextual_form'):
    contextual_question = st.text_input("Enter your natural language query:")
    
    # For contextual API
    contextual_api_endpoint = "http://localhost:5000/translate_with_context"
    contextual_db_file = st.file_uploader(
        "Upload Database File for Contextual Analysis", 
        type=['db', 'sqlite', 'sqlite3'],
        key='contextual_db'
    )
    
    submit_contextual = st.form_submit_button("Generate with Contextual Awareness")
    
    if submit_contextual:
        if not contextual_question:
            st.error("Please enter a question")
        elif contextual_db_file is None:
            st.error("Please upload a database file")
        else:
            with st.spinner("Analyzing database schema and relationships..."):
                try:
                    # Prepare files for upload
                    files = {
                        'db_file': (contextual_db_file.name, contextual_db_file.getvalue(), contextual_db_file.type),
                        'question': (None, contextual_question),
                        'model': (None, selected_model)
                    }
                    
                    # Make the API request to the contextual endpoint
                    response = requests.post(contextual_api_endpoint, files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Display the results
                        st.success("✅ Contextually enhanced query generated successfully!")
                        st.subheader("Generated SQL")
                        st.code(result['sql'], language='sql')
                        
                        # Show the original question for reference
                        st.subheader("Original Question")
                        st.write(result['question'])
                        
                    else:
                        st.error(f"❌ API Error: {response.status_code}")
                        st.code(response.text)
                
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to the API. Please make sure the backend is running.")
                
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")


# Information section
with st.expander("ℹ️ How it works"):
    st.markdown("""
    ### How this system works:
    
    1. **Natural Language Input**: Enter your question in plain English
    2. **Schema Analysis**: If provided, the system analyzes your database structure
    3. **AI Processing**: The query is processed by a specialized language model
    4. **SQL Generation**: The model generates the corresponding SQL query
    
    ### Features:
    
    - **Schema-Aware Processing**: Understands your database structure
    - **Contextual Understanding**: Considers relationships between tables
    - **Multiple Model Support**: Choose between different AI models
    - **Database Upload**: Automatically extract schema from your database file
    
    ### Tips:
    
    - Be specific in your queries
    - Upload your database file for better results
    - Use clear table and column name references
    """)

# Footer
st.markdown("---")
st.markdown("*NL2SQL Translator - Converting natural language to SQL using neural network architecture*")