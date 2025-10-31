"""
Script to help set up Ollama and pull Gemma3 1B model
"""

import subprocess
import sys
import os
import platform

def check_ollama_installed():
    """
    Check if Ollama is installed
    """
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"Ollama is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Ollama is not installed")
        return False

def install_ollama_windows():
    """
    Instructions for installing Ollama on Windows
    """
    print("To install Ollama on Windows:")
    print("1. Download the Windows installer from: https://ollama.com/download/OllamaSetup.exe")
    print("2. Run the installer and follow the installation instructions")
    print("3. Restart your terminal/command prompt after installation")

def install_ollama_linux():
    """
    Install Ollama on Linux
    """
    try:
        subprocess.run(['curl', '-fsSL', 'https://ollama.com/install.sh'], check=True)
        print("Ollama installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install Ollama")
        return False

def install_ollama_mac():
    """
    Instructions for installing Ollama on macOS
    """
    print("To install Ollama on macOS:")
    print("1. Download the macOS installer from: https://ollama.com/download/Ollama-darwin.zip")
    print("2. Unzip and run the installer")
    print("Or use Homebrew:")
    print("brew install ollama")

def pull_gemma_model():
    """
    Pull the Gemma3 1B model
    """
    try:
        print("Pulling Gemma3 1B model...")
        subprocess.run(['ollama', 'pull', 'gemma3:1b'], check=True)
        print("Gemma3 1B model pulled successfully")
        return True
    except subprocess.CalledProcessError:
        print("Failed to pull Gemma3 1B model")
        return False

def check_model_available():
    """
    Check if Gemma3 1B model is available
    """
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True, check=True)
        if 'gemma3:1b' in result.stdout:
            print("Gemma3 1B model is available")
            return True
        else:
            print("Gemma3 1B model is not available")
            return False
    except subprocess.CalledProcessError:
        print("Failed to list Ollama models")
        return False

def main():
    print("Setting up Ollama for Gemma3 1B model")
    print("=" * 40)
    
    # Check if Ollama is installed
    if not check_ollama_installed():
        system = platform.system()
        if system == "Windows":
            install_ollama_windows()
        elif system == "Linux":
            install_ollama_linux()
        elif system == "Darwin":  # macOS
            install_ollama_mac()
        else:
            print(f"Unsupported system: {system}")
        
        print("\nPlease install Ollama and restart your terminal, then run this script again")
        return
    
    # Check if model is available
    if not check_model_available():
        print("\nGemma3 1B model not found. Pulling the model...")
        if pull_gemma_model():
            print("Model is now available")
        else:
            print("Failed to pull the model. Please try manually:")
            print("ollama pull gemma3:1b")
    else:
        print("\nGemma3 1B model is ready to use!")
        print("\nYou can now test the model with:")
        print("python scripts/ollama_gemma_inference.py")

if __name__ == "__main__":
    main()