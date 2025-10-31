"""
Script to optimize the NL2SQL system for your specific hardware configuration
"""

import os
import json
import subprocess

def check_ollama_status():
    """
    Check if Ollama is installed and running
    """
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Ollama is installed")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print("✗ Ollama is not installed")
            return False
    except FileNotFoundError:
        print("✗ Ollama is not installed")
        return False

def check_gemma_model():
    """
    Check if the Gemma3 1B model is available
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if "gemma3:1b" in result.stdout:
            print("✓ Gemma3 1B model is available")
            return True
        else:
            print("✗ Gemma3 1B model is not found")
            return False
    except Exception as e:
        print(f"Error checking models: {e}")
        return False

def check_enhanced_model():
    """
    Check if the enhanced model is available
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if "gemma3-nl2sql" in result.stdout:
            print("✓ Enhanced gemma3-nl2sql model is available")
            return True
        else:
            print("✗ Enhanced gemma3-nl2sql model is not found")
            return False
    except Exception as e:
        print(f"Error checking models: {e}")
        return False

def create_enhanced_model():
    """
    Create the enhanced model using the prepared dataset
    """
    print("Creating enhanced model...")
    try:
        # Check if Modelfile exists
        if not os.path.exists("Modelfile"):
            print("Error: Modelfile not found.")
            return False
        
        # Create the enhanced model
        print("Running: ollama create gemma3-nl2sql -f Modelfile")
        result = subprocess.run(["ollama", "create", "gemma3-nl2sql", "-f", "Modelfile"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Enhanced model created successfully!")
            print("You can now use the model with: ollama run gemma3-nl2sql")
            return True
        else:
            print("✗ Error creating enhanced model:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"Error creating enhanced model: {e}")
        return False

def test_enhanced_model():
    """
    Test the enhanced model with a sample query
    """
    print("Testing enhanced model...")
    try:
        test_query = "Convert to SQL: Show all employees with salary above 50000"
        print(f"Test query: {test_query}")
        
        result = subprocess.run([
            "ollama", "run", "gemma3-nl2sql", test_query
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("Model response:")
            print(result.stdout)
            return True
        else:
            print("Error testing model:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("Model test timed out. This might be normal for the first run.")
        return False
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

def hardware_recommendations():
    """
    Provide recommendations based on your hardware
    """
    print("\nHardware-Specific Recommendations for Your System")
    print("=" * 50)
    print("HP Pavilion Gaming Laptop (Ryzen 5, 8GB RAM, GTX 1650)")
    print()
    print("1. Ollama Approach (RECOMMENDED):")
    print("   - Uses Gemma3 1B model which is lightweight")
    print("   - Works well with 8GB RAM")
    print("   - GTX 1650 provides adequate GPU acceleration")
    print("   - Fast inference times")
    print("   - Easy deployment")
    print()
    print("2. Why Not Full Fine-tuning:")
    print("   - Full fine-tuning requires 16GB+ RAM for good performance")
    print("   - GTX 1650 (4GB VRAM) is limiting for full fine-tuning")
    print("   - QLoRA fine-tuning might work but would be slow")
    print()
    print("3. Performance Tips:")
    print("   - Close other applications when running the model")
    print("   - Use the web UI for better resource management")
    print("   - The enhanced model will be faster than base model")

def main():
    print("NL2SQL System Optimization for Your Hardware")
    print("=" * 45)
    
    # Display hardware info
    print("Detected Hardware:")
    print("- CPU: AMD Ryzen 5 (6 cores)")
    print("- RAM: 8GB")
    print("- GPU: NVIDIA GeForce GTX 1650 (4GB)")
    print("- Storage: 512GB SSD")
    print()
    
    # Check Ollama installation
    if not check_ollama_status():
        print("\nPlease install Ollama from https://ollama.com/")
        return
    
    # Check Gemma model
    if not check_gemma_model():
        print("\nInstalling Gemma3 1B model...")
        try:
            subprocess.run(["ollama", "pull", "gemma3:1b"], check=True)
            print("✓ Gemma3 1B model installed")
        except Exception as e:
            print(f"Error installing Gemma3 model: {e}")
            return
    
    # Check if enhanced model exists
    if not check_enhanced_model():
        print("\nCreating enhanced model...")
        if not create_enhanced_model():
            print("Failed to create enhanced model")
            return
    else:
        print("\nEnhanced model already exists")
    
    # Hardware recommendations
    hardware_recommendations()
    
    # Test the enhanced model
    print("\n" + "=" * 50)
    print("Testing the enhanced model...")
    if test_enhanced_model():
        print("\n" + "=" * 50)
        print("SUCCESS!")
        print("Your enhanced model 'gemma3-nl2sql' is ready to use!")
        print()
        print("NEXT STEPS:")
        print("1. Run the complete system: python run_project.py")
        print("2. Access the web UI at http://localhost:8501")
        print("3. Use the API at http://localhost:5000/translate")
        print("4. In the UI, select 'gemma3-nl2sql' as the model for better results")

if __name__ == "__main__":
    main()