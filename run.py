import sys
import os
import subprocess
import argparse

def run_compiler():
    print("Running Compiler...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    subprocess.run(["python3", "scripts/compile_data.py"], env=env)

def run_studio():
    studio_dir = os.path.join(os.getcwd(), "studio")
    if not os.path.isdir(studio_dir):
        raise SystemExit("studio/ directory not found")
    print("Starting Oracle Studio (Vite). Flask is not the Studio runtime.")
    subprocess.run(["npm", "run", "dev"], cwd=studio_dir)

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
