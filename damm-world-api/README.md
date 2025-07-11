# damm-world-api

This is the **FastAPI backend** for the Damm World project. It exposes a REST API to serve indexed data stored in PostgreSQL.

---

## 🚀 Running Locally

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI app
uvicorn app.main:app --reload
```

API available at [http://localhost:8000/docs](http://localhost:8000/docs).

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

This API uses Uvicorn’s `--reload` feature to automatically reload when Python files change.

---

## 📄 License

MIT
