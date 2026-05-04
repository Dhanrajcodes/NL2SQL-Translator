# NL2SQL Studio

A locally-hosted Natural Language to SQL translation system built with Flask, Streamlit, and Ollama. This project lets users type plain English questions and receive valid SQL queries, with optional live execution against real databases.

## What This Project Does

- Translates English questions into SQL using a locally running Ollama language model (Gemma 3 1B)
- Supports multiple SQL dialects: SQLite, PostgreSQL, MySQL, SQL Server, and Oracle
- Automatically extracts and uses database schema context for accurate query generation
- Executes read-only queries safely on uploaded SQLite files or external database connections
- Includes scripts for fine-tuning the model on NL2SQL datasets (Spider, WikiSQL)
- Provides a clean web interface for the entire workflow

## Prerequisites

| Requirement       | Version | Notes                                |
|-------------------|---------|--------------------------------------|
| Python            | 3.10+   | Tested on 3.12 and 3.14              |
| Ollama            | latest  | https://ollama.com/download          |
| Git               | any     | For cloning                          |

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repo-url>
cd NL2SQL
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Core dependencies (required):

```bash
pip install -r requirements.txt
```

For connecting to external databases (PostgreSQL, MySQL, etc.):

```bash
pip install -r requirements-db.txt
```

For running the fine-tuning pipeline:

```bash
pip install -r requirements-finetune.txt
```

### 4. Install and set up Ollama

1. Download and install Ollama from https://ollama.com/download
2. Verify it is working:

```bash
ollama --version
```

3. Pull the base model:

```bash
ollama pull gemma3:1b
```

4. (Optional) Create a custom model variant with tuned system prompt:

```bash
ollama create gemma3-nl2sql -f Modelfile
```

## Running the Application

The easiest way to start everything:

```bash
python run_project.py
```

This starts both the Flask backend (port 5000) and the Streamlit frontend (port 8501) together.

**Alternatively**, start them in separate terminals:

Terminal 1 — Backend:

```bash
python -m app.app
```

Terminal 2 — Frontend:

```bash
streamlit run app/ui.py
```

Once running, open http://localhost:8501 in your browser.

## How to Use

1. Select a model and SQL dialect in the sidebar
2. Choose your database source:
   - **SQLite file**: Upload a `.db` file directly
   - **External connection**: Provide a SQLAlchemy connection URL
3. Click **Inspect database** to extract and view the schema
4. Go to the main area, type your English question
5. Click **Generate SQL** for translation only, or **Generate & Execute** to run the query and see results

## External Database Connection URL Formats

| Database   | URL Format                                                                    |
|------------|-------------------------------------------------------------------------------|
| PostgreSQL | `postgresql+psycopg://user:password@host:5432/dbname`                        |
| MySQL      | `mysql+pymysql://user:password@host:3306/dbname`                             |
| SQL Server | `mssql+pyodbc://user:password@host:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server` |
| Oracle     | `oracle+oracledb://user:password@host:1521/?service_name=orclpdb1`           |

Install the corresponding driver from `requirements-db.txt` before using these.

## API Endpoints

| Method | Route                    | Description                                    |
|--------|--------------------------|------------------------------------------------|
| POST   | `/translate`             | Translate NL question to SQL                   |
| POST   | `/schema`                | Extract schema from uploaded SQLite file        |
| POST   | `/query`                 | Generate SQL and execute on uploaded SQLite     |
| POST   | `/execute_sql`           | Execute raw SQL on uploaded SQLite              |
| POST   | `/connection_schema`     | Extract schema from external DB connection      |
| POST   | `/query_connection`      | Generate SQL and execute on external DB         |
| POST   | `/execute_connection_sql`| Execute raw SQL on external DB                  |
| POST   | `/translate_with_context`| NL to SQL with enhanced contextual prompting    |
| GET    | `/health`                | Health check                                   |

## Fine-Tuning (Optional)

This project includes scripts to fine-tune the base model using publicly available NL2SQL datasets.

### Step 1 — Download datasets

Follow the instructions printed by:

```bash
python scripts/download_datasets.py
```

Datasets used:
- **Spider** — https://github.com/taoyds/spider
- **WikiSQL** — https://github.com/salesforce/WikiSQL

### Step 2 — Prepare training data

```bash
python scripts/prepare_finetuning.py
```

This creates `data/finetuning_dataset.jsonl`.

### Step 3 — Run fine-tuning

```bash
python scripts/finetune_with_datasets.py
```

The fine-tuned model is saved to `models/gemma-nl2sql-finetuned/`.

> **Note:** Fine-tuning requires a GPU with sufficient VRAM. Reduce `per_device_train_batch_size` or `MAX_LENGTH` in the script if running on limited hardware.

## Evaluation

```bash
python scripts/evaluate_model.py
```

This runs the model against test examples and outputs exact-match accuracy and token overlap scores to `evaluation_results.json`.

## Project Structure

```
NL2SQL/
├── app/
│   ├── app.py               # Flask REST API (backend)
│   └── ui.py                # Streamlit web interface (frontend)
├── utils/
│   ├── schema_extractor.py  # SQLite schema extraction
│   ├── sql_runner.py        # Safe read-only query execution
│   ├── db_connector.py      # External database connections (SQLAlchemy)
│   ├── contextual_prompter.py  # Enhanced prompt construction
│   └── relationship_mapper.py  # Foreign key / relationship detection
├── scripts/
│   ├── download_datasets.py     # Dataset download helper
│   ├── prepare_finetuning.py    # JSONL preparation for fine-tuning
│   ├── finetune_with_datasets.py # Fine-tuning script (HuggingFace Trainer)
│   └── evaluate_model.py        # Model evaluation
├── data/
│   ├── sample.db                # Sample SQLite database for quick testing
│   └── finetuning_dataset.jsonl # Prepared training data
├── Modelfile                # Ollama custom model definition
├── run_project.py           # One-command launcher (backend + frontend)
├── requirements.txt         # Core runtime dependencies
├── requirements-db.txt      # External database drivers
└── requirements-finetune.txt # Fine-tuning dependencies
```

## Troubleshooting

| Problem                        | Solution                                                    |
|--------------------------------|-------------------------------------------------------------|
| Backend not running            | Run `python run_project.py` or start Flask manually          |
| Ollama timeout / errors        | Ensure Ollama service is running, verify with `ollama list`  |
| External DB connection errors  | Check URL format, install matching driver, check credentials |
| SQL blocked during execution   | Only read-only `SELECT` / `WITH` queries are allowed         |
| Port 8501 already in use       | Stop any existing Streamlit process or use `--server.port`   |
