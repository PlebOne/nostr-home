#!/usr/bin/env python3

import subprocess
import sys
import os

def install_requirements():
    """Install Python requirements"""
    print("📦 Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def run_test():
    """Run the Nostr test"""
    print("\n🔍 Testing Nostr connection...")
    try:
        subprocess.check_call([sys.executable, "test_python_nostr.py"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Test failed: {e}")
        return False

def run_server():
    """Run the Flask server"""
    print("\n🚀 Starting Python Flask server...")
    try:
        subprocess.check_call([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed: {e}")

def main():
    print("🐍 Nostr Home Python Setup")
    print("="*40)
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("❌ Please run this script from the project root directory")
        return
    
    # Install requirements
    if not install_requirements():
        return
    
    # Ask user what to do
    print("\n🤔 What would you like to do?")
    print("1. Test Nostr connection")
    print("2. Start the server")
    print("3. Both (test then start server)")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        run_test()
    elif choice == "2":
        run_server()
    elif choice == "3":
        if run_test():
            print("\n✅ Test passed! Starting server...")
            run_server()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
