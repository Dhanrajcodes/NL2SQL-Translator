# Clean Project Structure

## Root Directory
```
NL2SQL/
├── app/                 # Application code (UI and API)
├── data/                # Dataset files and processed data
├── docs/                # Project documentation
├── models/              # Saved models (if any)
├── scripts/             # Utility and evaluation scripts
├── results/             # Evaluation results and metrics
├── requirements.txt     # Python dependencies
├── README.md            # Project overview and instructions
├── run_project.py       # Main script to run the complete project
└── PROJECT_STRUCTURE.md # This file
```

## App Directory
```
app/
├── ui.py               # Streamlit user interface
└── app.py              # Flask API backend
```

## Data Directory
```
data/
├── spider/             # Spider dataset files
├── wikisql/            # WikiSQL dataset files (when downloaded)
├── spider_train.json   # Processed Spider training data
├── spider_test.json    # Processed Spider test data
├── wikisql_train.json  # Processed WikiSQL training data
├── wikisql_test.json   # Processed WikiSQL test data
└── finetuning_dataset.jsonl # Dataset for Ollama fine-tuning
```

## Docs Directory
```
docs/
├── methodology.md      # Research methodology
├── architecture.md     # System architecture
├── timeline.md         # Project timeline
└── research_paper_draft.md # Research paper draft
```

## Scripts Directory
```
scripts/
├── download_spider.py        # Download and process Spider dataset
├── download_wikisql.py       # Download and process WikiSQL dataset
├── gemma_qlora_finetune.py   # QLoRA fine-tuning for limited hardware
├── finetune_with_datasets.py # Full fine-tuning (requires access)
├── evaluate_model.py         # Model evaluation script
├── demonstration.py          # Demonstration of enhancements
├── schema_aware_prompting.py # Schema-aware prompting techniques
└── prepare_*                 # Data preparation scripts
```

## Results Directory
```
results/
├── evaluation_results.json   # Model evaluation metrics
└── *.png                     # Performance visualization charts
```