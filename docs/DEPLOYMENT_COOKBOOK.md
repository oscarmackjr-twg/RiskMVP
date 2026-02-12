# IPRS Deployment Cookbook

A step-by-step guide to deploying IPRS (Intrepid Portfolio Risk System) locally via Docker Compose and to AWS via Terraform.

## Table of Contents

1. [Prerequisites](#part-1-prerequisites)
2. [Local Deployment](#part-2-local-deployment)
3. [Load Market Data](#part-3-load-market-data)
4. [Run Your First Valuation](#part-4-run-your-first-valuation)
5. [AWS Deployment](#part-5-aws-deployment)
6. [Troubleshooting](#part-6-troubleshooting)

---

## Part 1: Prerequisites

### Required Software

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| Docker Desktop | 24+ | Container runtime | [docker.com](https://www.docker.com/products/docker-desktop) |
| Python | 3.11+ | Scripts, compute engine | [python.org](https://www.python.org/downloads/) |
| Node.js | 20+ | Frontend build | [nodejs.org](https://nodejs.org/) |
| Git | 2.x | Source control | [git-scm.com](https://git-scm.com/) |

### For AWS Deployment (optional)

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| AWS CLI | v2 | AWS operations | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| Terraform | 1.0+ | Infrastructure as code | [terraform.io](https://www.terraform.io/downloads) |

### API Keys (free)

| Key | Purpose | Get it at |
|-----|---------|-----------|
| FRED API Key | Real market data (Treasury yields, SOFR, credit spreads) | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) |

No key needed for FX rates (Frankfurter uses ECB reference rates, no auth required).

### Python Packages for Scripts

```bash
pip install requests
```

---

## Part 2: Local Deployment

### Quick Start (one command)

**PowerShell:**
```powershell
.\scripts\setup-local.ps1
```

**Bash:**
```bash
./scripts/setup-local.sh
```

This will:
1. Check prerequisites
2. Build all 9 Docker images
3. Start PostgreSQL + 7 services + worker + frontend
4. Wait for database to be healthy
5. Verify all endpoints

### Manual Step-by-Step

#### 1. Build all images

```bash
cd docker
docker compose build
```

Expected output: 9 images built successfully (db, marketdata, orchestrator, results, worker, portfolio, risk, regulatory, ingestion, frontend).

#### 2. Start the stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

#### 3. Verify database is ready

```bash
docker inspect --format='{{.State.Health.Status}}' iprs-db
# Should output: healthy
```

#### 4. Check all services

```bash
curl http://localhost:8001/health   # marketdata
curl http://localhost:8002/health   # orchestrator
curl http://localhost:8003/health   # results
curl http://localhost:8005/health   # portfolio
curl http://localhost:8006/health   # risk
curl http://localhost:8007/health   # regulatory
curl http://localhost:8008/health   # ingestion
curl http://localhost:80/           # frontend
```

Each health endpoint should return `{"ok": true}`.

#### 5. Check deep health (DB connectivity)

```bash
curl http://localhost:8001/health/deep
# {"ok": true, "db": "connected"}
```

### Service Map

| Service | Direct Port | Via Frontend Proxy |
|---------|-------------|-------------------|
| Frontend | http://localhost:80 | — |
| Market Data | http://localhost:8001 | http://localhost/mkt/ |
| Orchestrator | http://localhost:8002 | http://localhost/orch/ |
| Results API | http://localhost:8003 | http://localhost/results/ |
| Portfolio | http://localhost:8005 | http://localhost/portfolio/ |
| Risk | http://localhost:8006 | http://localhost/risk/ |
| Regulatory | http://localhost:8007 | http://localhost/regulatory/ |
| Ingestion | http://localhost:8008 | http://localhost/ingestion/ |
| PostgreSQL | localhost:5432 | — |
| Worker | (no port) | — |

### Stopping and Restarting

```bash
# Stop everything
cd docker && docker compose down

# Stop but keep data volume
cd docker && docker compose down

# Stop and delete everything including data
cd docker && docker compose down -v

# Restart a single service
docker compose restart marketdata
```

---

## Part 3: Load Market Data

IPRS uses two free data sources:
- **FRED** (St. Louis Fed): Treasury yield curve, SOFR, Fed Funds rate, corporate credit spreads
- **Frankfurter** (ECB): FX spot rates

### Step 1: Get a FRED API Key

1. Go to https://fred.stlouisfed.org/docs/api/api_key.html
2. Create an account (free)
3. Request an API key
4. Save the key — you'll use it in the next step

### Step 2: Run the Seed Script

```bash
python scripts/seed-market-data.py --fred-key YOUR_FRED_API_KEY
```

Expected output:
```
=== IPRS Market Data Seeder ===

[1/4] Fetching Treasury yield curve from FRED...
  1M: 5.36%
  3M: 5.23%
  ...
  30Y: 4.56%

[2/4] Fetching SOFR, Fed Funds, credit spread from FRED...
  SOFR:          5.33%
  Fed Funds:     5.33%
  Credit Spread: 117 bps

[3/4] Fetching FX rates from Frankfurter (ECB)...
  EURUSD: 1.089245
  GBPUSD: 1.268170
  ...

[4/4] Building market data snapshot...
  POSTing to http://localhost:8001/api/v1/marketdata/snapshots...

  Snapshot created: MKT-FRED-20260212-1430

=== Done ===
Use this snapshot_id in run requests: MKT-FRED-20260212-1430
```

### Step 3: Verify the Curve Loaded

```bash
curl http://localhost:8001/api/v1/marketdata/snapshots/MKT-FRED-20260212-1430
```

### Dry Run (no POST, just print)

```bash
python scripts/seed-market-data.py --fred-key YOUR_KEY --dry-run
```

### Data Sources Reference

| Data | FRED Series | Description |
|------|------------|-------------|
| Treasury 1M | DGS1MO | 1-month constant maturity |
| Treasury 3M | DGS3MO | 3-month constant maturity |
| Treasury 6M | DGS6MO | 6-month constant maturity |
| Treasury 1Y-30Y | DGS1..DGS30 | Full term structure |
| SOFR | SOFR | Secured Overnight Financing Rate |
| Fed Funds | DFF | Federal Funds Effective Rate |
| Credit Spread | BAMLC0A0CM | ICE BofA US Corporate OAS |

FX rates from Frankfurter: EUR, GBP, JPY, CHF, CAD, AUD (ECB reference rates).

---

## Part 4: Run Your First Valuation

### Step 1: Upload Positions

The demo positions are auto-loaded from `demo/inputs/positions.json` by the orchestrator. To upload additional positions:

```bash
curl -X POST http://localhost:8002/api/v1/positions/snapshot \
  -H "Content-Type: application/json" \
  -d @demo/fixtures/positions_snapshot_demo.json
```

### Step 2: Submit a Run

```bash
curl -X POST http://localhost:8002/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "run_type": "SANDBOX",
    "as_of_time": "2026-01-23T00:00:00Z",
    "market_snapshot_id": "MKT-FRED-20260212-1430",
    "model_set_id": "MODELSET-DEMO-001",
    "portfolio_scope": {"node_ids": ["BOOK-PRIME-LOANS"]},
    "measures": ["PV", "DV01"],
    "scenarios": [{"scenario_set_id": "BASE"}],
    "execution": {"hash_mod": 1}
  }'
```

Note the `run_id` from the response.

### Step 3: Poll for Completion

```bash
curl http://localhost:8002/api/v1/runs/YOUR_RUN_ID
# Look for "status": "COMPLETED"
```

### Step 4: Get Results

```bash
# Summary
curl http://localhost:8003/api/v1/results/YOUR_RUN_ID/summary

# Full result cube
curl http://localhost:8003/api/v1/results/YOUR_RUN_ID/cube
```

### Step 5: View in Frontend

Open http://localhost in your browser. The React frontend provides:
- **Run Launcher** — submit new valuation runs
- **Run Results** — view summary results
- **Run Cube** — drill-down pivot table

---

## Part 5: AWS Deployment

### Quick Deploy (one command)

**PowerShell:**
```powershell
.\scripts\deploy-aws.ps1 -Region us-east-1 -Environment dev
```

**Bash:**
```bash
./scripts/deploy-aws.sh --region=us-east-1 --environment=dev
```

This orchestrates the full deployment: Terraform, ECR push, migrations, ECS deploy.

### Manual Step-by-Step

#### 1. Configure AWS Credentials

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Verify
aws sts get-caller-identity
```

#### 2. Set Terraform Variables

```bash
cd terraform

# Create terraform.tfvars
cat > terraform.tfvars << EOF
aws_region         = "us-east-1"
environment        = "dev"
db_master_password = "YourSecurePassword123!"
EOF
```

#### 3. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

Expected resources created:
- VPC with public/private subnets
- Aurora PostgreSQL cluster + RDS Proxy
- ECS Fargate cluster
- 9 ECR repositories
- Application Load Balancer
- 8 ECS services (7 API + 1 worker)

#### 4. Build and Push Images

```powershell
.\scripts\build-images.ps1
.\scripts\push-ecr.ps1 -AccountId (aws sts get-caller-identity --query Account --output text)
```

Or bash:
```bash
./scripts/build-images.sh
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./scripts/push-ecr.sh --account-id=$ACCOUNT_ID
```

#### 5. Apply Migrations

Get the RDS endpoint from Terraform output:
```bash
cd terraform
DB_ENDPOINT=$(terraform output -raw rds_proxy_endpoint)
```

Apply migrations:
```bash
DATABASE_URL="postgresql://postgres:YourPassword@${DB_ENDPOINT}:5432/iprs" \
  ./scripts/apply-migrations.sh
```

#### 6. Force New ECS Deployments

```bash
CLUSTER=iprs-cluster-dev
for svc in marketdata orchestrator results worker portfolio risk regulatory ingestion; do
  aws ecs update-service --cluster $CLUSTER --service iprs-${svc}-dev --force-new-deployment
done
```

#### 7. Verify

```bash
ALB_DNS=$(cd terraform && terraform output -raw alb_dns_name)

# Health checks
curl http://$ALB_DNS/mkt/health
curl http://$ALB_DNS/orch/health
curl http://$ALB_DNS/results/health

# Full smoke test
python scripts/smoke-test.py --base-url http://$ALB_DNS

# Deployment verification
./scripts/verify-deployment.sh --alb-dns=$ALB_DNS
```

---

## Part 6: Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker compose -f docker/docker-compose.yml logs marketdata

# Check if port is already in use
netstat -an | findstr 8001     # Windows
lsof -i :8001                  # macOS/Linux
```

**Database not ready:**
```bash
# Check db health
docker inspect iprs-db --format='{{.State.Health.Status}}'

# Connect directly
docker exec -it iprs-db psql -U postgres -d iprs

# Check tables exist
docker exec -it iprs-db psql -U postgres -d iprs -c "\dt"
```

**Image build fails:**
```bash
# Build a specific service with verbose output
docker build -t iprs-marketdata -f docker/Dockerfile.marketdata .

# Clear Docker build cache
docker builder prune
```

**Port conflicts:**

If port 80 is in use (IIS, Apache, etc.), change the frontend port in `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "3000:80"  # Use port 3000 instead
```

### Service Issues

**Service returns 500:**
```bash
# Check service logs
docker compose -f docker/docker-compose.yml logs --tail=50 marketdata

# Check DB connectivity
curl http://localhost:8001/health/deep
```

**Worker not processing tasks:**
```bash
# Check worker logs
docker compose -f docker/docker-compose.yml logs --tail=50 worker

# Verify worker can reach DB
docker exec iprs-worker python -c "
from services.common.db import db_conn
with db_conn() as c:
    c.execute('SELECT 1')
    print('DB OK')
"
```

### AWS Issues

**ECS service not starting:**
```bash
# Check events
aws ecs describe-services --cluster iprs-cluster-dev --services iprs-marketdata-dev \
  --query 'services[0].events[:5]'

# Check task stopped reason
aws ecs list-tasks --cluster iprs-cluster-dev --service-name iprs-marketdata-dev --desired-status STOPPED
aws ecs describe-tasks --cluster iprs-cluster-dev --tasks TASK_ARN \
  --query 'tasks[0].stoppedReason'
```

**Can't connect to RDS:**
```bash
# Verify security groups allow traffic
aws ec2 describe-security-groups --group-ids SG_ID

# Check RDS status
aws rds describe-db-clusters --db-cluster-identifier iprs-aurora-dev
```

**ALB returning 502/503:**
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN

# Check CloudWatch logs
aws logs tail /ecs/iprs-dev --since 5m
```

### Rollback

**Local:**
```bash
# Stop everything and restart clean
cd docker
docker compose down -v
docker compose up -d
```

**AWS:**
```bash
# Roll back to previous task definition
aws ecs update-service --cluster iprs-cluster-dev \
  --service iprs-marketdata-dev \
  --task-definition iprs-marketdata-dev:PREVIOUS_REVISION

# Or roll back infrastructure
cd terraform
terraform plan   # review changes
terraform apply
```

### Reset Database

**Local (wipe and rebuild):**
```bash
cd docker
docker compose down -v    # -v removes the data volume
docker compose up -d      # recreates with fresh schema
```

**AWS (re-run migrations):**
```bash
# Connect via bastion or direct if accessible
psql $DATABASE_URL -f sql/001_mvp_core.sql
psql $DATABASE_URL -f sql/002_portfolio_data_services.sql
psql $DATABASE_URL -f sql/003_regulatory_analytics.sql
```

### Run Smoke Tests

```bash
# Quick (skip run submission, ~10s)
python scripts/smoke-test.py --skip-run

# Full pipeline (~60s, includes run + result verification)
python scripts/smoke-test.py

# Against AWS
python scripts/smoke-test.py --base-url http://YOUR-ALB-DNS
```
