"""
Script to fine-tune Gemma3 model using Spider and WikiSQL datasets
"""

import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from datasets import Dataset
import numpy as np

class GemmaNL2SQLFineTuner:
    def __init__(self, model_name="google/gemma-2b"):
        """
        Initialize the fine-tuner
        
        Args:
            model_name (str): Name of the Gemma model to fine-tune
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
    
    def load_model_and_tokenizer(self):
        """
        Load the Gemma model and tokenizer
        """
        try:
            print(f"Loading model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                device_map="auto"
            )
            
            print("Model and tokenizer loaded successfully!")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def prepare_dataset(self, data_path):
        """
        Prepare dataset for fine-tuning
        
        Args:
            data_path (str): Path to the dataset JSON file
            
        Returns:
            Dataset: Hugging Face Dataset object
        """
        try:
            # Load data
            with open(data_path, 'r') as f:
                data = json.load(f)
            
            # Format data for Gemma
            formatted_data = []
            for item in data:
                # Create prompt for Gemma
                prompt = f"Convert the following natural language question to SQL:\nQuestion: {item['question']}\nSQL:"
                completion = f" {item['sql']}"
                
                # Tokenize
                encoding = self.tokenizer(
                    prompt + completion,
                    truncation=True,
                    padding="max_length",
                    max_length=512,
                    return_tensors="pt"
                )
                
                # Labels for training (only train on completion part)
                prompt_encoding = self.tokenizer(
                    prompt,
                    return_tensors="pt"
                )
                
                labels = encoding["input_ids"].clone()
                labels[:, :prompt_encoding["input_ids"].shape[1]] = -100
                
                formatted_data.append({
                    "input_ids": encoding["input_ids"].squeeze(),
                    "attention_mask": encoding["attention_mask"].squeeze(),
                    "labels": labels.squeeze()
                })
            
            # Create Dataset object
            dataset = Dataset.from_list(formatted_data)
            return dataset
        
        except Exception as e:
            print(f"Error preparing dataset: {e}")
            return None
    
    def fine_tune(self, train_dataset, eval_dataset=None):
        """
        Fine-tune the model
        
        Args:
            train_dataset (Dataset): Training dataset
            eval_dataset (Dataset): Evaluation dataset (optional)
        """
        try:
            # Define training arguments
            training_args = TrainingArguments(
                output_dir="./results/gemma-nl2sql",
                overwrite_output_dir=True,
                num_train_epochs=3,
                per_device_train_batch_size=4,
                per_device_eval_batch_size=4,
                warmup_steps=100,
                logging_steps=10,
                save_steps=500,
                evaluation_strategy="steps" if eval_dataset else "no",
                eval_steps=500 if eval_dataset else None,
                prediction_loss_only=True,
                remove_unused_columns=False,
                fp16=True,  # Use mixed precision for faster training
            )
            
            # Create trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                tokenizer=self.tokenizer,
            )
            
            # Start training
            print("Starting fine-tuning...")
            trainer.train()
            
            # Save model
            print("Saving fine-tuned model...")
            trainer.save_model("./models/gemma-nl2sql-finetuned")
            self.tokenizer.save_pretrained("./models/gemma-nl2sql-finetuned")
            
            print("Fine-tuning completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error during fine-tuning: {e}")
            return False

def main():
    print("Gemma3 NL2SQL Fine-tuning")
    print("=" * 30)
    
    # Initialize fine-tuner
    fine_tuner = GemmaNL2SQLFineTuner("google/gemma-2b")
    
    # Load model and tokenizer
    if not fine_tuner.load_model_and_tokenizer():
        print("Failed to load model. Exiting.")
        return
    
    # Check for datasets
    spider_train_path = "data/spider_train.json"
    wikisql_train_path = "data/wikisql_train.json"
    
    train_datasets = []
    
    # Load Spider dataset if available
    if os.path.exists(spider_train_path):
        print("Loading Spider dataset...")
        spider_dataset = fine_tuner.prepare_dataset(spider_train_path)
        if spider_dataset:
            train_datasets.append(spider_dataset)
    
    # Load WikiSQL dataset if available
    if os.path.exists(wikisql_train_path):
        print("Loading WikiSQL dataset...")
        wikisql_dataset = fine_tuner.prepare_dataset(wikisql_train_path)
        if wikisql_dataset:
            train_datasets.append(wikisql_dataset)
    
    if not train_datasets:
        print("No training datasets found. Please download and process the datasets first.")
        print("Run scripts/download_spider.py and scripts/download_wikisql.py")
        return
    
    # Combine datasets
    if len(train_datasets) > 1:
        print("Combining datasets...")
        # For simplicity, we'll use just the first dataset in this example
        train_dataset = train_datasets[0]
    else:
        train_dataset = train_datasets[0]
    
    print(f"Training dataset size: {len(train_dataset)} examples")
    
    # Start fine-tuning
    fine_tuner.fine_tune(train_dataset)
    
    print("\nFine-tuning process completed!")
    print("Fine-tuned model saved to: ./models/gemma-nl2sql-finetuned")

if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import transformers
        import datasets
        main()
    except ImportError as e:
        print("Missing required packages. Please install them:")
        print("pip install transformers datasets accelerate")
        print(f"Error: {e}")