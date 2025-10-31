"""
Fine-tuning script for Gemma3 1B model on NL2SQL task
"""

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    Trainer, 
    TrainingArguments,
    DataCollatorForLanguageModeling
)
from datasets import Dataset
import json
import os
import argparse
from datetime import datetime

class GemmaSQLDataset(torch.utils.data.Dataset):
    def __init__(self, data_path, tokenizer, max_length=512):
        """
        Custom dataset for NL2SQL task with Gemma model
        
        Args:
            data_path (str): Path to the JSON dataset
            tokenizer: Gemma tokenizer
            max_length (int): Maximum sequence length
        """
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Load data
        with open(data_path, 'r') as f:
            self.data = json.load(f)
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Format input for instruction tuning
        # We use a prompt format that Gemma can understand
        input_text = f"""<start_of_turn>user
Convert the following natural language query to SQL:
{item['question']}<end_of_turn>
<start_of_turn>model
{item['sql']}<end_of_turn>"""
        
        # Tokenize the input
        encodings = self.tokenizer(
            input_text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        # For causal language modeling, labels are the same as input_ids
        labels = encodings['input_ids'].clone()
        
        return {
            'input_ids': encodings['input_ids'].flatten(),
            'attention_mask': encodings['attention_mask'].flatten(),
            'labels': labels.flatten()
        }

def load_model_and_tokenizer(model_path):
    """
    Load Gemma model and tokenizer
    
    Args:
        model_path (str): Path to the Gemma model
    
    Returns:
        tuple: Model and tokenizer
    """
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Resize token embeddings
    model.resize_token_embeddings(len(tokenizer))
    
    return model, tokenizer

def prepare_training_data(train_path, test_path, tokenizer):
    """
    Prepare training and validation datasets
    
    Args:
        train_path (str): Path to training data
        test_path (str): Path to test data
        tokenizer: Gemma tokenizer
    
    Returns:
        tuple: Training and validation datasets
    """
    # Create datasets
    train_dataset = GemmaSQLDataset(train_path, tokenizer)
    test_dataset = GemmaSQLDataset(test_path, tokenizer)
    
    return train_dataset, test_dataset

def train_model(train_dataset, test_dataset, tokenizer, output_dir="./models/gemma-nl2sql"):
    """
    Fine-tune the Gemma model
    
    Args:
        train_dataset: Training dataset
        test_dataset: Validation dataset
        tokenizer: Gemma tokenizer
        output_dir (str): Directory to save the model
    """
    # Define training arguments optimized for your hardware
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,  # Small batch size for limited GPU memory
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,  # To simulate larger batch size
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        save_steps=500,
        save_total_limit=2,
        evaluation_strategy="steps",
        eval_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=torch.cuda.is_available(),  # Use mixed precision if CUDA available
        dataloader_pin_memory=False,  # Reduce memory usage
        remove_unused_columns=False,
        report_to=None,  # Disable wandb to save resources
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Not masked language modeling
    )
    
    # Load model
    model, _ = load_model_and_tokenizer("google/gemma-2b")  # Using the standard version for compatibility
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )
    
    # Start training
    trainer.train()
    
    # Save model
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    
    print(f"Model training completed and saved to {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Gemma3 1B for NL2SQL")
    parser.add_argument("--train_data", type=str, default="data/train.json", 
                        help="Path to training data")
    parser.add_argument("--test_data", type=str, default="data/test.json", 
                        help="Path to test data")
    parser.add_argument("--model_path", type=str, default="google/gemma-2b", 
                        help="Path to Gemma model")
    parser.add_argument("--output_dir", type=str, default="./models/gemma-nl2sql", 
                        help="Directory to save the fine-tuned model")
    
    args = parser.parse_args()
    
    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Prepare datasets
    print("Preparing datasets...")
    train_dataset, test_dataset = prepare_training_data(
        args.train_data, 
        args.test_data, 
        tokenizer
    )
    
    # Train model
    print("Starting training...")
    train_model(train_dataset, test_dataset, tokenizer, args.output_dir)

if __name__ == "__main__":
    main()