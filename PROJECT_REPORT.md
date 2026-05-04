# NL2SQL Studio — Project Report

## 1. Introduction

NL2SQL Studio is a system that converts natural language questions into structured SQL queries using a locally hosted large language model. The goal is to allow non-technical users to interact with relational databases by asking questions in plain English, without needing to know SQL syntax.

The system runs entirely on the user's machine — no cloud APIs or external services are required for inference. This keeps data private and avoids dependency on third-party API keys.

## 2. Problem Statement

Writing SQL requires familiarity with query syntax, table structures, and join logic. For users who need quick answers from a database — analysts, managers, students — this creates a barrier. Existing solutions either rely on paid cloud APIs (OpenAI, Google) or are too simplistic to handle real-world schemas.

We built a self-contained system that:
- Runs locally using open-source models through Ollama
- Understands the actual structure of the database being queried
- Generates syntactically valid SQL across multiple dialects
- Executes queries safely in a read-only sandbox

## 3. System Architecture

The application follows a three-tier architecture:

```
┌──────────────────────┐
│   Streamlit Frontend │  ← Browser-based UI
│   (app/ui.py)        │
└──────────┬───────────┘
           │ HTTP (REST)
┌──────────▼───────────┐
│   Flask Backend      │  ← API layer
│   (app/app.py)       │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼────┐ ┌───▼──────────┐
│ Ollama  │ │ SQLite /     │
│ (LLM)  │ │ External DB  │
└─────────┘ └──────────────┘
```

**Frontend:** Streamlit provides the web interface. Users upload databases, type questions, and view results — all through the browser. The UI supports theme switching (dark/light), schema inspection, and tabbed workflows.

**Backend:** Flask handles all business logic. It receives the user's question, extracts schema from the database, constructs a prompt, sends it to Ollama, and returns the generated SQL. For live execution, it runs the query in a read-only sandbox and returns the result set.

**Model Inference:** Ollama runs the Gemma 3 1B model locally. The backend communicates with Ollama through its Python SDK to generate SQL from the constructed prompt.

## 4. Key Features

### 4.1 Schema-Aware Prompt Engineering

The system does not blindly send the user's question to the model. Before generating SQL, it:

1. Extracts the full schema from the uploaded database (tables, columns, types, primary keys, nullable fields)
2. Detects foreign key relationships and table connections
3. Injects this schema context into the prompt

This significantly improves accuracy because the model knows exactly which tables and columns exist.

### 4.2 Multi-Dialect SQL Generation

The system can generate SQL for five different database engines:
- SQLite
- PostgreSQL
- MySQL
- SQL Server (T-SQL)
- Oracle SQL

The dialect is specified in the prompt, so the model adjusts syntax accordingly (e.g., `LIMIT` vs `FETCH FIRST`, quoting conventions).

### 4.3 Safe Read-Only Execution

When executing queries against real databases, safety is critical. The execution layer (`utils/sql_runner.py`) enforces:

- Only `SELECT` and `WITH` (CTE) statements are allowed
- Statements containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `TRUNCATE`, or `VACUUM` are blocked
- Multi-statement queries (semicolon injection) are rejected
- SQLite connections are opened in read-only mode (`?mode=ro`)
- A configurable row limit prevents excessive data retrieval

### 4.4 External Database Connectivity

Beyond SQLite file uploads, the system supports connecting to live databases through SQLAlchemy connection URLs. This covers PostgreSQL, MySQL, SQL Server, and Oracle. Schema extraction and query execution work the same way — the user just provides a connection string instead of uploading a file.

### 4.5 Contextual Prompt Construction

The `utils/contextual_prompter.py` module builds enhanced prompts that include:
- Suggested JOIN paths based on detected foreign key relationships
- Value hints from the actual data (e.g., department names, status values)
- Relationship context so the model understands how tables connect

This goes beyond basic schema injection and provides the model with the kind of context a human developer would have when writing a query.

### 4.6 Relationship Mapping

The `utils/relationship_mapper.py` module automatically detects:
- Explicit foreign key constraints
- Implicit relationships based on naming conventions (e.g., `department_id` → `departments.id`)
- Many-to-many junction tables

These detected relationships feed into the prompt construction to help the model generate correct JOINs.

## 5. Fine-Tuning Pipeline

We implemented a complete fine-tuning workflow to improve the base model's NL2SQL performance.

### Datasets Used

- **Spider** (Yale University) — 7,000+ complex, cross-domain NL-SQL pairs
- **WikiSQL** (Salesforce Research) — 80,000+ simpler NL-SQL pairs from Wikipedia tables

### Pipeline Steps

1. **Dataset Download** — `scripts/download_datasets.py` provides instructions and processes raw dataset files into a standardized JSON format
2. **Data Preparation** — `scripts/prepare_finetuning.py` converts examples into JSONL format suitable for causal language model training
3. **Fine-Tuning** — `scripts/finetune_with_datasets.py` uses HuggingFace Transformers and the Trainer API to fine-tune a Gemma 2B model with:
   - FP16 mixed precision (when GPU is available)
   - Gradient accumulation for effective batching on limited hardware
   - Conservative hyperparameters (lr=2e-5, 1 epoch) to avoid overfitting
4. **Custom Ollama Model** — The `Modelfile` defines a custom Ollama model variant with a tuned system prompt and inference parameters (temperature=0.2, top_p=0.9)

### Evaluation

`scripts/evaluate_model.py` measures:
- **Exact match accuracy** — percentage of predictions that exactly match the reference SQL
- **Token overlap score** — partial credit metric for queries that are close but not identical

## 6. Frontend Design

The Streamlit interface was designed to be functional and visually clean:

- **Themed UI** — Two color schemes (Night Blue dark theme, Sky Blue light theme) with full CSS customization
- **Custom typography** — IBM Plex Sans for the interface, JetBrains Mono for code/SQL display
- **Sidebar workflow** — Model selection, dialect picker, database upload, and schema inspection are organized in the sidebar
- **Tabbed main area** — Separate tabs for translation-only, generate-and-execute, and direct SQL execution
- **Schema viewer** — Expandable table-by-table view of columns, types, and constraints
- **Result display** — Query results shown in interactive data tables with timing information

## 7. Technologies Used

| Component          | Technology                          |
|--------------------|-------------------------------------|
| Backend framework  | Flask 2.x                           |
| Frontend framework | Streamlit 1.x                       |
| Model serving      | Ollama (local inference)            |
| Base model         | Google Gemma 3 1B                   |
| Database access    | sqlite3 (built-in), SQLAlchemy 2.x  |
| Fine-tuning        | HuggingFace Transformers, Trainer   |
| Datasets           | Spider (Yale), WikiSQL (Salesforce) |
| Styling            | Custom CSS with CSS variables       |

## 8. Challenges Faced

- **Prompt sensitivity** — Small changes in prompt wording caused large differences in SQL output quality. We iterated on the prompt template to find a balance between giving the model enough context and keeping it focused.
- **Schema injection length** — Databases with many tables produce very long prompts. We had to be selective about what schema details to include to stay within the model's context window.
- **Read-only safety** — Preventing SQL injection in the execution layer required careful keyword blocking and multi-statement detection, since user-facing systems cannot trust model output.
- **Fine-tuning on limited hardware** — The fine-tuning script needed conservative batch sizes and gradient accumulation to fit within consumer GPU memory.

## 9. Future Scope

- Support for conversational follow-up questions (multi-turn context)
- Query explanation in plain English alongside the generated SQL
- Visual query builder as an alternative to natural language input
- Integration with more model backends (Llama, Mistral, Phi)
- Automatic query optimization suggestions based on execution plans

## 10. How to Run

Refer to `README.md` for complete setup instructions. In short:

```bash
# Install dependencies
pip install -r requirements.txt

# Pull the model
ollama pull gemma3:1b

# Start the application
python run_project.py
```

Then open http://localhost:8501 in a browser.
