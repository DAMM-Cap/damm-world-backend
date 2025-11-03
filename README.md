# damm-world-backend

This repository contains the complete backend stack for the **Damm World** project, structured as a modular system:

- **damm-world-api**: FastAPI app serving indexed data to the frontend
- **lagoon-indexer**: Worker service that reads blockchain events and writes to PostgreSQL
- **keeper-bot**: Background service that writes to blockchain and updates status via FastAPI
- **PostgreSQL**: Shared database used by all services
- **docker-compose.yml**: Orchestrates all services for local development and deployment

---

## 🏗️ Project Structure

```
damm-world-backend/
├── damm-world-api/     # FastAPI backend
├── lagoon-indexer/     # Blockchain indexer
├── bot/                # Keeper bot service
├── docker-compose.yml  # Orchestrator for all services
└── .env                # Environment variables (optional)
```

---

## 🐳 Running with Docker Compose

### Start all services

```bash
docker-compose up --build
```

### Stop all services

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
  - Accessible at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Reads data**: from the shared PostgreSQL database

### 3️⃣ lagoon-indexer

- **Build context**: `lagoon-indexer/`
- **No exposed port** (runs as a background service)
- **Writes data**: to the shared PostgreSQL database

### 4️⃣ keeper-bot

- **Build context**: `bot/`
- **No exposed port** (runs as a background service)
- **Functionality**:
  - Writes data to blockchain
  - Updates its status to the shared PostgreSQL database through FastAPI endpoint
  - Stays in-sync with the indexer to wait for it to read and update the database once the bot has triggered transactions to the blockchain

---

## 🔧 Render Build & Deploy

Generate a project for deploying each of the three necessary services idependently. A fourth service can be deployed for enabling the keeper-bot instances.

The main repository from where Render pulls services is https://github.com/DAMM-Cap/damm-world-backend

### Lagoon-db

After deploying the service, look into `connections` info to set up env vars

### DAMM API

Dockerfile Path: `./damm-world-api/Dockerfile`

### Lagoon-indexer

Dockerfile Path: `./lagoon-indexer/Dockerfile`
Docker Command: `python indexer.py --sleep_time 10 --range 3000 --real_time 1 --run_time 60`

---

## 📝 Environment Variables

Both `damm-world-api` and `lagoon-indexer` read the database connection URL from the environment:

```bash
DATABASE_URL=postgresql://postgres:postgres@db:5432/lagoon
```

> **Note**: Use `postgresql://` (not `postgres://`) for SQLAlchemy compatibility.

> **Note**: env.example. has a detailed description of the necessary env vars. For allowing the keeper-bot to run as well, add also the env vars included in the bot service's root.

---

## ⛓️ Supported Chains

To add support for a new chain:

1. **Add RPC configuration** in `lagoon-indexer/utils/rpc.py`:

   Update the `FALLBACK_ENV_VARS` dictionary:

   ```python
   FALLBACK_ENV_VARS = {
       480: "WORLDCHAIN_JSON_RPC",
       # Add your chain here
       # chain_id: "CHAIN_JSON_RPC_ENV_VAR"
   }
   ```

2. **Add chain ID** to the `SUPPORTED_CHAINS` environment variable (comma-separated):

   ```bash
   SUPPORTED_CHAINS=11155111,8453,480
   ```

---

## 🏦 Adding New Vaults

The indexer and bot are synced according to the registration in the `factory` table. To add a new vault for indexing (and automatic settlement through the keeper-bot), insert a new row in the `factory` table.

### Example: Registering a vault on Optimism mainnet

```sql
INSERT INTO factory (
    chain_id,
    genesis_block_number,
    vault_address,
    silo_address,
    continue_indexing,
    keeper_bot_enabled,
    created_at
) VALUES (
    10,
    143028805,
    '0xd93a8dfe6514179D23314B91aFbaa7a7443372bC',
    '0x3b6AEeEF64DdA9879f0b9DE798F4A0C219D4d661',
    TRUE,
    FALSE,
    NOW()
) ON CONFLICT (chain_id, vault_address) DO NOTHING;
```

### Field descriptions

- **`continue_indexing`**: Set to `TRUE` to allow an indexer instance to listen to the vault
- **`keeper_bot_enabled`**: Set to `FALSE` for manual settlement, or `TRUE` for automatic settlement
- **Required fields**:
  - `chain_id`: Chain identifier
  - `genesis_block_number`: Block number of the transaction that deployed the vault
  - `vault_address`: Lagoon vault contract address
  - `silo_address`: Lagoon silo contract address

---

## 🔧 Utility Scripts

### `restart.sh`

Reruns all services locally without rebuilding.

### `reset_and_restart.sh`

**⚠️ Warning: This script is destructive.**

- Cleans all Docker services
- Drops all tables from the PostgreSQL service
- Re-runs the whole project

This service can also be deployed on Render and kept suspended, allowing you to reset the database at any time by activating the service.

---

## 📄 License

This project is licensed under the **Elastic License 2.0**. You may use, modify, and share this code for **non-commercial purposes**. Commercial use requires a commercial license from the author.

See the [LICENSE](./LICENSE) file for more details.
