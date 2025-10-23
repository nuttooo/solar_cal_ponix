#!/usr/bin/env python3
"""
Run script for Solar Analyzer Web Application
"""

import os
import sys

def main():
    """Main entry point for the application"""
    
    # Check if required directories exist
    required_dirs = ['uploads', 'static/outputs', 'templates']
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
    
    # Check if data directory exists
    if not os.path.exists('data'):
        print("Creating directory: data")
        os.makedirs('data', exist_ok=True)
    
    # Import and run the Flask app
    try:
        from app import app
        print("🚀 Starting Solar Analyzer Pro Web Application...")
        print("📊 Open your browser and go to: http://localhost:8080")
        print("🔧 Press Ctrl+C to stop the server")
        app.run(debug=True, host='0.0.0.0', port=8080)
    except ImportError as e:
        print(f"❌ Error importing app: {e}")
        print("Please make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()