#!/usr/bin/env python3
"""smoke-test.py — End-to-end verification of the IPRS deployment.

Validates: health checks, market data upload, run submission, result retrieval.

Usage:
    python scripts/smoke-test.py [--base-url http://localhost]
    python scripts/smoke-test.py --base-url http://my-alb.us-east-1.elb.amazonaws.com
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# Service definitions: (name, port, health_path, alb_prefix)
SERVICES = [
    ("marketdata",   8001, "/health", "/mkt"),
    ("orchestrator", 8002, "/health", "/orch"),
    ("results",      8003, "/health", "/results"),
    ("portfolio",    8005, "/health", "/portfolio"),
    ("risk",         8006, "/health", "/risk"),
    ("regulatory",   8007, "/health", "/regulatory"),
    ("ingestion",    8008, "/health", "/ingestion"),
]

# Demo market snapshot for testing
DEMO_SNAPSHOT = {
    "snapshot_id": f"MKT-SMOKE-{int(time.time())}",
    "as_of_time": "2026-01-23T00:00:00Z",
    "vendor": "SMOKE-TEST",
    "universe_id": "USD",
    "fx_spots": [
        {"pair": "EURUSD", "spot": 1.09, "ts": "2026-01-23T00:00:00Z"}
    ],
    "curves": [
        {
            "curve_id": "USD-OIS",
            "curve_type": "DISCOUNT",
            "nodes": [
                {"tenor": "1M", "zero_rate": 0.045},
                {"tenor": "6M", "zero_rate": 0.046},
                {"tenor": "1Y", "zero_rate": 0.047},
            ],
        },
        {
            "curve_id": "LOAN-SPREAD",
            "curve_type": "SPREAD",
            "nodes": [
                {"tenor": "1M", "zero_rate": 0.020},
                {"tenor": "6M", "zero_rate": 0.020},
                {"tenor": "1Y", "zero_rate": 0.020},
            ],
        },
        {
            "curve_id": "FI-SPREAD",
            "curve_type": "SPREAD",
            "nodes": [{"tenor": "1Y", "zero_rate": 0.015}],
        },
    ],
    "quality": {"dq_status": "PASS", "issues": []},
}


class SmokeTest:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

        # Determine if we're running against localhost (direct port access)
        # or a remote ALB (path-prefix routing via nginx)
        parsed = urlparse(self.base_url)
        self.is_local = parsed.hostname in ("localhost", "127.0.0.1")

    def _service_url(self, name: str, port: int, path: str, alb_prefix: str) -> str:
        """Build the correct URL for a service endpoint."""
        if self.is_local:
            return f"http://localhost:{port}{path}"
        else:
            return f"{self.base_url}{alb_prefix}{path}"

    def check(self, name: str, ok: bool, detail: str = ""):
        if ok:
            print(f"  PASS: {name}")
            self.passed += 1
        else:
            msg = f"  FAIL: {name}" + (f" — {detail}" if detail else "")
            print(msg)
            self.failed += 1
            self.errors.append(f"{name}: {detail}")

    def _get(self, url: str) -> requests.Response | None:
        try:
            return requests.get(url, timeout=self.timeout)
        except Exception as e:
            return None

    def _post(self, url: str, body: dict) -> requests.Response | None:
        try:
            return requests.post(url, json=body, timeout=self.timeout)
        except Exception as e:
            return None

    def test_health_checks(self):
        """Test /health on all services."""
        print("\n[1/6] Health Checks")
        for name, port, path, alb_prefix in SERVICES:
            url = self._service_url(name, port, path, alb_prefix)
            resp = self._get(url)
            ok = resp is not None and resp.status_code == 200
            detail = "" if ok else f"HTTP {resp.status_code}" if resp else "connection refused"
            self.check(f"{name} ({url})", ok, detail)

    def test_deep_health(self):
        """Test /health/deep (DB connectivity) on core services."""
        print("\n[2/6] Deep Health (DB connectivity)")
        for name, port, _, alb_prefix in SERVICES:
            url = self._service_url(name, port, "/health/deep", alb_prefix)
            resp = self._get(url)
            if resp and resp.status_code == 200:
                body = resp.json()
                ok = body.get("ok", False) and body.get("db") == "connected"
                self.check(f"{name} DB", ok, str(body) if not ok else "")
            else:
                self.check(f"{name} DB", False, "endpoint not available")

    def test_market_data(self) -> str | None:
        """POST demo snapshot, GET it back."""
        print("\n[3/6] Market Data Upload")
        if self.is_local:
            url = "http://localhost:8001/api/v1/marketdata/snapshots"
        else:
            url = f"{self.base_url}/mkt/api/v1/marketdata/snapshots"

        resp = self._post(url, DEMO_SNAPSHOT)
        if resp and resp.status_code in (200, 201):
            result = resp.json()
            sid = result.get("snapshot_id", DEMO_SNAPSHOT["snapshot_id"])
            self.check("POST snapshot", True)

            # Retrieve it back
            get_resp = self._get(f"{url}/{sid}")
            ok = get_resp is not None and get_resp.status_code == 200
            self.check("GET snapshot", ok)
            return sid
        else:
            detail = f"HTTP {resp.status_code}: {resp.text[:200]}" if resp else "connection refused"
            self.check("POST snapshot", False, detail)
            return None

    def test_run_submission(self, snapshot_id: str) -> str | None:
        """POST a run request and poll until completed."""
        print("\n[4/6] Run Submission")
        run_request = {
            "run_type": "SANDBOX",
            "as_of_time": "2026-01-23T00:00:00Z",
            "market_snapshot_id": snapshot_id,
            "model_set_id": "MODELSET-SMOKE-001",
            "portfolio_scope": {"node_ids": ["BOOK-PRIME-LOANS"]},
            "measures": ["PV", "DV01"],
            "scenarios": [{"scenario_set_id": "BASE"}],
            "execution": {"hash_mod": 1},
        }

        if self.is_local:
            url = "http://localhost:8002/api/v1/runs"
        else:
            url = f"{self.base_url}/orch/api/v1/runs"

        resp = self._post(url, run_request)
        if not resp or resp.status_code not in (200, 201):
            detail = f"HTTP {resp.status_code}" if resp else "connection refused"
            self.check("POST run", False, detail)
            return None

        result = resp.json()
        run_id = result.get("run_id")
        self.check("POST run", True)

        # Poll for completion (max 60s)
        print("  Polling for completion...")
        if self.is_local:
            status_base = "http://localhost:8002/api/v1/runs"
        else:
            status_base = f"{self.base_url}/orch/api/v1/runs"

        for i in range(30):
            time.sleep(2)
            status_resp = self._get(f"{status_base}/{run_id}")
            if status_resp and status_resp.status_code == 200:
                status = status_resp.json().get("status", "")
                if status == "COMPLETED":
                    self.check("Run completed", True)
                    return run_id
                elif status in ("FAILED", "CANCELLED"):
                    self.check("Run completed", False, f"status={status}")
                    return run_id
            print(f"    ...{(i+1)*2}s")

        self.check("Run completed", False, "timed out after 60s")
        return run_id

    def test_results(self, run_id: str):
        """GET results summary and cube."""
        print("\n[5/6] Results Retrieval")

        if self.is_local:
            results_base = "http://localhost:8003/api/v1/results"
        else:
            results_base = f"{self.base_url}/results/api/v1/results"

        # Summary
        url = f"{results_base}/{run_id}/summary"
        resp = self._get(url)
        if resp and resp.status_code == 200:
            body = resp.json()
            self.check("GET summary", True)
        else:
            self.check("GET summary", False, f"HTTP {resp.status_code}" if resp else "connection refused")

        # Cube
        url = f"{results_base}/{run_id}/cube"
        resp = self._get(url)
        if resp and resp.status_code == 200:
            body = resp.json()
            rows = body.get("rows", body) if isinstance(body, dict) else body
            count = len(rows) if isinstance(rows, list) else "N/A"
            self.check("GET cube", True, f"{count} rows")
        else:
            self.check("GET cube", False, f"HTTP {resp.status_code}" if resp else "connection refused")

    def test_frontend(self):
        """Check that the frontend is serving."""
        print("\n[6/6] Frontend")
        if self.is_local:
            url = "http://localhost:80/"
        else:
            url = f"{self.base_url}/"

        resp = self._get(url)
        if resp and resp.status_code == 200:
            has_html = "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()
            self.check("Frontend loads", has_html, "" if has_html else "no HTML content")
        else:
            self.check("Frontend loads", False, "not reachable")

    def summary(self) -> int:
        """Print summary and return exit code."""
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")

        if self.errors:
            print(f"\nFailures:")
            for err in self.errors:
                print(f"  - {err}")

        if self.failed == 0:
            print("\nAll smoke tests PASSED")
            return 0
        else:
            print(f"\n{self.failed} test(s) FAILED")
            return 1


def main():
    parser = argparse.ArgumentParser(description="IPRS deployment smoke test")
    parser.add_argument("--base-url", default="http://localhost", help="Base URL (default: http://localhost)")
    parser.add_argument("--skip-run", action="store_true", help="Skip run submission (faster)")
    args = parser.parse_args()

    print("=== IPRS Smoke Test ===")
    print(f"Target: {args.base_url}")

    st = SmokeTest(args.base_url)

    # 1. Health checks
    st.test_health_checks()

    # 2. Deep health
    st.test_deep_health()

    # 3. Market data
    snapshot_id = st.test_market_data()

    # 4-5. Run + results (optional)
    if not args.skip_run and snapshot_id:
        run_id = st.test_run_submission(snapshot_id)
        if run_id:
            st.test_results(run_id)
    elif args.skip_run:
        print("\n[4/6] Skipping run submission (--skip-run)")
        print("\n[5/6] Skipping results retrieval (--skip-run)")

    # 6. Frontend
    st.test_frontend()

    sys.exit(st.summary())


if __name__ == "__main__":
    main()
