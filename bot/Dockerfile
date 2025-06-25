FROM python:3.10-slim

# Set working directory
WORKDIR /app

# --- 1. Install system dependencies (for node, yarn, ts-node, TypeScript)
RUN apt-get update && apt-get install -y curl gnupg \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && npm install -g yarn ts-node typescript \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install watchfiles

# --- 3. Copy app files
COPY . .

# --- 4. Install Node dependencies from project
RUN yarn install

# --- 5. Force immediate stdout flush
ENV PYTHONUNBUFFERED=1

# --- 6. Run the keeper with auto-restart
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "python", "keeper.py"]
