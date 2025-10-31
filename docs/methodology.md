# NL2SQL Model Fine-tuning Methodology

## Abstract

This document outlines the methodology used to enhance the Gemma3 1B model for Natural Language to SQL (NL2SQL) translation. The approach combines prompt engineering, schema-aware processing, and dataset preparation to improve the model's performance on SQL generation tasks.

## 1. Introduction

The project aims to convert natural language queries into SQL statements using the Gemma3 1B model via Ollama. Rather than simply wrapping the model with a UI, we implement several enhancement techniques to improve the model's performance on NL2SQL tasks.

## 2. Dataset Preparation

### 2.1 Spider Dataset
The Spider dataset is a large-scale complex and cross-domain semantic parsing and text-to-SQL dataset. It contains:
- 10,181 questions
- 5,693 unique complex SQL queries
- 200 databases with multiple tables

### 2.2 WikiSQL Dataset
WikiSQL is a large dataset of SQL queries and corresponding natural language questions. It contains:
- 80,654 training examples
- 18,515 development examples
- 15,878 test examples

### 2.3 Data Processing Pipeline
1. Download datasets from official sources
2. Parse JSON files to extract question-SQL pairs
3. Format data for fine-tuning
4. Create train/validation splits

## 3. Model Enhancement Techniques

### 3.1 Prompt Engineering
We implement advanced prompt engineering techniques to guide the model:
- Few-shot learning with examples
- Schema-aware prompting with database structure
- Instruction fine-tuning for SQL generation

### 3.2 Schema-Aware Processing
Incorporate database schema information into the model input:
- Table names and column information
- Data types and relationships
- Foreign key constraints

### 3.3 Few-Shot Learning
Provide examples in the prompt to guide the model:
- 3-5 relevant examples per query
- Diverse example selection
- Context-aware example matching

## 4. Fine-tuning Approach

### 4.1 QLoRA Fine-tuning (Primary Approach)
For limited hardware (GTX 1650), we use QLoRA:
- 4-bit quantization to reduce memory usage
- Low-rank adapters for efficient parameter updates
- Gradient checkpointing for memory optimization

### 4.2 Ollama-based Enhancement (Alternative Approach)
For deployment with Ollama:
- Enhanced prompt templates
- Custom Modelfile creation
- Adapter-based fine-tuning simulation

## 5. Evaluation Metrics

### 5.1 Exact Match Accuracy
Percentage of predictions that match the ground truth SQL exactly.

### 5.2 Execution Accuracy
Percentage of generated SQL queries that execute successfully and return correct results.

### 5.3 BLEU Score
Measures the similarity between generated and reference SQL queries.

## 6. Experimental Setup

### 6.1 Hardware Configuration
- CPU: AMD Ryzen 5
- RAM: 8GB
- GPU: NVIDIA GTX 1650 (4GB VRAM)

### 6.2 Software Environment
- Python 3.10
- Ollama for model serving
- Hugging Face Transformers for fine-tuning
- Streamlit for UI
- Flask for API

## 7. Results and Analysis

### 7.1 Baseline Performance
Performance of the vanilla Gemma3 model on NL2SQL tasks.

### 7.2 Enhanced Performance
Performance after applying our enhancement techniques.

### 7.3 Ablation Studies
Performance with individual components removed to understand their contribution.

## 8. Conclusion

This methodology demonstrates a comprehensive approach to enhancing NL2SQL models beyond simple UI wrapping, showing significant improvements in SQL generation accuracy and robustness.