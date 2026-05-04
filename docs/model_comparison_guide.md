# Model Comparison Test Guide

This document explains how to use the model comparison script to evaluate and visualize the performance difference between the base Gemma3 model and the trained model.

## Overview

The `model_comparison_test.py` script performs the following functions:

1. Tests both the base Gemma3 model (`gemma3:1b`) and the trained model (`gemma3-nl2sql`)
2. Evaluates each model using a set of predefined natural language to SQL conversion tasks
3. Calculates exact match accuracy for each model
4. Generates a visual comparison graph showing the performance differences
5. Saves the results to a JSON file for future reference

## Prerequisites

Before running the script, ensure you have:

1. Installed all project dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Ollama installed and running

3. The base Gemma3 model pulled:
   ```
   ollama pull gemma3:1b
   ```

4. Created the trained model (if applicable):
   ```
   ollama create gemma3-nl2sql -f Modelfile
   ```

## Running the Script

To run the model comparison test:

```bash
cd scripts
python model_comparison_test.py
```

## Output Files

After running the script, the following files will be generated:

1. `model_comparison_results.png` - A graph comparing the performance of both models
2. `model_comparison_results.json` - Detailed numerical results in JSON format

## Interpreting Results

The script will display the results in the console and generate a visualization:

- **Exact Matches**: Number of test cases where the predicted SQL exactly matched the expected SQL
- **Accuracy**: Percentage of exact matches over total test cases

The visualization contains two charts:
1. Exact Matches Comparison - Shows the raw count of exact matches for each model
2. Accuracy Comparison - Shows the accuracy percentage for each model

## Customizing Test Cases

You can modify the test cases by editing the `TEST_DATA` array in the `model_comparison_test.py` script. Each test case should include:

```python
{
    "question": "Natural language question",
    "actual_sql": "Expected SQL query"
}
```

## Troubleshooting

### Trained Model Not Found

If you see a message that the trained model was not found, make sure you have created it using:

```bash
ollama create gemma3-nl2sql -f Modelfile
```

### Connection Errors

If you encounter connection errors with Ollama:

1. Make sure Ollama is running:
   ```bash
   ollama serve
   ```

2. Verify that the base model is available:
   ```bash
   ollama list
   ```

## Example Output

```
NL2SQL Model Comparison Test
==================================================
Comparing base Gemma3 model with trained model

Testing model: gemma3:1b
  Testing case 1/5: Show all employees with salary above 50000
    Actual:    SELECT * FROM employee WHERE salary > 50000
    Predicted: SELECT * FROM employee WHERE salary > 50000
    Exact Match: True
  ...

FINAL RESULTS
==================================================
Base Model ('gemma3:1b'):
  Exact Matches: 3/5
  Accuracy: 60.00%

Trained Model:
  Exact Matches: 4/5
  Accuracy: 80.00%
```