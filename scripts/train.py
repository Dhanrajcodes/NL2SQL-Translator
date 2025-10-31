"""
Training script for fine-tuning T5 model for NL2SQL task
"""

import torch
from transformers import (
    T5ForConditionalGeneration, 
    T5Tokenizer, 
    Trainer, 
    TrainingArguments,
    AutoConfig
)
from datasets import Dataset
import json
import pandas as pd
import sys
import os
import argparse
from datetime import datetime
import numpy as np

# Add parent directory to path to import preprocessing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.preprocess import load_dataset, preprocess_for_t5

def prepare_training_data(train_path, test_path):
    """
    Prepare training data for the model
    
    Args:
        train_path (str): Path to training data
        test_path (str): Path to test data
    
    Returns:
        tuple: Training and validation datasets
    """
    # Load datasets
    train_df, test_df = load_dataset(train_path, test_path)
    
    # Initialize tokenizer
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    
    # Preprocess data
    train_encodings = preprocess_for_t5(train_df, tokenizer)
    test_encodings = preprocess_for_t5(test_df, tokenizer)
    
    # Convert to Dataset format
    train_dataset = Dataset.from_dict({
        'input_ids': train_encodings['input_ids'],
        'attention_mask': train_encodings['attention_mask'],
        'labels': train_encodings['labels']
    })
    
    test_dataset = Dataset.from_dict({
        'input_ids': test_encodings['input_ids'],
        'attention_mask': test_encodings['attention_mask'],
        'labels': test_encodings['labels']
    })
    
    return train_dataset, test_dataset, tokenizer

def train_model(train_dataset, test_dataset, output_dir='../models/t5_nl2sql', 
                hyperparams=None):
    """
    Train the T5 model for NL2SQL task
    
    Args:
        train_dataset: Training dataset
        test_dataset: Test/validation dataset
        output_dir (str): Directory to save the trained model
        hyperparams (dict): Dictionary of hyperparameters
    """
    # Default hyperparameters
    if hyperparams is None:
        hyperparams = {
            'num_train_epochs': 3,
            'per_device_train_batch_size': 4,
            'per_device_eval_batch_size': 4,
            'warmup_steps': 500,
            'weight_decay': 0.01,
            'learning_rate': 5e-5,
            'logging_steps': 10,
            'save_total_limit': 3,
        }
    
    # Load model
    model = T5ForConditionalGeneration.from_pretrained('t5-small')
    
    # Create timestamp for logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = f'./logs/{timestamp}'
    os.makedirs(log_dir, exist_ok=True)
    
    # Define training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=hyperparams['num_train_epochs'],
        per_device_train_batch_size=hyperparams['per_device_train_batch_size'],
        per_device_eval_batch_size=hyperparams['per_device_eval_batch_size'],
        warmup_steps=hyperparams['warmup_steps'],
        weight_decay=hyperparams['weight_decay'],
        learning_rate=hyperparams['learning_rate'],
        logging_dir=log_dir,
        logging_steps=hyperparams['logging_steps'],
        evaluation_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        save_total_limit=hyperparams['save_total_limit'],
        fp16=torch.cuda.is_available(),  # Use mixed precision if CUDA is available
        dataloader_num_workers=4,
        report_to=None,  # Disable external tracking for simplicity
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
    )
    
    # Start training
    trainer.train()
    
    # Save model
    trainer.save_model(output_dir)
    
    # Save training logs
    log_history = trainer.state.log_history
    log_file = os.path.join(log_dir, 'training_logs.json')
    with open(log_file, 'w') as f:
        json.dump(log_history, f, indent=2)
    
    print(f"Training logs saved to {log_file}")
    
    return trainer

def hyperparameter_search(train_dataset, test_dataset):
    """
    Perform basic hyperparameter search
    
    Args:
        train_dataset: Training dataset
        test_dataset: Test/validation dataset
    
    Returns:
        dict: Best hyperparameters
    """
    print("Performing hyperparameter search...")
    
    # Define hyperparameter space
    learning_rates = [3e-5, 5e-5, 1e-4]
    batch_sizes = [2, 4, 8]
    best_score = 0
    best_params = None
    
    # Simple grid search (in practice, you might want to use more sophisticated methods)
    for lr in learning_rates:
        for batch_size in batch_sizes:
            print(f"Testing: learning_rate={lr}, batch_size={batch_size}")
            
            # Train with current parameters
            hyperparams = {
                'num_train_epochs': 1,  # Short training for search
                'per_device_train_batch_size': batch_size,
                'per_device_eval_batch_size': batch_size,
                'warmup_steps': 100,
                'weight_decay': 0.01,
                'learning_rate': lr,
                'logging_steps': 10,
                'save_total_limit': 2,
            }
            
            try:
                trainer = train_model(
                    train_dataset, 
                    test_dataset, 
                    output_dir='../models/temp_model',
                    hyperparams=hyperparams
                )
                
                # Get evaluation score
                eval_result = trainer.evaluate()
                eval_loss = eval_result['eval_loss']
                
                # Convert loss to score (lower loss is better)
                score = -eval_loss
                
                print(f"  Eval loss: {eval_loss:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_params = hyperparams.copy()
                    print(f"  New best parameters found!")
                    
            except Exception as e:
                print(f"  Error with parameters: {e}")
                continue
    
    print(f"Best hyperparameters: {best_params}")
    return best_params

def main():
    """
    Main training function
    """
    parser = argparse.ArgumentParser(description='Train NL2SQL model')
    parser.add_argument('--dataset', type=str, default='wikisql', 
                        choices=['wikisql', 'spider'],
                        help='Dataset to use for training')
    parser.add_argument('--hyperparam-search', action='store_true',
                        help='Perform hyperparameter search')
    parser.add_argument('--epochs', type=int, default=3,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=4,
                        help='Training batch size')
    parser.add_argument('--learning-rate', type=float, default=5e-5,
                        help='Learning rate')
    
    args = parser.parse_args()
    
    print("Starting NL2SQL Model Training")
    print("==============================")
    
    # Determine dataset paths based on selection
    if args.dataset == 'wikisql':
        train_path = '../data/train.json'
        test_path = '../data/test.json'
        model_path = '../models/t5_nl2sql_wikisql'
    else:  # spider
        train_path = '../data/spider_train.json'
        test_path = '../data/spider_test.json'
        model_path = '../models/t5_nl2sql_spider'
    
    # Check if dataset exists
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print(f"Dataset not found for {args.dataset}.")
        if args.dataset == 'wikisql':
            print("Please run: python scripts/download_wikisql.py")
        else:
            print("Please download and process the Spider dataset.")
        return
    
    # Prepare data
    print("Preparing training data...")
    train_dataset, test_dataset, tokenizer = prepare_training_data(train_path, test_path)
    
    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(test_dataset)}")
    
    # Set hyperparameters
    hyperparams = {
        'num_train_epochs': args.epochs,
        'per_device_train_batch_size': args.batch_size,
        'per_device_eval_batch_size': args.batch_size,
        'warmup_steps': 500,
        'weight_decay': 0.01,
        'learning_rate': args.learning_rate,
        'logging_steps': 10,
        'save_total_limit': 3,
    }
    
    # Perform hyperparameter search if requested
    if args.hyperparam_search:
        best_params = hyperparameter_search(train_dataset, test_dataset)
        if best_params:
            hyperparams = best_params
            print("Using best hyperparameters for final training")
    
    # Train model
    print("Starting training process...")
    trainer = train_model(train_dataset, test_dataset, model_path, hyperparams)
    
    # Save tokenizer
    tokenizer.save_pretrained(model_path)
    
    print("Training completed successfully!")
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    main()