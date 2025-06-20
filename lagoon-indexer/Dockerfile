FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Force immediate stdout flush
ENV PYTHONUNBUFFERED=1

# Use watchmedo to auto-restart indexer.py when .py files change
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "python", "indexer.py"]
