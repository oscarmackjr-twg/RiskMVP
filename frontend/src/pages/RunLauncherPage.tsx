import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { addRunHistory, loadRunHistory } from "../runHistory";
import { createRun, healthMarket, healthOrch, healthResults, type RunCreateRequest } from "../api";

export default function RunLauncherPage() {
  const nav = useNavigate();

  const [marketSnapshotId, setMarketSnapshotId] = useState("MKT-DEMO-20260123");
  const [asOfTime, setAsOfTime] = useState("2026-01-23T00:00:00Z");
  const [portfolioNodeId, setPortfolioNodeId] = useState("BOOK-PRIME-LOANS");
  const [measures, setMeasures] = useState<string[]>(["PV"]);
  const [scenarioId] = useState("BASE");

  const history = useMemo(() => loadRunHistory(), []);

  const qMkt = useQuery({ queryKey: ["health","mkt"], queryFn: healthMarket, refetchInterval: 5000 });
  const qOrch = useQuery({ queryKey: ["health","orch"], queryFn: healthOrch, refetchInterval: 5000 });
  const qRes = useQuery({ queryKey: ["health","results"], queryFn: healthResults, refetchInterval: 5000 });

  const mCreate = useMutation({
    mutationFn: async () => {
      const runId = "RUN_" + new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
      const req: RunCreateRequest = {
        run_id: runId,
        run_type: "SANDBOX",
        as_of_time: asOfTime,
        market_snapshot_id: marketSnapshotId,
        portfolio_scope: { node_ids: [portfolioNodeId] },
        measures,
        scenarios: [{ scenario_set_id: scenarioId }],
        execution: { hash_mod: 8 },
      };
      return await createRun(req);
    },
    onSuccess: (resp) => {
      addRunHistory({
        runId: resp.run_id,
        asOfTime,
        portfolioNodeId,
        createdAt: new Date().toISOString(),
      });
      nav(`/runs/${resp.run_id}`);
    },
  });

  function toggleMeasure(m: string) {
    setMeasures((prev) => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]);
  }

  return (
    <div className="row">
      <div className="col">
        <div className="card">
          <div className="hstack" style={{ justifyContent: "space-between" }}>
            <div style={{ fontSize: 16, fontWeight: 800 }}>Run Launcher</div>
            <span className="badge">scenario: BASE</span>
          </div>

          <div style={{ height: 10 }} />

          <div className="kv">
            <div>Market Snapshot</div>
            <div><input className="input code" value={marketSnapshotId} onChange={(e) => setMarketSnapshotId(e.target.value)} /></div>

            <div>As-of Time</div>
            <div><input className="input code" value={asOfTime} onChange={(e) => setAsOfTime(e.target.value)} /></div>

            <div>Portfolio Node</div>
            <div><input className="input code" value={portfolioNodeId} onChange={(e) => setPortfolioNodeId(e.target.value)} /></div>

            <div>Measures</div>
            <div className="hstack">
              <label className="small"><input type="checkbox" checked={measures.includes("PV")} onChange={() => toggleMeasure("PV")} /> PV</label>
              <label className="small"><input type="checkbox" checked={measures.includes("DV01")} onChange={() => toggleMeasure("DV01")} /> DV01</label>
            </div>
          </div>

          <div style={{ height: 14 }} />

          <div className="hstack">
            <button className="btn" onClick={() => mCreate.mutate()} disabled={mCreate.isPending || measures.length === 0}>
              {mCreate.isPending ? "Creating..." : "Create Run"}
            </button>
            {mCreate.isError && (
              <span className="small" style={{ color: "#b91c1c" }}>
                Error: {(mCreate.error as any)?.message ?? "failed to create run"}
              </span>
            )}
          </div>

          <div style={{ height: 14 }} />

          <div className="card" style={{ background: "#f8fafc" }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Service Health</div>
            <div className="small">Marketdata: {String((qMkt.data as any)?.ok ?? qMkt.data ?? "…")}</div>
            <div className="small">Orchestrator: {String((qOrch.data as any)?.ok ?? qOrch.data ?? "…")}</div>
            <div className="small">Results: {String((qRes.data as any)?.ok ?? qRes.data ?? "…")}</div>
          </div>

          <div style={{ height: 10 }} />
          <div className="small">
            Tip: Start your services with <span className="code">scripts\demo_runner.ps1 -NoCleanup</span>.
          </div>
        </div>
      </div>

      <div className="col">
        <div className="card">
          <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 10 }}>Recent Runs</div>
          {history.length === 0 ? (
            <div className="small">No run history yet (stored in localStorage).</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>As-of</th>
                  <th>Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.runId}>
                    <td><a href={`/runs/${h.runId}`}>{h.runId}</a></td>
                    <td className="code">{h.asOfTime}</td>
                    <td className="code">{h.portfolioNodeId}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
