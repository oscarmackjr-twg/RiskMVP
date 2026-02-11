# Technology Stack

**Analysis Date:** 2026-02-11

## Languages

**Primary:**
- Python 3.11+ - Backend services and distributed computing engine
- TypeScript 5.6.2 - Frontend React application with strict type checking
- SQL (PostgreSQL) - Data layer schema and migrations

**Secondary:**
- JavaScript - CSS tooling (PostCSS, Tailwind)

## Runtime

**Environment:**
- Python 3.11+ for backend (`requires-python = ">=3.11"` in `pyproject.toml`)
- Node.js (version managed by npm lockfile v3) for frontend

**Package Manager:**
- pip with venv for Python dependencies
- npm 10+ for JavaScript dependencies (lockfile: `package-lock.json` v3)

## Frameworks

**Core Backend:**
- FastAPI 0.100+ - REST API framework for three microservices
  - `services/marketdata_svc/app/main.py` - Market data snapshot service (port 8001)
  - `services/run_orchestrator/app/main.py` - Run orchestration and task distribution (port 8002)
  - `services/results_api/app/main.py` - Results query and aggregation API (port 8003)

**Frontend:**
- React 18.3.1 - UI component framework
- React Router 6.26.2 - Client-side routing

**Build/Dev:**
- Vite 5.4.6 - Frontend dev server and production build tool
- TypeScript 5.6.2 compiler (strict mode enabled)
- Tailwind CSS 3.4.19 - Utility-first CSS framework
- PostCSS 8.5.6 - CSS transformation tool
- Autoprefixer 10.4.24 - CSS vendor prefix handling

**Data Fetching:**
- TanStack React Query 5.59.16 - Server state management with caching
- Axios 1.7.7 - HTTP client for API calls

**Testing:**
- pytest 7.4.0 - Python test framework (`testpaths = ["compute/tests"]` in `pyproject.toml`)

## Key Dependencies

**Critical Backend:**
- psycopg 3.1.18+ with binary wheels - PostgreSQL 3.0 adapter for Python
  - Uses: Dict row factory, JSONB type helpers
  - Import: `psycopg` and `psycopg.types.json.Json`
- pydantic - Data validation and serialization for API models
  - Used in: Request/response models across all FastAPI services
  - Example: `PositionSnapshotIn`, `MarketDataSnapshotV1`, `RunRequestedV1`

**Frontend:**
- @types/react 18.3.5 - TypeScript definitions for React
- @types/react-dom 18.3.0 - TypeScript definitions for React DOM
- @vitejs/plugin-react 4.3.1 - Vite plugin for React with Fast Refresh

**Styling:**
- tailwindcss 3.4.19 with extended brutal design theme (custom colors: yellow, pink, blue, green, orange, red, purple, lime)
- postcss 8.5.6 with autoprefixer integration

## Configuration

**Environment Variables:**

Backend (used in `services/common/db.py` and services):
- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/iprs`)
- `POSITIONS_SNAPSHOT_PATH` - Path to demo positions JSON file (default: `demo/inputs/positions.json`)
- `WORKER_ID` - Worker instance identifier (default: `worker-1`)
- `WORKER_LEASE_SECONDS` - Task lease duration in seconds (default: `60`)
- `WORKER_IDLE_SLEEP_SECONDS` - Worker idle sleep duration (default: `0.5`)
- `RUN_TASK_HASH_MOD` - Number of hash buckets for task sharding (default: `1`)
- `RUN_TASK_MAX_ATTEMPTS` - Maximum task retry attempts (default: `3`)

Frontend:
- Uses Vite proxy to services (no env vars required for local dev)
- Proxy configuration in `frontend/vite.config.ts`:
  - `/mkt` → http://127.0.0.1:8001
  - `/orch` → http://127.0.0.1:8002
  - `/results` → http://127.0.0.1:8003

**Build Configuration:**

Backend:
- `pyproject.toml` - Project metadata and build system (setuptools)
  - Defines compute* packages only (excludes contracts, services, sql, ui)
  - pytest configuration with testpaths

Frontend:
- `vite.config.ts` - Dev server proxy and React plugin setup
- `tsconfig.json` - TypeScript compilation (ES2022 target, strict mode)
- `tsconfig.node.json` - Node-specific TypeScript config for build tools
- `tailwind.config.js` - CSS theme extensions and plugin configuration
- `postcss.config.js` - PostCSS pipeline setup

## Platform Requirements

**Development:**
- Python 3.11+ with venv
- PostgreSQL 12+ with psycopg 3 support (JSONB columns)
- Node.js 18+ (via npm)
- PowerShell (for demo runner scripts on Windows)

**Production:**
- PostgreSQL database with schema initialized from `sql/001_mvp_core.sql`
- Python 3.11+ runtime with installed dependencies
- Node.js for static asset generation (can be pre-built)
- HTTP server for frontend SPA (static assets)

## Service Port Allocation

- Port 8001: Market Data Service
- Port 8002: Run Orchestrator Service
- Port 8003: Results API Service
- Port 5173: Frontend Vite dev server (default)

---

*Stack analysis: 2026-02-11*
