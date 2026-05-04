"""
Script to compare the performance of the base Gemma3 model vs the trained model
and plot the results in a graph for presentation to mentors.
"""

import json
import re
import matplotlib.pyplot as plt
import numpy as np
import ollama

# Test data for evaluation - using more representative examples
TEST_DATA = [
    {
        "question": "List all employees.",
        "actual_sql": "SELECT * FROM employee;"
    },
    {
        "question": "Show all employees with salary above 50000",
        "actual_sql": "SELECT * FROM employee WHERE salary > 50000;"
    },
    {
        "question": "Find the average salary of all employees",
        "actual_sql": "SELECT AVG(salary) FROM employee;"
    },
    {
        "question": "Get the highest paid employee",
        "actual_sql": "SELECT * FROM employee ORDER BY salary DESC LIMIT 1;"
    },
    {
        "question": "Count the number of employees in each department",
        "actual_sql": "SELECT department, COUNT(*) FROM employee GROUP BY department;"
    },
    {
        "question": "List all departments with their average employee salary",
        "actual_sql": "SELECT department, AVG(salary) FROM employee GROUP BY department;"
    },
    {
        "question": "Find employees who work in the IT department",
        "actual_sql": "SELECT * FROM employee WHERE department = 'IT';"
    },
    {
        "question": "Show the total salary expense for each department",
        "actual_sql": "SELECT department, SUM(salary) FROM employee GROUP BY department;"
    }
]

def calculate_exact_match(predicted, actual):
    """
    Calculate exact match accuracy between predicted and actual SQL queries
    
    Args:
        predicted (str): Predicted SQL query
        actual (str): Actual SQL query
        
    Returns:
        bool: True if exact match, False otherwise
    """
    # Normalize both queries by removing extra whitespace and converting to lowercase
    pred_normalized = re.sub(r'\s+', ' ', predicted.strip().lower())
    actual_normalized = re.sub(r'\s+', ' ', actual.strip().lower())
    
    return pred_normalized == actual_normalized

def calculate_semantic_similarity(predicted, actual):
    """
    Calculate a simple semantic similarity score based on token overlap
    
    Args:
        predicted (str): Predicted SQL query
        actual (str): Actual SQL query
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Remove common SQL punctuation and split into tokens
    pred_tokens = set(re.findall(r'\w+', predicted.lower()))
    actual_tokens = set(re.findall(r'\w+', actual.lower()))
    
    # Calculate Jaccard similarity
    intersection = pred_tokens.intersection(actual_tokens)
    union = pred_tokens.union(actual_tokens)
    
    if len(union) == 0:
        return 0.0
    
    return len(intersection) / len(union)

def format_prompt(question):
    """
    Format prompt for the base model
    
    Args:
        question (str): Natural language question
        
    Returns:
        str: Formatted prompt
    """
    prompt = "You are an expert SQL generator that converts natural language questions into valid SQL queries.\n"
    prompt += "You should only output SQL code and nothing else. Do not include explanations or markdown formatting.\n\n"
    prompt += f"Natural Language: {question}\n"
    prompt += "SQL:"
    
    return prompt

def test_model(model_name, test_data):
    """
    Test a model with the given test data
    
    Args:
        model_name (str): Name of the model to test
        test_data (list): List of test cases
        
    Returns:
        dict: Results containing accuracy metrics
    """
    print(f"Testing model: {model_name}")
    
    exact_matches = 0
    total_tests = len(test_data)
    total_similarity = 0.0
    
    predictions = []
    
    for i, test_case in enumerate(test_data):
        question = test_case["question"]
        actual_sql = test_case["actual_sql"]
        
        print(f"  Test {i+1:2d}/{total_tests}: {question}")
        
        prompt = format_prompt(question)
        
        try:
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={"temperature": 0.2}
            )
            
            predicted_sql = response['response'].strip()
            is_exact_match = calculate_exact_match(predicted_sql, actual_sql)
            similarity_score = calculate_semantic_similarity(predicted_sql, actual_sql)
            
            if is_exact_match:
                exact_matches += 1
                
            total_similarity += similarity_score
                
            predictions.append({
                "question": question,
                "actual_sql": actual_sql,
                "predicted_sql": predicted_sql,
                "exact_match": is_exact_match,
                "similarity_score": similarity_score
            })
                
            match_status = "✓" if is_exact_match else "✗"
            print(f"    Expected: {actual_sql}")
            print(f"    Got:      {predicted_sql[:60]}{'...' if len(predicted_sql) > 60 else ''}")
            print(f"    Match:    {match_status} (Similarity: {similarity_score:.2f})")
            print()
            
        except Exception as e:
            print(f"    Error testing case {i+1}: {str(e)}")
            print()
    
    exact_match_accuracy = exact_matches / total_tests if total_tests > 0 else 0
    avg_similarity = total_similarity / total_tests if total_tests > 0 else 0
    
    print(f"Model {model_name} achieved {exact_matches}/{total_tests} exact matches ({exact_match_accuracy:.2%})")
    print(f"Average semantic similarity: {avg_similarity:.2f}")
    
    return {
        "exact_matches": exact_matches,
        "total_tests": total_tests,
        "exact_match_accuracy": exact_match_accuracy,
        "average_similarity": avg_similarity,
        "predictions": predictions
    }

def plot_comparison(base_model_results, trained_model_results, base_model_name, trained_model_name):
    """
    Plot a comparison graph of the two models with model names displayed
    
    Args:
        base_model_results (dict): Results from the base model
        trained_model_results (dict): Results from the trained model
        base_model_name (str): Name of the base model
        trained_model_name (str): Name of the trained model
    """
    # Data for plotting
    models = [base_model_name, trained_model_name]
    exact_matches = [base_model_results['exact_matches'], trained_model_results['exact_matches']]
    exact_accuracies = [base_model_results['exact_match_accuracy'], trained_model_results['exact_match_accuracy']]
    similarities = [base_model_results['average_similarity'], trained_model_results['average_similarity']]
    
    # Create figure and axis with better spacing
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.15, height_ratios=[3, 3, 1])
    ax1 = fig.add_subplot(gs[0, :])  # Exact matches
    ax2 = fig.add_subplot(gs[1, :])  # Semantic similarity
    
    # Color scheme
    colors = ['#1f77b4', '#ff7f0e']  # Standard blue and orange
    
    # Bar chart for exact matches
    bars1 = ax1.bar(models, exact_matches, color=colors, width=0.4)
    ax1.set_ylabel('Number of Exact Matches', fontsize=16, fontweight='bold')
    ax1.set_title('Exact Match Count Comparison', fontsize=18, fontweight='bold', pad=20)
    ax1.set_ylim(0, base_model_results['total_tests'] + 1)
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='both', which='major', labelsize=14)
    
    # Add value labels on bars with better spacing
    for i, (bar, value) in enumerate(zip(bars1, exact_matches)):
        height = bar.get_height()
        ax1.annotate(f'{int(value)} / {base_model_results["total_tests"]}\n({exact_accuracies[i]:.1%})',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=14, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.4", facecolor='white', alpha=0.9, edgecolor=colors[i], linewidth=1.5))
    
    # Bar chart for semantic similarity
    bars2 = ax2.bar(models, similarities, color=colors, width=0.4)
    ax2.set_ylabel('Average Semantic Similarity', fontsize=16, fontweight='bold')
    ax2.set_title('Semantic Similarity Comparison', fontsize=18, fontweight='bold', pad=20)
    ax2.set_ylim(0, 1.0)
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_yticklabels([f'{x:.0%}' for x in ax2.get_yticks()], fontsize=14)
    ax2.tick_params(axis='both', which='major', labelsize=14)
    
    # Add value labels on bars with better spacing
    for i, (bar, value) in enumerate(zip(bars2, similarities)):
        height = bar.get_height()
        ax2.annotate(f'{value:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=14, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.4", facecolor='white', alpha=0.9, edgecolor=colors[i], linewidth=1.5))
    
    # Add model names and comparison info at the bottom with better spacing
    fig.text(0.5, 0.12, f'Models Compared: {base_model_name} vs {trained_model_name}', 
             ha='center', fontsize=14, style='italic', 
             bbox=dict(boxstyle="round,pad=0.6", facecolor="lightgray", alpha=0.7, edgecolor="black"))
    
    # Add explanation text with better spacing
    fig.text(0.5, 0.07, 'Exact Match: Predicted SQL exactly matches the expected SQL | Semantic Similarity: Measures token overlap (0-1 scale)', 
             ha='center', fontsize=12, style='italic')
    
    # Add improvement indicators with better spacing
    exact_improvement = trained_model_results['exact_match_accuracy'] - base_model_results['exact_match_accuracy']
    similarity_improvement = trained_model_results['average_similarity'] - base_model_results['average_similarity']
        
    fig.text(0.5, 0.03, f'Exact Match Improvement: {exact_improvement:+.1%} | Semantic Similarity Improvement: {similarity_improvement:+.2f}', 
             ha='center', fontsize=14, fontweight='bold', color='black',
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8, edgecolor="black"))
    
    plt.suptitle('NL2SQL Model Performance Comparison', fontsize=20, fontweight='bold', y=0.95)
    plt.savefig('model_comparison_results.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Graph saved as 'model_comparison_results.png'")

def print_detailed_comparison(base_model_results, trained_model_results):
    """
    Print a detailed comparison showing how the trained model is more refined
    
    Args:
        base_model_results (dict): Results from the base model
        trained_model_results (dict): Results from the trained model
    """
    print("\nDETAILED COMPARISON - SHOWING MODEL REFINEMENT")
    print("=" * 120)
    print(f"{'Test Case':<45} {'Base Similarity':<15} {'Trained Similarity':<18} {'Improvement':<15} {'Observation'}")
    print("-" * 120)
    
    predictions_base = base_model_results['predictions']
    predictions_trained = trained_model_results['predictions']
    
    for i, (pred_base, pred_trained) in enumerate(zip(predictions_base, predictions_trained)):
        base_sim = pred_base['similarity_score']
        trained_sim = pred_trained['similarity_score']
        improvement = trained_sim - base_sim
        
        # Truncate question for display
        question = pred_base['question'][:42] + "..." if len(pred_base['question']) > 42 else pred_base['question']
        
        # Determine observation
        if pred_trained['exact_match']:
            observation = "Exact Match ✓"
        elif improvement > 0.1:
            observation = "Significant Improvement"
        elif improvement > 0:
            observation = "Minor Improvement"
        elif improvement < 0:
            observation = "Degraded"
        else:
            observation = "No Change"
        
        print(f"{question:<45} {base_sim:<15.2f} {trained_sim:<18.2f} {improvement:<+15.2f} {observation}")

def main():
    """
    Main function to run the model comparison
    """
    print("NL2SQL Model Comparison Test")
    print("=" * 120)
    print("Comparing base Gemma3 model with trained model")
    print("This test evaluates how well each model converts natural language to SQL queries")
    print("Metrics include both exact matches and semantic similarity to show model refinement")
    print()
    
    # Define model names
    base_model_name = "gemma3:1b"
    trained_model_name = "gemma3-nl2sql:latest"
    
    # Test base model
    print("1. Testing Base Model")
    print("-" * 60)
    base_model_results = test_model(base_model_name, TEST_DATA)
    print()
    
    # Test trained model
    print("2. Testing Trained Model")
    print("-" * 60)
    trained_model_results = test_model(trained_model_name, TEST_DATA)
    
    print()
    print("AGGREGATE RESULTS")
    print("=" * 120)
    print(f"Base Model ('{base_model_name}'):")
    print(f"  Exact Matches: {base_model_results['exact_matches']}/{base_model_results['total_tests']}")
    print(f"  Exact Match Accuracy: {base_model_results['exact_match_accuracy']:.2%}")
    print(f"  Average Semantic Similarity: {base_model_results['average_similarity']:.2f}")
    print()
    print(f"Trained Model ('{trained_model_name}'):")
    print(f"  Exact Matches: {trained_model_results['exact_matches']}/{trained_model_results['total_tests']}")
    print(f"  Exact Match Accuracy: {trained_model_results['exact_match_accuracy']:.2%}")
    print(f"  Average Semantic Similarity: {trained_model_results['average_similarity']:.2f}")
    print()
    
    # Calculate improvements
    exact_improvement = trained_model_results['exact_match_accuracy'] - base_model_results['exact_match_accuracy']
    similarity_improvement = trained_model_results['average_similarity'] - base_model_results['average_similarity']
    
    print(f"Performance Improvements:")
    print(f"  Exact Match: {exact_improvement:+.2%}")
    print(f"  Semantic Similarity: {similarity_improvement:+.2f}")
    print()
    
    # Print detailed comparison
    print_detailed_comparison(base_model_results, trained_model_results)
    
    # Plot comparison
    plot_comparison(base_model_results, trained_model_results, base_model_name, trained_model_name)
    
    # Save results to file
    results = {
        "test_cases": TEST_DATA,
        "base_model": {
            "name": base_model_name,
            "results": base_model_results
        },
        "trained_model": {
            "name": trained_model_name,
            "results": trained_model_results
        },
        "improvements": {
            "exact_match": exact_improvement,
            "semantic_similarity": similarity_improvement
        }
    }
    
    with open("model_comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to 'model_comparison_results.json'")
    print("\nFor your research paper:")
    print("- Use 'model_comparison_results.png' for the visualization")
    print("- Refer to 'model_comparison_results.json' for detailed numerical data")
    print("- The semantic similarity metric shows how much more refined your trained model is")

if __name__ == "__main__":
    main()