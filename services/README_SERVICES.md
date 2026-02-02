# Services (FastAPI) - MVP

Packages:
- services.marketdata_svc.app.main:app
- services.run_orchestrator.app.main:app
- services.results_api.app.main:app

Environment:
- DATABASE_URL=postgresql://postgres:postgres@localhost:5432/iprs

Run (PowerShell):
  $env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iprs"
  uvicorn services.marketdata_svc.app.main:app --reload --port 8001
  uvicorn services.run_orchestrator.app.main:app --reload --port 8002
  uvicorn services.results_api.app.main:app --reload --port 8003
