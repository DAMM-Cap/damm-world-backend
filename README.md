# damm-world-backend

This repository contains the complete backend stack for the **Damm World** project, structured as a modular system:

- **damm-world-api**: FastAPI app serving indexed data to the frontend.
- **lagoon-indexer**: Worker service that reads blockchain events and writes to PostgreSQL.
- **PostgreSQL**: Shared database used by both services.
- **docker-compose.yml**: Orchestrates all services for local development and deployment.

---

## 🏗️ Project Structure

```
damm-world-backend/
├── damm-world-api/     # FastAPI backend
├── lagoon-indexer/     # Blockchain indexer
├── docker-compose.yml  # Orchestrator for all services
└── .env                # Environment variables (optional)
```

---

## 🐳 Running with Docker Compose

Start all services:

```bash
docker-compose up --build
```

Stop all services:

```bash
docker-compose down
```

---

## 🔧 Service Details

### 1️⃣ PostgreSQL

- **Port**: `5432` (exposed for local development)
- **Credentials**:
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=postgres`
  - `POSTGRES_DB=lagoon`

### 2️⃣ damm-world-api (FastAPI)

- **Build context**: `damm-world-api/`
- **Port**: `8000`
  - Accessible at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).
- **Reads data**: from the shared PostgreSQL database.

### 3️⃣ lagoon-indexer

- **Build context**: `lagoon-indexer/`
- **No exposed port** (runs as a background service).
- **Writes data**: to the shared PostgreSQL database.

---

## 📝 Environment Variables

Both `damm-world-api` and `lagoon-indexer` read the database connection URL from the environment:

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/lagoon
```

✅ **Note**: Use `postgresql://` (not `postgres://`) for SQLAlchemy compatibility.

---

## 📜 License

This project is licensed under the **Elastic License 2.0**. You may use, modify, and share this code for **non-commercial purposes**. Commercial use requires a commercial license from the author.

See the [LICENSE](./LICENSE) file for more details.
