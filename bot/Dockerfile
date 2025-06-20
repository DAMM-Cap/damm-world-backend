FROM python:3.10-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install watchfiles for hot reload
RUN pip install watchfiles

# Copy the rest of the app
COPY . .

# Force immediate stdout flush
ENV PYTHONUNBUFFERED=1

# Use watchmedo to auto-restart keeper.py when .py files change
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "python", "keeper.py"]
