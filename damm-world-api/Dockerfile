FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY damm-world-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY lagoon-indexer/db /app/db
COPY lagoon-indexer/core /app/core
COPY lagoon-indexer/utils /app/utils
COPY damm-world-api/app/constants /app/constants

# Copy the FastAPI app code
COPY damm-world-api /app

# Env setup
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
