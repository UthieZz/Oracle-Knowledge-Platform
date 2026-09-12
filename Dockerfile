FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask web API removed. This image is for the OKC compiler / export path only.
# Studio reads Firestore directly; run compile locally or in CI:
#   python run.py
CMD ["python", "-c", "print('OKP compiler image. Flask removed. Use: python run.py')"]
