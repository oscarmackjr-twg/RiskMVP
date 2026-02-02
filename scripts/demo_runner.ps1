<#
Demo Runner - MVP Risk Platform (Exec Demo)

Starts services + worker, verifies health, loads fixtures, creates run,
polls for results, checks cube aggregation, prints PASS/FAIL checklist,
and optionally keeps services running.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts/demo_runner.ps1
  powershell -ExecutionPolicy Bypass -File scripts/demo_runner.ps1 -NoCleanup
  powershell -ExecutionPolicy Bypass -File scripts/demo_runner.ps1 -KillExisting

Notes / Hardening:
  - Prints ports + OpenAPI URLs up front.
  - On FAIL, auto-tails last N lines of *.err.log and *.log for fast triage.
  - Writes positions JSON as UTF-8 *without BOM* (prevents JSONDecodeError "Unexpected UTF-8 BOM").
#>

param(
  [switch]$NoCleanup,
  [switch]$KillExisting
)

$ErrorActionPreference = "Stop"
$script:NoCleanup = $NoCleanup

# -------------------- Config --------------------
$Ports = @{
  Market       = $(if ($env:MARKETDATA_PORT)   { [int]$env:MARKETDATA_PORT }   else { 8001 })
  Orchestrator = $(if ($env:ORCHESTRATOR_PORT) { [int]$env:ORCHESTRATOR_PORT } else { 8002 })
  Results      = $(if ($env:RESULTS_PORT)      { [int]$env:RESULTS_PORT }      else { 8003 })
}

$Env:PYTHONUNBUFFERED = "1"
if (-not $Env:DATABASE_URL) {
  $Env:DATABASE_URL = "postgresql://postgres:Gillian2026!!!@localhost:5432/riskmvp"
}
Write-Host "[env] DATABASE_URL=$($env:DATABASE_URL)"

# Resolve python executable reliably (venv/python/py fallback)
$PythonExe = $null
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd) { $PythonExe = $cmd.Source }
if (-not $PythonExe) {
  $cmd = Get-Command py -ErrorAction SilentlyContinue
  if ($cmd) { $PythonExe = $cmd.Source }
}
if (-not $PythonExe) { throw "Python executable not found (python or py not on PATH)" }
Write-Host "[python] Using $PythonExe"

# Fixture paths
$FixtureMarket    = "demo/fixtures/market_snapshot_demo.json"
$FixturePositions = "demo/fixtures/positions_snapshot_demo.json"
$FixtureRunReq    = "demo/fixtures/run_request_demo.json"

# Orchestrator reads positions from a file.
$PositionsInputPath = "demo/inputs/positions.json"
$Env:POSITIONS_SNAPSHOT_PATH = $PositionsInputPath

$LogsDir = "demo/logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

$HealthTimeoutSec = 40
$PollTimeoutSec   = 120
$PollIntervalSec  = 2

$TailLines = 120

# ---- Defaults ----
if (-not $RunId) { $RunId = "RUN_" + (Get-Date -Format "yyyyMMdd_HHmmss") }
if (-not $AsOfTime) { $AsOfTime = "2026-01-23T00:00:00Z" }
if (-not $PortfolioNodeId) { $PortfolioNodeId = "BOOK-PRIME-LOANS" }

# -------------------- Process tracking (script-scope) --------------------
$script:procs = @()

# -------------------- Helpers --------------------
function Write-Section([string]$msg) {
  Write-Host ""
  Write-Host "============================================================"
  Write-Host $msg
  Write-Host "============================================================"
}

function Stop-ProcSafe($p) {
  if ($null -ne $p -and -not $p.HasExited) {
    try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
  }
}

function Tail-File([string]$path, [int]$n = 80) {
  if (Test-Path $path) {
    Write-Host ""
    Write-Host ("--- tail {0}: {1} ---" -f $n, $path) -ForegroundColor Yellow
    try { Get-Content $path -Tail $n } catch { Write-Host ("(failed to read: {0})" -f $_.Exception.Message) }
  }
}

function Dump-Logs([int]$n = 80) {
  Write-Section "Auto-Triage: Tail Logs"
  Tail-File (Join-Path $LogsDir "marketdata-svc.err.log") $n
  Tail-File (Join-Path $LogsDir "run-orchestrator.err.log") $n
  Tail-File (Join-Path $LogsDir "results-api.err.log") $n
  Tail-File (Join-Path $LogsDir "worker.err.log") $n

  # also tail stdout logs (often contain request lines)
  Tail-File (Join-Path $LogsDir "marketdata-svc.log") $n
  Tail-File (Join-Path $LogsDir "run-orchestrator.log") $n
  Tail-File (Join-Path $LogsDir "results-api.log") $n
  Tail-File (Join-Path $LogsDir "worker.log") $n
}

function Cleanup-And-Exit([int]$ExitCode = 0) {
  if (-not $script:NoCleanup) {
    Write-Section "Cleanup: Stopping Services + Worker"
    foreach ($p in $script:procs) { Stop-ProcSafe $p }
    Write-Host "DONE: Cleanup complete." -ForegroundColor Green
  } else {
    Write-Section "Cleanup skipped (NoCleanup=true)"
    Write-Host "DONE: Services left running." -ForegroundColor Green
  }
  exit $ExitCode
}

function Fail([string]$msg) {
  Write-Host ("FAIL: " + $msg) -ForegroundColor Red
  Write-Host "Check logs in demo/logs for details." -ForegroundColor Yellow
  Dump-Logs $TailLines
  Cleanup-And-Exit 1
}

function Pass([string]$msg) { Write-Host ("PASS: " + $msg) -ForegroundColor Green }
function Warn([string]$msg) { Write-Host ("WARN: " + $msg) -ForegroundColor Yellow }

function Read-JsonFile([string]$path) {
  if (-not (Test-Path $path)) { Fail ("Missing fixture file: " + $path) }
  return Get-Content $path -Raw | ConvertFrom-Json
}

function Write-JsonFileNoBom([string]$path, $obj, [int]$depth = 80) {
  $dir = Split-Path -Parent $path
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

  $json = $obj | ConvertTo-Json -Depth $depth

  # UTF-8 without BOM (fixes Python json.load "Unexpected UTF-8 BOM")
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($path, $json, $utf8NoBom)
}

function Start-Proc {
  param(
    [Parameter(Mandatory)] [string]   $Name,
    [Parameter(Mandatory)] [string]   $Exe,
    [Parameter(Mandatory)] [string[]] $ArgList,
    [Parameter(Mandatory)] [string]   $LogPath,
    [string] $WorkingDir = (Get-Location).Path
  )

  if ([string]::IsNullOrWhiteSpace($Exe)) { throw "Start-Proc: '$Name' exe is empty" }
  if (-not $ArgList -or $ArgList.Count -eq 0) { throw "Start-Proc: '$Name' args are empty. Exe='$Exe' Log='$LogPath'" }
  foreach ($a in $ArgList) {
    if ([string]::IsNullOrWhiteSpace([string]$a)) {
      throw "Start-Proc: '$Name' has a blank arg. Args=[$($ArgList -join ' ')]"
    }
  }

  $logOut = $LogPath
  $logErr = [System.IO.Path]::ChangeExtension($LogPath, ".err.log")
  $dir = Split-Path -Parent $logOut
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

  Write-Host "Starting $Name..."
  Write-Host "  Exe : $Exe"
  Write-Host "  Args: $($ArgList -join ' ')"
  Write-Host "  Out : $logOut"
  Write-Host "  Err : $logErr"

  $p = Start-Process -FilePath $Exe -ArgumentList $ArgList `
    -WorkingDirectory $WorkingDir `
    -NoNewWindow -PassThru `
    -RedirectStandardOutput $logOut `
    -RedirectStandardError  $logErr

  return $p
}

function Wait-Health([string]$url, [int]$timeoutSec) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
    try {
      $r = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 4
      if ($r.ok -eq $true) { return $true }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  return $false
}

function Post-Json([string]$url, $obj) {
  $body = $obj | ConvertTo-Json -Depth 80
  Write-Host "[HTTP] POST $url"
  Write-Host "[HTTP] Body:`n$body"

  try {
    return Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Body $body
  }
  catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.GetResponseStream()) {
      try {
        $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $text = $sr.ReadToEnd()
        Write-Host "`n=== HTTP error response body ===" -ForegroundColor Red
        Write-Host $text
        Write-Host "=== end body ===`n" -ForegroundColor Red
      } catch {
        Write-Host "HTTP error (could not read response body): $($_.Exception.Message)" -ForegroundColor Red
      }
    } else {
      Write-Host "HTTP error: $($_.Exception.Message)" -ForegroundColor Red
    }
    throw
  }
}

function Build-Url([string]$baseUrl, [string[]]$pairs) {
  $ub = [System.UriBuilder]::new($baseUrl)
  if ($pairs -and $pairs.Count -gt 0) {
    $ub.Query = [System.String]::Join([char]38, $pairs)  # '&'
  }
  return $ub.Uri.AbsoluteUri
}

function Stop-ListeningOnPort([int]$Port) {
  # Windows-safe: stop PID(s) listening on TCP port
  try {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
      if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
        Write-Host "[kill] Port $Port PID=$($c.OwningProcess)" -ForegroundColor Yellow
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
      }
    }
  } catch {}
}

# Ensure cleanup happens if PowerShell exits unexpectedly
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
  if (-not $script:NoCleanup) {
    foreach ($p in $script:procs) {
      if ($null -ne $p -and -not $p.HasExited) {
        try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
      }
    }
  }
} | Out-Null

# -------------------- Print endpoints (demo-friendly) --------------------
Write-Section "Demo Endpoints"
Write-Host "[ports] Market=$($Ports.Market) Orchestrator=$($Ports.Orchestrator) Results=$($Ports.Results)" -ForegroundColor Cyan
Write-Host ("[openapi] Market       http://localhost:{0}/docs" -f $Ports.Market) -ForegroundColor DarkGray
Write-Host ("[openapi] Orchestrator http://localhost:{0}/docs" -f $Ports.Orchestrator) -ForegroundColor DarkGray
Write-Host ("[openapi] Results      http://localhost:{0}/docs" -f $Ports.Results) -ForegroundColor DarkGray
Write-Host ("[env] POSITIONS_SNAPSHOT_PATH={0}" -f $Env:POSITIONS_SNAPSHOT_PATH) -ForegroundColor DarkGray

# -------------------- Preflight: fixtures --------------------
Write-Section "Demo Preflight - Fixtures"
$fixtureList = @($FixtureMarket, $FixturePositions, $FixtureRunReq)
foreach ($item in $fixtureList) {
  if (Test-Path $item) { Pass ("Found " + $item) }
  else { Fail ("Missing " + $item + ". Create it or update script paths.") }
}

# -------------------- Preflight: DB smoke test --------------------
Write-Section "Demo Preflight - DB Smoke Test"
if (Test-Path "scripts/db_smoke_test.py") {
  & $PythonExe scripts/db_smoke_test.py
  if ($LASTEXITCODE -ne 0) { Fail "DB smoke test failed. Fix DB schema before demo." }
  Pass "DB smoke test passed"
} else {
  Warn "scripts/db_smoke_test.py not found - skipping DB table verification"
}

# -------------------- Step 0: Write positions file BEFORE services start --------------------
Write-Section "Preflight - Prepare Positions Payload (file for orchestrator)"
$positions = Read-JsonFile $FixturePositions
Write-JsonFileNoBom $PositionsInputPath $positions 80
Pass ("Wrote positions payload (UTF-8 no BOM) to " + $PositionsInputPath)

# -------------------- Optional: kill anything already bound to ports --------------------
if ($KillExisting) {
  Write-Section "Kill Existing Listeners on Demo Ports"
  Stop-ListeningOnPort $Ports.Market
  Stop-ListeningOnPort $Ports.Orchestrator
  Stop-ListeningOnPort $Ports.Results
  Pass "Killed any existing listeners (if found)"
}

# -------------------- Start processes --------------------
Write-Section "Starting Services + Worker"

$logMarket  = Join-Path $LogsDir "marketdata-svc.log"
$logOrch    = Join-Path $LogsDir "run-orchestrator.log"
$logResults = Join-Path $LogsDir "results-api.log"
$logWorker  = Join-Path $LogsDir "worker.log"

$script:procs += Start-Proc "marketdata-svc" $PythonExe @(
  "-m","uvicorn","services.marketdata_svc.app.main:app",
  "--port", "$($Ports.Market)"
) $logMarket

$script:procs += Start-Proc "run-orchestrator" $PythonExe @(
  "-m","uvicorn","services.run_orchestrator.app.main:app",
  "--port", "$($Ports.Orchestrator)"
) $logOrch

$script:procs += Start-Proc "results-api" $PythonExe @(
  "-m","uvicorn","services.results_api.app.main:app",
  "--port", "$($Ports.Results)"
) $logResults

$script:procs += Start-Proc "compute-worker" $PythonExe @(
  "-m","compute.worker.worker"
) $logWorker

# -------------------- Health checks --------------------
Write-Section "Health Checks"

if (Wait-Health ("http://localhost:" + $Ports.Market + "/health") $HealthTimeoutSec) { Pass "marketdata-svc /health ok" }
else { Fail ("marketdata-svc failed health check. See " + $logMarket) }

if (Wait-Health ("http://localhost:" + $Ports.Orchestrator + "/health") $HealthTimeoutSec) { Pass "run-orchestrator /health ok" }
else { Fail ("run-orchestrator failed health check. See " + $logOrch) }

if (Wait-Health ("http://localhost:" + $Ports.Results + "/health") $HealthTimeoutSec) { Pass "results-api /health ok" }
else { Fail ("results-api failed health check. See " + $logResults) }

Pass "All services are healthy"

# -------------------- Load remaining fixtures --------------------
Write-Section "Load Demo Fixtures"
$market   = Read-JsonFile $FixtureMarket
$runReqFx = Read-JsonFile $FixtureRunReq
Pass "Loaded fixture JSON"

# -------------------- Step 1: Market snapshot --------------------
Write-Section "Step 1: Create Market Data Snapshot"
$marketUrl  = "http://localhost:$($Ports.Market)/api/v1/marketdata/snapshots"
$marketResp = Post-Json $marketUrl $market
if (-not $marketResp.snapshot_id) { Fail "marketdata snapshot response missing snapshot_id" }
Pass ("Created/updated MarketDataSnapshot snapshot_id=" + $marketResp.snapshot_id)

# -------------------- Step 2: (file-driven) Position snapshot --------------------
Write-Section "Step 2: Position Snapshot (file-driven for orchestrator)"
Pass ("Orchestrator will read positions from " + $PositionsInputPath)

# -------------------- Step 3: Create run --------------------
Write-Section "Step 3: Create Run (fan-out tasks)"

if ([string]::IsNullOrWhiteSpace($RunId)) { $RunId = "RUN_" + (Get-Date -Format "yyyyMMdd_HHmmss") }
if ([string]::IsNullOrWhiteSpace($AsOfTime)) { $AsOfTime = "2026-01-23T00:00:00Z" }
if ([string]::IsNullOrWhiteSpace($PortfolioNodeId)) { $PortfolioNodeId = "BOOK-PRIME-LOANS" }
if ($null -eq $marketResp -or [string]::IsNullOrWhiteSpace($marketResp.snapshot_id)) { Fail "Step 1 snapshot_id is missing" }

$runReq = $runReqFx
$runReq.run_id = $RunId
if (-not $runReq.run_type) { $runReq.run_type = "SANDBOX" }
$runReq.as_of_time = $AsOfTime
$runReq.market_snapshot_id = $marketResp.snapshot_id

if (-not $runReq.portfolio_scope) { $runReq.portfolio_scope = @{} }
$runReq.portfolio_scope.node_ids = @($PortfolioNodeId)

if (-not $runReq.measures -or $runReq.measures.Count -lt 1) { $runReq.measures = @("PV") }

$runUrl  = "http://localhost:$($Ports.Orchestrator)/api/v1/runs"
$runResp = Post-Json $runUrl $runReq

if (-not $runResp.run_id) { Fail "run create response missing run_id" }
$runId = $runResp.run_id

if ($runResp.PSObject.Properties.Name -contains "status") {
  Pass ("Run created run_id=" + $runId + " status=" + $runResp.status)
} else {
  Pass ("Run created run_id=" + $runId)
}

# -------------------- Step 4: Poll results --------------------
Write-Section "Step 4: Poll Results until PV exists"
$summaryBase = "http://localhost:$($Ports.Results)/api/v1/results/$runId/summary"
$summaryUrl  = Build-Url $summaryBase @("scenario_id=BASE")

$sw = [Diagnostics.Stopwatch]::StartNew()
$gotResults = $false
$lastErr = $null
$lastSum = $null

while ($sw.Elapsed.TotalSeconds -lt $PollTimeoutSec) {
  try {
    $sum = Invoke-RestMethod -Uri $summaryUrl -Method GET -TimeoutSec 5
    $lastSum = $sum

    # results-api returns: { rows, pv_sum }
    if (($sum.rows -as [int]) -ge 1 -and $null -ne $sum.pv_sum) {
      $gotResults = $true
      Pass ("Results present: rows=" + $sum.rows + " pv_sum=" + $sum.pv_sum)
      break
    }
  } catch {
    $lastErr = $_
  }

  Start-Sleep -Seconds $PollIntervalSec
}

if (-not $gotResults) {
  Warn "Timed out waiting for results."
  Warn ("Summary URL: " + $summaryUrl)

  if ($null -ne $lastSum) {
    Warn ("Last summary response: " + ($lastSum | ConvertTo-Json -Depth 10))
  } elseif ($null -ne $lastErr) {
    Warn ("Last error: " + $lastErr.Exception.Message)
  }

  Warn ("Open logs: " + $logWorker)
  Warn ("          " + $logOrch)
  Warn ("          " + $logResults)
  Fail ("No results produced within " + $PollTimeoutSec + " seconds.")
}

# -------------------- Step 5: Cube aggregation sanity --------------------
Write-Section "Step 5: Sanity Checks (Aggregations)"
$cubeBase = "http://localhost:$($Ports.Results)/api/v1/results/$runId/cube"
$cubeUrl  = Build-Url $cubeBase @("measure=PV","by=product_type","scenario_id=BASE")

$cube = Invoke-RestMethod -Uri $cubeUrl -Method GET -TimeoutSec 10
if ($null -eq $cube) { Fail "Cube aggregation returned null response" }

$cubeCount = 1
if ($cube -is [System.Array]) { $cubeCount = $cube.Count }
if ($cubeCount -lt 1) { Fail "Cube aggregation returned no rows" }

Pass ("Cube aggregation ok (PV by product_type): returned " + $cubeCount + " rows")

# -------------------- Final checklist --------------------
Write-Section "EXEC DEMO CHECKLIST - READY"
Pass "Services start cleanly"
Pass "Health checks OK"
Pass "Market snapshot POST works"
Pass "Position snapshot file prepared"
Pass "Run creation works"
Pass "Worker processed tasks and wrote results"
Pass "Results summary endpoint works"
Pass "Results cube endpoint works"

Write-Host ""
Write-Host ("Demo Run ID: " + $runId) -ForegroundColor Cyan
Write-Host ("Results Summary: " + $summaryUrl) -ForegroundColor Cyan
Write-Host ("Results Cube: " + $cubeUrl) -ForegroundColor Cyan
Write-Host ("Logs at: " + $LogsDir) -ForegroundColor Cyan

Cleanup-And-Exit 0
