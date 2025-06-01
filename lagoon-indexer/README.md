# lagoon-indexer

This is the **indexer service** for the Damm World project. It listens to blockchain events and writes the data to PostgreSQL.

---

## 🚀 Running Locally

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the indexer script
python indexer.py
```

---

## ⚙️ Environment Variables

Set the database connection URL:

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/lagoon
```

---

## 🐳 Running with Docker

This service is also included in the root `docker-compose.yml` and can be launched with:

```bash
docker-compose up --build
```

---

## 🔁 Live Reload (Development)

The indexer uses `watchmedo` to automatically restart when Python files change.

---

## 📄 License

MIT
