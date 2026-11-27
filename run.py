import sys
import os
import subprocess
import argparse

def run_compiler():
    print("WARNING: 'compiler' mode is the legacy src/ path (scripts/compile_data.py).")
    print("Preferred local pilot path is the okc/ surface:")
    print("  - python run.py server          # local OKC API for Studio")
    print("  - python scripts/verify_local_pilot.py  # single-command end-to-end verification")
    print("  - python scripts/run_connect_worker.py  # Connect worker")
    print("See docs/IMPLEMENTATION_OWNERSHIP.md and README.md.")
    print("Running legacy compiler...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    subprocess.run(["python3", "scripts/compile_data.py"], env=env)

def run_studio():
    studio_dir = os.path.join(os.getcwd(), "studio")
    if not os.path.isdir(studio_dir):
        raise SystemExit("studio/ directory not found")
    print("Starting Oracle Studio (Vite). Flask is not the Studio runtime.")
    print("Note: for ImportPage upload/compile, also start the local OKC server: python run.py server")
    subprocess.run(["npm", "run", "dev"], cwd=studio_dir)

def run_server():
    """Start the local OKC API server expected by studio/src/services/apiService.ts.
    
    Binds to OKC_API_HOST/OKC_API_PORT (default 127.0.0.1:5000).
    Honors OKP_STRICT_PERMISSIONS for the upload/compile path.
    """
    print("Starting local OKC API server (okc.server.app)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    subprocess.run([sys.executable, "-m", "okc.server.app"], env=env)

def main():
    parser = argparse.ArgumentParser(description="Oracle Knowledge Platform")
    parser.add_argument("mode", choices=["compiler", "studio", "server"], help="Mode to run.")
    args = parser.parse_args()
    if args.mode == "compiler":
        run_compiler()
    elif args.mode == "studio":
        run_studio()
    elif args.mode == "server":
        run_server()

if __name__ == "__main__":
    main()
