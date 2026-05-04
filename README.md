# NL2SQL Project: Enhancing Gemma3 for Natural Language to SQL Translation

This project converts natural language queries into SQL using the Gemma3 1B model via Ollama. Unlike simple UI wrappers, this implementation demonstrates significant enhancements through prompt engineering, schema-aware processing, and parameter-efficient fine-tuning techniques.

## Research Contributions

This project goes beyond a simple UI wrapper by implementing:
1. **Schema-Aware Prompting**: Incorporating database schema information in model inputs
2. **Few-Shot Learning**: Using examples to guide the model's SQL generation
3. **Parameter-Efficient Fine-tuning**: QLoRA implementation for limited hardware
4. **Comprehensive Evaluation**: Multiple metrics to assess performance
5. **Dynamic Schema Extraction**: Automatically extracting schema information from uploaded databases
6. **Contextual SQL Generation**: Using relationship mapping to improve JOIN operations

## Setup

1. Install Ollama from https://ollama.com/
2. Pull the Gemma3 1B model:
   ```bash
   ollama pull gemma3:1b
   ```
3. Install project dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Project

Start both frontend and backend:
```bash
python run_project.py
```

Or run them separately:
- Frontend: `streamlit run app/ui.py`
- Backend: `python app/app.py`

## Project Highlights

### Dynamic Schema Extraction and Contextual SQL Generation
A major enhancement to the system that enables automatic database schema extraction and contextual SQL generation. This feature allows users to upload their database files directly, and the system will:

- Automatically detect and extract table structures
- Identify primary keys, foreign keys, and relationships
- Generate more accurate SQL queries based on actual schema information
- Suggest appropriate JOIN operations based on table relationships

### Model Comparison

You can compare the performance of the base Gemma3 model with your trained model using the dedicated comparison script:

```bash
python scripts/model_comparison_test.py
```

This will generate a visual comparison graph (`model_comparison_results.png`) and save detailed results to `model_comparison_results.json`. See [Model Comparison Guide](docs/model_comparison_guide.md) for more details.

## Using the Enhanced Schema Feature

The new schema extraction feature can be accessed through the UI:

1. **Upload Database File**: Use the file uploader to provide your database file (SQLite format)
2. **Enter Natural Language Query**: Describe the SQL query you want to generate
3. **Generate with Context**: The system will analyze your database schema and generate more accurate SQL

Alternatively, you can use the API endpoint directly:

```bash
curl -X POST http://localhost:5000/translate_with_context \
  -F "question=Show all employees and their department names" \
  -F "db_file=@path/to/your/database.db"
```

## Project Structure

```
NL2SQL/
├── app/                 # Application code (UI and API)
├── data/                # Dataset files and processed data
├── docs/                # Project documentation
├── models/              # Saved models (if any)
├── scripts/             # Utility and evaluation scripts
├── results/             # Evaluation results and metrics
├── utils/               # Utility modules (new!)
│   ├── schema_extractor.py      # Database schema extraction
│   ├── relationship_mapper.py   # Table relationship analysis
│   └── contextual_prompter.py   # Enhanced prompt generation
├── requirements.txt     # Python dependencies
├── README.md            # Project overview and instructions
└── run_project.py       # Main script to run the complete project
```

## Benchmark Datasets

The most commonly used benchmark datasets for NL2SQL are:

### Spider Dataset (Most Popular for Research)
- Covers multiple databases and complex queries
- Official repository: https://github.com/taoyds/spider
- Direct download link: https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV
- Contains 10,181 questions and 5,693 unique complex SQL queries across 200 databases

### WikiSQL (Simpler, Good for Beginners)
- Large dataset but mostly single-table queries
- Official repository: https://github.com/salesforce/WikiSQL
- Contains 80,654 training examples, 18,515 development examples, and 15,878 test examples

### Spider2 (Newer Enterprise-Focused Dataset)
- More complex enterprise-level workflows
- Official repository: https://github.com/xlang-ai/Spider2
- Contains real-world enterprise scenarios
- More complex setup requirements

**Note**: For this college project, we recommend using the original Spider dataset as it's more established and suitable for educational purposes. Spider2 is more complex and requires enterprise database access.

## Downloading and Processing Datasets

To download and process the real datasets:

1. **Get detailed download instructions**:
   ```bash
   python scripts/download_real_datasets.py
   ```

2. **Manual Download Steps**:

   **For Spider Dataset**:
   ```bash
   # Create directory
   mkdir -p data/spider
   
   # Download manually from:
   # https://drive.google.com/uc?export=download&id=1_AckYkinAnhqmRQtGsQgXuudkLZj6bUV
   
   # Extract to data/spider/
   ```

   **For WikiSQL Dataset**:
   ```bash
   # Create directory
   mkdir -p data/wikisql
   
   # Download manually from the WikiSQL GitHub repository
   # Extract to data/wikisql/
   ```

3. **Process Datasets**:
   ```bash
   python scripts/download_spider_original.py
   python scripts/download_wikisql_proper.py
   ```

4. **Prepare data for fine-tuning**:
   ```bash
   python scripts/prepare_finetuning.py
   ```

These scripts will process the datasets into the required format for fine-tuning.

## Fine-tuning for Better Performance

For limited hardware like our GTX 1650, we recommend using the QLoRA fine-tuning approach:

1. **Install additional dependencies**:
   ```bash
   pip install datasets accelerate bitsandbytes peft trl
   ```

2. **Prepare data for fine-tuning**:
   ```bash
   python scripts/prepare_finetuning.py
   ```

3. **Fine-tune Gemma3 model using QLoRA** (optimized for limited hardware):
   ```bash
   python scripts/finetune_with_datasets.py
   ```

This approach uses 4-bit quantization and LoRA adapters to significantly reduce memory requirements while still achieving good performance.

If you have access to more powerful hardware and want to fine-tune the full model:

1. **Register for access** to the Gemma model at https://huggingface.co/google/gemma-2b
2. **Authenticate** with Hugging Face:
   ```bash
   huggingface-cli login
   ```
3. **Run full fine-tuning**:
   ```bash
   python scripts/finetune_with_datasets.py
   ```

## Ollama-based Enhancement

For deployment with Ollama, you can create an enhanced model:

1. **Prepare the dataset**:
   ```bash
   python scripts/prepare_finetuning.py
   ```

2. **Create a Modelfile**:
   ```dockerfile
   FROM gemma3:1b
   
   SYSTEM """You are an expert SQL generator that converts natural language questions into valid SQL queries. Only output SQL code."""
   
   PARAMETER temperature 0.2
   PARAMETER top_p 0.9
   
   ADAPTER data/finetuning_dataset.jsonl
   ```

3. **Create enhanced model**:
   ```bash
   ollama create gemma3-nl2sql -f Modelfile
   ```

## Schema-Aware SQL Generation

For better results with complex queries, provide database schema information:

1. In the Streamlit UI, use the "Database Schema" expander to provide schema information
2. In the API, include the schema in your request:
   ```bash
   curl -X POST http://localhost:5000/translate \
     -H "Content-Type: application/json" \
     -d '{
       "question": "Show all employees with salary above 50000",
       "schema": {
         "employees": {
           "columns": [
             {"name": "id", "type": "INTEGER"},
             {"name": "name", "type": "TEXT"},
             {"name": "salary", "type": "INTEGER"}
           ]
         }
       }
     }'
   ```

## New Schema Extraction Feature

The new dynamic schema extraction feature works as follows:

1. **Automatic Schema Detection**: Upload your database file and the system automatically detects tables, columns, and relationships
2. **Relationship Mapping**: Identifies foreign key relationships to suggest appropriate JOIN operations
3. **Contextual Prompting**: Generates enhanced prompts with detailed schema information
4. **Improved Accuracy**: Uses actual database structure to generate more accurate SQL queries

## Evaluation

To evaluate the model performance:

```bash
python scripts/evaluate_model.py
```

This will generate metrics including:
- Exact Match Accuracy
- BLEU Score
- Execution Accuracy (planned)

## Documentation

The project includes comprehensive documentation:
- [Methodology](docs/methodology.md): Detailed approach and techniques
- [Architecture](docs/architecture.md): System design and components
- [Timeline](docs/timeline.md): Project development schedule
- [Research Paper Draft](docs/research_paper_draft.md): Academic paper draft

## Hardware Configuration

The system is designed to work on limited hardware:
- CPU: AMD Ryzen 5
- RAM: 8GB
- GPU: NVIDIA GTX 1650 (4GB VRAM)

## Research Significance

This project demonstrates that meaningful NL2SQL enhancements can be achieved on consumer-grade hardware, making this technology accessible to organizations with constrained computational resources. The implementation shows that value can be added beyond simple UI wrapping through:

1. **Advanced Prompt Engineering**: Schema-aware and few-shot learning techniques
2. **Dynamic Schema Extraction**: Automatically analyzing database structures for improved accuracy
3. **Relationship Mapping**: Understanding table relationships to suggest appropriate JOIN operations
4. **Contextual Prompting**: Creating enhanced prompts based on actual database schemas
5. **Hardware-Optimized Fine-tuning**: QLoRA implementation for limited VRAM
6. **Comprehensive Evaluation**: Multiple metrics to assess performance
7. **Reproducible Research**: Complete documentation and code

## Future Work

1. Integration with larger models when hardware permits
2. Execution-based validation by connecting to actual databases
3. Active learning from user feedback
4. Multi-dialect SQL support