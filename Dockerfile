FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run seeder on startup to verify fixtures and print test tokens, then start portal
CMD ["sh", "-c", "python seed.py && uvicorn src.main:app --host 0.0.0.0 --port 8080"]
