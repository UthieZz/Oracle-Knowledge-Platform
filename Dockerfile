FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Near-term product path is the local-folder Connect pilot.
# Mount a config, watched folder, and persistent volumes for db/package/snapshot.
# Example:
#   docker run --rm -v $(pwd)/pilot.json:/app/pilot.json \
#     -v /path/to/watched:/data/watched \
#     -v /var/okp:/var/okp \
#     okp python scripts/run_connect_worker.py --config /app/pilot.json
#
# Legacy compiler entry remains available: python run.py
CMD ["python", "scripts/run_connect_worker.py", "--help"]
