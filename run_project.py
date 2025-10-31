"""
Script to run both frontend and backend of the NL2SQL project simultaneously
"""

import subprocess
import sys
import time
import threading

def run_flask():
    """Run the Flask backend"""
    print("Starting Flask backend...")
    flask_process = subprocess.Popen([sys.executable, "app/app.py"])
    return flask_process

def run_streamlit():
    """Run the Streamlit frontend"""
    print("Starting Streamlit frontend...")
    streamlit_process = subprocess.Popen(["streamlit", "run", "app/ui.py"])
    return streamlit_process

def main():
    print("Starting NL2SQL Project - Both Frontend and Backend")
    print("=" * 50)
    
    # Start Flask backend
    flask_process = run_flask()
    
    # Wait a moment for Flask to start
    time.sleep(2)
    
    # Start Streamlit frontend
    streamlit_process = run_streamlit()
    
    print("\nBoth services are now running:")
    print("- Flask backend: http://localhost:5000")
    print("- Streamlit frontend: http://localhost:8501")
    print("\nPress Ctrl+C to stop both services")
    
    try:
        # Wait for both processes
        while True:
            if flask_process.poll() is not None or streamlit_process.poll() is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down services...")
        flask_process.terminate()
        streamlit_process.terminate()
        flask_process.wait()
        streamlit_process.wait()
        print("Services stopped.")

if __name__ == "__main__":
    main()