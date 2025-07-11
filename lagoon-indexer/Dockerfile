FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY lagoon-indexer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared folders from monorepo root
COPY damm-world-api/app/constants /app/constants
COPY lagoon-indexer/db /app/db
COPY lagoon-indexer/core /app/core
COPY lagoon-indexer/utils /app/utils

# Copy lagoon-indexer source
COPY lagoon-indexer /app

# Force immediate stdout flush + import path consistency
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Dev-friendly auto-reload
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "python", "indexer.py"]
