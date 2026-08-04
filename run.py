import sys
import subprocess
import argparse

def run_compiler():
    # Placeholder for compiler logic, preserving architecture
    print("Running Compiler...")
    subprocess.run(["python3", "main.py"])

def run_studio():
    print("Starting Oracle Studio Backend...")
    # Launching as a module to preserve relative imports and package structure
    subprocess.run(["python3", "-m", "src.studio.api_server"])

def main():
    parser = argparse.ArgumentParser(description="Oracle Knowledge Platform")
    parser.add_argument("mode", choices=["compiler", "studio"], help="Mode to run.")
    args = parser.parse_args()
    
    if args.mode == "compiler":
        run_compiler()
    elif args.mode == "studio":
        run_studio()

if __name__ == "__main__":
    main()
