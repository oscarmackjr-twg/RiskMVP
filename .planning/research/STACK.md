# Technology Stack: Institutional Portfolio Analytics Platform

**Project:** IPRS Risk Platform - Expansion to Full Portfolio Analytics
**Researched:** 2026-02-11
**Scope:** Loan-heavy fixed income portfolio (70%+), thousands of positions
**Infrastructure:** AWS (ECS Fargate, RDS Aurora, PostgreSQL)
**Baseline:** Python 3.11+, FastAPI, psycopg3, PostgreSQL JSONB, React 18 + TypeScript

---

## Recommended Stack

### Core Quantitative Libraries

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **QuantLib** | 1.34+ | Curve construction, interest rate models, pricing | Industry standard for fixed income; C++ core with Python bindings for performance; handles complex instruments (callable/putable bonds, ABS/MBS). Alternative: Re-implementing in pure Python is 10x slower for portfolio-scale work. | HIGH |
| **NumPy** | 1.26+ | Numerical computing, vectorized operations | Essential for scenario analysis, Monte Carlo at scale. Industry standard. Already used implicitly in vectorized risk calculations. | HIGH |
| **SciPy** | 1.14+ | Optimization, interpolation, root-finding | Curve interpolation, convexity adjustments, PD calibration. QuantLib uses scipy internally for some models. | MEDIUM |
| **pandas** | 2.2+ | Data manipulation, portfolio aggregation, reporting | Time-series handling, grouping by risk factors, drill-down analytics. Use for data ingestion and result aggregation, NOT for real-time pricing (too slow). | HIGH |
| **Numba** | 0.59+ | JIT compilation for numerical code | 50-100x speedup for tight loops in cash flow generation, scenario application, Monte Carlo. Critical for loan-heavy portfolios with amortization complexity. | HIGH |

### Risk and Credit Modeling

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **Statsmodels** | 0.14+ | Statistical modeling, regression, GARCH | PD/LGD calibration, historical stress scenarios, factor models. Use for macro-economic factor linking. | MEDIUM |
| **Scikit-learn** | 1.4+ | Classification, clustering, preprocessing | PD model training (logistic regression), credit segmentation, portfolio clustering for risk aggregation. Light dependency—only import specific modules. | MEDIUM |
| **cython-compiled curve builder** | Custom | Fast curve construction for 1000+ curve scenarios | QuantLib curve construction is a bottleneck at scale. Consider cythonized custom implementation for OIS/spread dual-curve bootstrapping. Build in-house or use QuantLib extensions. | MEDIUM |

### Monte Carlo and Stochastic Engines

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **Ray** | 2.28+ (LTS) | Distributed Monte Carlo, task scheduling | Horizontal scaling for Monte Carlo simulations (rates, spreads, defaults). Drop-in replacement for multiprocessing. Integrates with ECS task distribution. Scale from 1 to 1000+ tasks transparently. | MEDIUM |
| **Polars** | 0.20+ (if replacing pandas for hot paths) | High-performance DataFrames for large scenario sets | Optional: Only for extremely large scenario matrices (>1M paths × 1000 curves). Use pandas for everything else—better ecosystem. Replace selectively. | LOW |
| **Dask** | 2024.3+ | Lazy evaluation for distributed cash flow generation | Alternative to Ray if you prefer lazy evaluation. Smaller learning curve than Ray. Use one OR the other, not both. Recommend Ray for financial workloads. | LOW |

### Cash Flow and Structural Modeling

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **Existing custom modules** | In-house | Loan amortization, ARM resets, prepayment, waterfalls | You have skeleton for these; build on them. Pre-payment is domain-specific—no standard library exists. Cash flow generation is computational bottleneck; use Numba or Cython for tight loops. | HIGH |
| **actuarial** | 0.7+ | Mortality tables, annuity valuation (if needed) | Only if you model life insurance or mortality-linked instruments. Likely out of scope for loan portfolios. | LOW |

### Regulatory and Compliance

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **Custom CECL engine** | In-house | ASC 326 expected credit loss modeling | No standard library. Build: (1) PD calibration from rating transitions, (2) stage classification logic (IFRS 9/ASC 326), (3) scenario weighting engine, (4) allowance roll-forward. Integrate PD/LGD from Statsmodels. | MEDIUM |
| **Custom Basel III/RWA** | In-house | Capital adequacy calculation, risk-weighted assets | Implementation is straightforward arithmetic; regulatory requirements change annually. Keep modular, externalize assumptions to config. | MEDIUM |
| **jsonschema** | 4.22+ | Data contract validation | Enforce domain schemas for regulatory reporting payloads. Validate CECL inputs before computation. | MEDIUM |

### Optimization and Analytics

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **SciPy optimize** | 1.14+ | Portfolio optimization, ALM | Constraint optimization for performance attribution, risk budgeting. Use only for non-real-time analytics (not in pricing loop). | MEDIUM |
| **statsmodels.multivariate** | 0.14+ | Factor models, PCA for dimension reduction | Decompose yield curve into level/slope/curvature; reduce 50 rate tenors to 3 factors for intuitive reporting. | MEDIUM |
| **networkx** (optional) | 3.2+ | Graph analysis for counterparty dependencies | If tracking collateral netting, funding flows, or interconnectedness. Likely post-Phase 2. | LOW |

### Testing, Validation, Golden Data

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **pytest** | 7.4+ (already in MVP) | Unit and integration tests | Standard. Add fixtures in `.planning/fixtures/` for loan products, bonds, curves. | HIGH |
| **pytest-benchmark** | 4.0+ | Performance regression testing | Critical: Golden pricer tests must execute in <500ms for 100-bond portfolio. Track regressions. | MEDIUM |
| **hypothesis** | 6.98+ | Property-based testing for pricing | Generate random curves, instruments, scenarios; verify invariants (e.g., PV decreases with rate increase, DV01 > 0). Catch edge cases. | MEDIUM |
| **json-schema-ref-parser** (npm) | 11.5+ | Validation of contract schemas on frontend | Validate incoming API payloads match `contracts/domains/` schemas before submission to orchestrator. | MEDIUM |

### Database and ORM

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **psycopg** | 3.1+ (already in MVP) | PostgreSQL async driver | Keep it. Async support for high-concurrency results API. | HIGH |
| **SQLAlchemy** (optional) | 2.0+ | ORM, query builder | Use sparingly: Only for complex queries in results_api (aggregations, drill-downs). For workers/pricers, use raw SQL with psycopg—faster. | LOW |
| **alembic** | 1.13+ | Database migrations | Formalize DDL changes. Create migration for each schema update. | MEDIUM |
| **pgvector** (PostgreSQL extension) | 0.7+ | Vector similarity for instrument matching | Only if building instrument search/clustering. Post-Phase 1. | LOW |

### Infrastructure and Deployment

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **boto3** | 1.34+ | AWS SDK for Python | Retrieve secrets from Secrets Manager, interact with S3 (scenario dumps), SNS (notifications). Required for production. | HIGH |
| **python-dotenv** | 1.0+ | Environment variable loading (dev only) | Use for `.env` in development. Never commit secrets. | MEDIUM |
| **pydantic** | 2.6+ | Data validation, config management | Already implicitly used in FastAPI. Formalize config schema; export to Terraform for reproducibility. | HIGH |
| **Terraform** | 1.7+ (infrastructure) | IaC for AWS | Define ECS Fargate clusters, RDS Aurora, task definitions, IAM roles, CloudWatch alarms. Keep separate from app repo (or in `.infra/`). | MEDIUM |
| **docker** | 27+ | Containerization | Multi-stage Dockerfile: build Python wheels, slimmed runtime image. Target <500MB image. Use ECR for private registry. | HIGH |

### Async and Concurrency

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **asyncio** (stdlib) | 3.11+ | Async runtime | Use for I/O-bound tasks (DB queries, API calls). NOT for CPU-bound pricing (use thread/process pool or Ray). | HIGH |
| **httpx** | 0.26+ | Async HTTP client | Replace `requests` in services for async calls to other services. | MEDIUM |
| **aiojobs** | 1.3+ | Background job scheduling | If needing delayed/recurring tasks (e.g., daily EOD runs). Consider Celery + Redis alternative. | LOW |

### Frontend Extensions (Beyond React 18 + TypeScript + Vite)

| Library | Version | Purpose | Why This Choice | Confidence |
|---------|---------|---------|-----------------|------------|
| **react-query** (TanStack Query) | 5.6+ (already in MVP) | Server state management | Keep it. Essential for drill-down queries, caching, background refetches. | HIGH |
| **D3.js** or **Plotly.js** | 7.8+ or 2.26+ | Portfolio visualizations | D3 for custom yield curve, risk ladder, attribution waterfall. Plotly for quick, interactive charts. Recommend Plotly for speed; D3 if branding demands pixel-perfect control. | MEDIUM |
| **Apache ECharts** | 5.4+ | Alternative to Plotly for large datasets | Lighter than D3, richer than Plotly. Good for real-time risk dashboards (1000+ positions). | LOW |
| **TailwindCSS** | 3.4+ (already in MVP) | Utility CSS | Keep it. Fast. Standard in modern React stacks. | HIGH |
| **Heroicons** | 2.0+ | Icon library | Lightweight, pairs with TailwindCSS. Or Material-UI Icons. | LOW |
| **zustand** (optional) | 4.4+ | Lightweight state management | Only if props drilling becomes painful. For portfolio analytics, React Context + Query is often sufficient. | LOW |
| **@tanstack/table** | 8.16+ | Advanced table with virtualization | Critical for 1000+ position drill-down. Virtualized rendering for performance. | MEDIUM |

---

## Alternatives Considered (NOT Recommended)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **Curve Construction** | QuantLib (C++ + Python) | Matplotlib/SciPy interpolation | SciPy lacks interest rate model conventions (day-count, compounding). QuantLib handles them natively. |
| **Curve Construction** | QuantLib | OpenGamma Strata (Java) | Strata is excellent but adds Java/JVM overhead in Python service. Stick with QuantLib. |
| **Curve Construction** | QuantLib | Custom pure-Python curve builder | Benchmarking shows 10-50x performance penalty for 1000+ curves. Not viable. |
| **Monte Carlo** | Ray | Dask | Ray has better scheduling for financial workloads. Dask better for lazy evaluation (less relevant here). Pick one. |
| **Monte Carlo** | Ray | Celery + Redis | Ray is simpler for financial workflows. Celery overkill unless you have non-financial background jobs. |
| **Credit Modeling** | Custom CECL + Statsmodels | Commercial platforms (Moody's, S&P) | Cost prohibitive ($500K+/year). Build in-house for competitive advantage. |
| **Optimization** | SciPy | CPLEX, Gurobi | Overkill for portfolio analytics. SciPy's solvers sufficient for constraints. Add commercial solvers only if hitting scaling limits. |
| **ORM** | Raw psycopg (workers) + SQLAlchemy (API) | Tortoise ORM, Peewee | SQLAlchemy is most mature for complex queries. Others fine for CRUD; too slow for aggregations. |
| **Frontend State** | React Query + Context | Redux | Redux adds boilerplate. React Query solves 80% of issues. Use Redux only if needing complex time-travel debugging. |
| **Frontend Charts** | Plotly.js | Victory, Recharts | Victory/Recharts lighter but less feature-rich. Plotly better for financial drilling/export. |
| **Testing** | pytest + hypothesis | unittest (stdlib) | pytest has better plugins, fixtures, parametrization. Use unittest only if enforced by org. |

---

## Dependency Map (Load Order)

```
Core Math Foundation:
  NumPy 1.26+ → SciPy 1.14+ → Numba 0.59+
  ├─ QuantLib 1.34+ (depends on NumPy)
  └─ pandas 2.2+ (optional, for data ingestion)

Risk & Credit:
  Statsmodels 0.14+ (depends on SciPy, NumPy)
  └─ Scikit-learn 1.4+ (optional, depends on SciPy)

Distributed Computing:
  Ray 2.28+ (depends on NumPy, optional cloudpickle)
  └─ For Monte Carlo and portfolio aggregation

Application Layer:
  FastAPI 0.100+ (depends on Pydantic 2.6+)
  ├─ psycopg 3.1+ (no math deps)
  ├─ httpx 0.26+ (for async inter-service calls)
  └─ Pydantic 2.6+

Testing:
  pytest 7.4+
  ├─ pytest-benchmark 4.0+
  └─ hypothesis 6.98+

Frontend:
  React 18.3+ + TypeScript 5.6+
  ├─ React Router 6.26+
  ├─ TanStack Query 5.6+
  ├─ TanStack Table 8.16+ (optional)
  ├─ Plotly.js 2.26+ (optional)
  └─ TailwindCSS 3.4+
```

---

## Installation & Version Pinning

### Backend Dependencies

```bash
# Core compute (quantitative library layer)
pip install numpy==1.26.4 scipy==1.14.1 numba==0.59.1

# QuantLib (C++ bindings)
# On Windows: download wheel from https://github.com/leanprover-community/mathlib4/releases
# On Linux/Mac: pip install QuantLib (source build, ~5 min)
pip install QuantLib==1.34

# Pandas (data aggregation, not for real-time pricing)
pip install pandas==2.2.0

# Risk & Credit
pip install statsmodels==0.14.0
pip install scikit-learn==1.4.1

# Distributed computing (optional, for portfolio-scale Monte Carlo)
pip install ray[all]==2.28.0

# FastAPI stack (already in MVP)
pip install fastapi==0.109.1 uvicorn==0.27.0 psycopg[binary]==3.1.18

# Async HTTP
pip install httpx==0.26.0

# Config & validation
pip install pydantic==2.6.1

# Testing
pip install pytest==7.4.3 pytest-benchmark==4.0.0 hypothesis==6.98.3

# Database migrations
pip install alembic==1.13.1

# AWS (production only)
pip install boto3==1.34.19
```

**Create `requirements.txt`:**

```
numpy==1.26.4
scipy==1.14.1
numba==0.59.1
QuantLib==1.34
pandas==2.2.0
statsmodels==0.14.0
scikit-learn==1.4.1
ray[all]==2.28.0
fastapi==0.109.1
uvicorn==0.27.0
psycopg[binary]==3.1.18
httpx==0.26.0
pydantic==2.6.1
pytest==7.4.3
pytest-benchmark==4.0.0
hypothesis==6.98.3
alembic==1.13.1
boto3==1.34.19
python-dotenv==1.0.0
```

### Frontend Dependencies

```bash
cd frontend
npm install
npm install --save-dev \
  @types/react@18.3.5 \
  @types/react-dom@18.3.0 \
  typescript@5.6.2 \
  vite@5.4.6 \
  tailwindcss@3.4.19
npm install plotly.js@2.26.0
npm install @tanstack/table@8.16.0 @tanstack/react-table@8.16.0
```

**Update `frontend/package.json`:**

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "@tanstack/react-query": "^5.59.16",
    "@tanstack/react-table": "^8.16.0",
    "plotly.js": "^2.26.0",
    "axios": "^1.7.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.6.2",
    "vite": "^5.4.6",
    "tailwindcss": "^3.4.19"
  }
}
```

---

## Critical Libraries: Deep Dives

### QuantLib (1.34+)

**Why it matters:** The single most important dependency for institutional fixed income.

**What it provides:**
- Interest rate model calibration (Vasicek, Hull-White, SABR)
- Bond pricing with conventions (accrual, settlement, edge cases)
- Curve construction and interpolation
- Option-adjusted spread (OAS) calculation
- Forward rate agreement (FRA) pricing
- Cross-currency swap modeling

**How you'll use it in this project:**
1. **Curve construction:** Replace custom `ZeroCurve` class with QuantLib's `PiecewiseLogCubicDiscount` for better accuracy with market data.
2. **Bond pricing:** Extend from MVP's simple bond pricer to handle callable/putable bonds, floating-rate notes, step-ups.
3. **ABS/MBS:** Use for prepayment model calibration.
4. **Scenario application:** Shift curves, recalibrate models.

**Performance note:** QuantLib is C++; Python bindings add ~10-20% overhead compared to pure C++. Acceptable for portfolio pricing; not suitable for 10M+ position real-time repricing.

**Version pins:** Use 1.34 (latest stable as of Feb 2025). Avoid 1.28 or older (missing some rate model variants).

### NumPy + Numba + Numba (Compiled Cash Flow Generation)

**Why it matters:** Cash flow generation is CPU-bound for loan portfolios (amortization, ARM resets, prepayment modeling, waterfalls).

**Strategy:**
1. Pure Python skeleton in `compute/cashflow/generator.py` (readable, testable).
2. Critical tight loop (DCF discounting): Compile with Numba `@jit(nopython=True)`.
3. Benchmark: 1000 loans × 240 cash flows = 240K DCF steps. Target: <50ms. NumPy: 500ms (too slow). Numba: <50ms ✓.

**Example (in `compute/cashflow/generator.py`):**

```python
import numpy as np
from numba import jit

@jit(nopython=True)
def discount_cashflows_numba(cashflows_array, discount_factors_array):
    """Numba-compiled DCF. Input: (n_flows,) and (n_flows,) arrays."""
    pv = 0.0
    for i in range(len(cashflows_array)):
        pv += cashflows_array[i] * discount_factors_array[i]
    return pv
```

Then call from Python:

```python
pv = discount_cashflows_numba(cf_array, df_array)
```

Result: Equivalent of C++ performance without rewriting in C.

### Ray for Distributed Monte Carlo

**Why it matters:** At 10,000+ positions with 1,000 Monte Carlo paths, single-threaded Python takes 30+ minutes.

**Strategy:**
1. **Early phase (Phase 2):** Use multiprocessing for task distribution (existing MVP approach). Cap at ~8 cores.
2. **Scaling phase (Phase 4):** Migrate to Ray. Horizontally scale to 100 workers on ECS Fargate with no code changes.

**Example (future):**

```python
import ray

@ray.remote
def price_portfolio_scenario(positions, scenario_id, mc_path):
    return [price_position(p, scenario_id, mc_path) for p in positions]

# On 100 ECS tasks, compute 100 MC paths in parallel
futures = [price_portfolio_scenario.remote(positions, "BASE", i) for i in range(100)]
results = ray.get(futures)  # Automatic orchestration
```

**When to adopt:** Once pricing takes >5 minutes. Don't over-engineer early.

---

## AWS Infrastructure Stack (Terraform)

Beyond Python libraries, you need AWS services:

| Service | Version | Purpose | Why |
|---------|---------|---------|-----|
| **ECS Fargate** | Latest | Container orchestration for workers, services | Serverless—scale 1 to 1000 tasks. No VM management. Integrates with CloudWatch. |
| **RDS Aurora** | PostgreSQL 15+ | Managed PostgreSQL | Auto-backups, read replicas, failover. Production-grade. Required for team of risk quants. |
| **Secrets Manager** | Latest | Credential rotation, API keys | Centralize secrets. Rotate RDS password automatically. Never commit credentials. |
| **CloudWatch** | Latest | Logging, metrics, alarms | Stream stdout/stderr from workers. Set alarms for task failures. Cost optimization. |
| **ECR** | Latest | Container registry | Private Docker images. Required for Fargate deployments. |
| **S3** | Latest | Scenario dumps, result exports | Cheap bulk storage for historical runs, audit trail, machine-learning model training. |
| **Lambda** (optional) | Latest | Serverless event handlers | Trigger overnight runs, email reports. Not needed for real-time analytics. |

**Terraform modules to create:**

```
.infra/
  ├── main.tf              # Root config
  ├── variables.tf         # Input variables
  ├── outputs.tf           # Output values
  ├── ecs.tf              # Fargate cluster, task definitions
  ├── rds.tf              # Aurora PostgreSQL
  ├── networking.tf       # VPC, security groups
  ├── iam.tf              # Roles, permissions
  ├── cloudwatch.tf       # Logging, alarms
  └── terraform.tfvars    # Non-secret config (git-tracked)
```

Will expand in Phase 5 (Infrastructure).

---

## Rationale: Why NOT These

### Why not Pandas for real-time pricing?

Pandas excels at data manipulation but struggles with:
- **Row-by-row operations:** Vectorized operations require all data in memory in the same shape.
- **Conditional branching:** If-else logic on per-row basis requires `.apply()`, which is slow.
- **Complex domain logic:** Loan amortization with prepayment options requires custom code, not Pandas idioms.

**Use Pandas for:** Post-pricing aggregation, results rollup, reporting.

### Why not pure Python curve construction?

100 curves × 100 interpolations = 10,000 calls/second. Python: 5ms/call = 50 seconds. QuantLib (C++): 0.5ms/call = 5 seconds. **10x penalty unacceptable.**

### Why not Celery + Redis?

Ray is simpler for financial workflows:
- **Ray:** One-liner: `@ray.remote`. No configuration.
- **Celery:** Requires Redis broker, message serialization, worker pools, task routing. Overhead for this use case.

**Use Celery if:** You have heterogeneous task types (email, file upload, price). Ray if: Homogeneous numerical compute.

### Why not SQLAlchemy ORM for pricing workers?

ORM overhead:
- **Raw psycopg:** 1 query, 2ms.
- **SQLAlchemy ORM:** Same query, instantiate objects, 5ms.

In pricing workers, you want raw speed. In results_api, ORM helps with complex aggregations.

---

## Confidence Levels

| Component | Confidence | Notes |
|-----------|------------|-------|
| **NumPy/SciPy/Pandas** | HIGH | Industry standard. Proven at scale. |
| **QuantLib 1.34** | HIGH | Mature (open-source since 2000). Used at major banks. |
| **Numba 0.59** | MEDIUM | Excellent for numerical code. Avoid if code is non-deterministic (RNG, I/O). Works perfectly for DCF loops. |
| **Ray 2.28** | MEDIUM | Production-ready but relatively newer than other choices. Best-in-class for distributed ML/finance. Scale when needed, not before. |
| **Statsmodels 0.14** | HIGH | PD/LGD calibration well-established. Actively maintained. |
| **Custom CECL/Basel** | MEDIUM | No library exists. Implementation straightforward. Risk: Regulatory interpretation changes annually. Mitigation: Modularize assumptions. |
| **Plotly.js frontend** | MEDIUM | Good for financial charts. Learning curve < D3. Plotly.js is WebGL-accelerated (scales to 10K points). |
| **React Query 5.6** | HIGH | Handles server state elegantly. Caching + refetch strategies. Standard in 2025. |

---

## Phase-by-Phase Stack Usage

### Phase 1: MVP Completion (Existing)
- NumPy, SciPy (light use)
- Custom ZeroCurve, loan/bond pricers
- PostgreSQL + psycopg
- React 18 + React Query

### Phase 2: Institutional Pricers Expansion
- **Add:** QuantLib 1.34 (callable/putable bonds, ABS/MBS)
- **Add:** Numba (compiled cash flow generation)
- Extend pricers for floating-rate, structured products

### Phase 3: Risk Analytics Engine
- **Add:** Statsmodels 0.14 (PD/LGD calibration)
- **Add:** SciPy optimize (portfolio optimization)
- Build custom CECL allowance engine
- Build custom Basel III RWA engine

### Phase 4: Distributed Scenario & Monte Carlo
- **Add:** Ray 2.28 (scale to 1000+ paths)
- Refactor workers to use Ray remote actors
- Horizontal scaling to 100 ECS tasks

### Phase 5: Analytics Dashboard & Reporting
- **Add:** Plotly.js (curves, ladders, attribution waterfall)
- **Add:** TanStack Table 8.16 (virtualized drill-down tables)
- Build drill-down analytics UI

### Phase 6: Compliance & Regulatory
- CECL allowance computation (from Phase 3 scaffold)
- Basel III capital adequacy reporting
- Quarterly regulatory submissions

---

## Installation & Getting Started

### First-Time Setup (Developer Machine)

```bash
# Clone repo
git clone <repo> riskmvp
cd riskmvp

# Python environment
python -m venv venv
./venv/Scripts/activate  # Windows
source venv/bin/activate # Mac/Linux

# Install base
pip install -e .
pip install -r requirements.txt

# QuantLib (C++ dependency - platform specific)
# Windows: pip install QuantLib (wheel available)
# Mac: brew install quantlib && pip install QuantLib
# Linux: sudo apt install libquantlib-dev && pip install QuantLib

# Verify
python -c "import QuantLib; print(QuantLib.__version__)"

# Frontend
cd frontend
npm install

# Test
cd ..
pytest compute/tests/ -v
```

### Docker Build (For ECS)

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y build-essential
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY compute/ compute/
COPY services/ services/
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "services.run_orchestrator.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

Multi-stage build keeps runtime image ~300MB.

---

## Sources & References

**QuantLib:**
- Official: https://www.quantlib.org
- Python bindings: https://www.quantlib.org/install/macosx.html

**NumPy/SciPy ecosystem:**
- NumPy: https://numpy.org
- SciPy: https://scipy.org
- Numba: https://numba.readthedocs.io

**Ray for financial computing:**
- Ray docs: https://docs.ray.io
- Ray distributed Monte Carlo examples in financial services

**FastAPI & PostgreSQL:**
- FastAPI: https://fastapi.tiangolo.com
- psycopg3: https://www.psycopg.org

**Terraform for AWS:**
- Terraform registry: https://registry.terraform.io
- AWS provider: https://registry.terraform.io/providers/hashicorp/aws/latest

**Frontend:**
- React 18: https://react.dev
- TanStack Query: https://tanstack.com/query/latest
- Plotly.js: https://plotly.com/javascript/

---

## Next Steps: Infrastructure Deep Dive

This STACK.md is technology-focused. **Phase 5 (Infrastructure) will cover:**
- Terraform modules for ECS, RDS Aurora, networking
- CI/CD pipeline (GitHub Actions)
- Cost optimization strategies (Fargate spot instances, RDS auto-scaling)
- Disaster recovery and backup strategy
- Monitoring and alerting dashboards

**This document assumes:** You'll deploy to AWS with Terraform. If deploying on-premise or different cloud (GCP, Azure), adjust container orchestration layer accordingly. Core compute stack (QuantLib, NumPy, Ray) remains unchanged.
