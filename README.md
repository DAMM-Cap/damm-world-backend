# damm-world-backend

This repository contains the complete backend stack for the Damm World project, structured as a modular system with:

- **damm-world-api**: A FastAPI app serving indexed data to the frontend.
- **lagoon-indexer**: A worker service that reads blockchain events and writes to PostgreSQL.
- **PostgreSQL**: The database shared by both services.
- **docker-compose.yml**: Orchestrates the services for local development or production deployment.

---

## 🏗️ Project Structure

```
damm-world-backend/
├── damm-world-api/     # FastAPI backend
├── lagoon-indexer/     # Blockchain indexer
├── docker-compose.yml  # Service orchestrator
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

- **Port**: 5432 (exposed for local development)
- **Credentials**:
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=postgres`
  - `POSTGRES_DB=lagoon`

### 2️⃣ damm-world-api (FastAPI)

- **Builds from**: `damm-world-api/` folder
- **Port**: 8000 (accessible at [http://localhost:8000/docs](http://localhost:8000/docs))
- **Reads data**: from the shared PostgreSQL database.

### 3️⃣ lagoon-indexer

- **Builds from**: `lagoon-indexer/` folder
- **No exposed port** (runs as a background service)
- **Writes data**: to the shared PostgreSQL database.

---

## 📝 Environment Variables

Both `damm-world-api` and `lagoon-indexer` read the database connection from the environment:

```
DATABASE_URL=postgres://postgres:postgres@db:5432/lagoon
```

---

## 📄 License

MIT
