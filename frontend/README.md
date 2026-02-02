\
# Risk MVP Frontend (React)

Minimal React (Vite + TypeScript) UI that matches your MVP demo endpoints/ports.

## Ports / services
- marketdata-svc:   http://127.0.0.1:8001
- run-orchestrator: http://127.0.0.1:8002
- results-api:      http://127.0.0.1:8003

## Dev proxy (Vite)
- /mkt     -> 8001
- /orch    -> 8002
- /results -> 8003

## Install / run (PowerShell)
Backend (leave running):
```powershell
cd C:\Users\omack\Intrepid\pythonFramework\RiskPlatform\riskmvp
powershell -ExecutionPolicy Bypass -File scripts\demo_runner.ps1 -NoCleanup
```

Frontend:
```powershell
cd C:\Users\omack\Intrepid\pythonFramework\RiskPlatform\riskmvp\frontend
npm install
npm run dev
```

Open http://localhost:5173 (or whatever Vite prints).
