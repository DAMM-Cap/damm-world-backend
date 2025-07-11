FROM python:3.10-slim

# --- 1. Set working directory
WORKDIR /app

# --- 2. Install system dependencies (Node.js + Yarn + ts-node + TypeScript)
RUN apt-get update && apt-get install -y curl gnupg \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && npm install -g yarn ts-node typescript \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- 3. Install Python dependencies
COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install watchfiles

# --- 4. Copy shared code from monorepo root
COPY damm-world-api/app/constants /app/constants
COPY lagoon-indexer/db /app/db
COPY lagoon-indexer/core /app/core
COPY lagoon-indexer/utils /app/utils

# --- 5. Copy bot code
COPY bot /app

# --- 6. Install Node dependencies for bot
RUN yarn install

# --- 7. Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# --- 8. Run the keeper bot with auto-restart on code changes
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "python", "keeper.py"]
