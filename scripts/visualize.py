"""
Visualization script for training progress and model evaluation
"""

import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime

def plot_training_progress(log_dir='../logs'):
    """
    Plot training progress from log files
    
    Args:
        log_dir (str): Directory containing training logs
    """
    # Find the most recent log directory
    log_dirs = [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]
    if not log_dirs:
        print("No training logs found.")
        return
    
    # Sort by timestamp and get the most recent
    log_dirs.sort(reverse=True)
    latest_log_dir = log_dirs[0]
    log_file = os.path.join(log_dir, latest_log_dir, 'training_logs.json')
    
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    # Load training logs
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    # Extract training metrics
    epochs = []
    train_losses = []
    eval_losses = []
    learning_rates = []
    
    for log in logs:
        if 'epoch' in log:
            epochs.append(log['epoch'])
            if 'loss' in log:
                train_losses.append(log['loss'])
            if 'eval_loss' in log:
                eval_losses.append(log['eval_loss'])
            if 'learning_rate' in log:
                learning_rates.append(log['learning_rate'])
    
    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Training Progress', fontsize=16)
    
    # Plot training loss
    if train_losses:
        axes[0, 0].plot(epochs[:len(train_losses)], train_losses, 'b-', marker='o')
        axes[0, 0].set_title('Training Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].grid(True)
    
    # Plot evaluation loss
    if eval_losses:
        axes[0, 1].plot(epochs[:len(eval_losses)], eval_losses, 'r-', marker='o')
        axes[0, 1].set_title('Evaluation Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].grid(True)
    
    # Plot learning rate
    if learning_rates:
        axes[1, 0].plot(epochs[:len(learning_rates)], learning_rates, 'g-', marker='o')
        axes[1, 0].set_title('Learning Rate')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Learning Rate')
        axes[1, 0].grid(True)
    
    # Plot loss comparison
    if train_losses and eval_losses:
        min_len = min(len(train_losses), len(eval_losses))
        axes[1, 1].plot(epochs[:min_len], train_losses[:min_len], 'b-', marker='o', label='Training')
        axes[1, 1].plot(epochs[:min_len], eval_losses[:min_len], 'r-', marker='s', label='Evaluation')
        axes[1, 1].set_title('Training vs Evaluation Loss')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Loss')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
    
    plt.tight_layout()
    plt.savefig('../docs/training_progress.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Training progress plot saved to ../docs/training_progress.png")

def plot_model_comparison():
    """
    Plot comparison of different model checkpoints or versions
    """
    # This would typically load results from different models and compare them
    # For now, we'll create a placeholder
    models = ['T5-small (WikiSQL)', 'T5-base (WikiSQL)', 'T5-small (Spider)']
    exact_match = [0.65, 0.72, 0.58]
    bleu_scores = [0.78, 0.82, 0.71]
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    
    x = np.arange(len(models))
    width = 0.35
    
    ax.bar(x - width/2, exact_match, width, label='Exact Match Accuracy', alpha=0.8)
    ax.bar(x + width/2, bleu_scores, width, label='BLEU Score', alpha=0.8)
    
    ax.set_xlabel('Model Configuration')
    ax.set_ylabel('Score')
    ax.set_title('Model Performance Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('../docs/model_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Model comparison plot saved to ../docs/model_comparison.png")

def main():
    """
    Main visualization function
    """
    print("Generating visualizations...")
    
    # Create docs directory if it doesn't exist
    os.makedirs('../docs', exist_ok=True)
    
    # Plot training progress
    plot_training_progress()
    
    # Plot model comparison
    plot_model_comparison()
    
    print("Visualizations complete!")

if __name__ == "__main__":
    main()