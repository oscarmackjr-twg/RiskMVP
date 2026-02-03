import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { addRunHistory, loadRunHistory } from "../runHistory";
import { createRun, healthMarket, healthOrch, healthResults, type RunCreateRequest } from "../api";

function HealthIndicator({ label, data, isLoading }: { label: string; data: any; isLoading: boolean }) {
  const isOk = data?.ok === true || data === true;
  const status = isLoading ? "checking" : isOk ? "ok" : "error";

  return (
    <div className="flex items-center justify-between p-3 border-3 border-black bg-white">
      <span className="font-bold text-sm uppercase">{label}</span>
      <span
        className={`px-3 py-1 border-3 border-black font-bold text-xs uppercase ${
          status === "ok"
            ? "bg-brutal-green"
            : status === "checking"
            ? "bg-brutal-orange animate-pulse"
            : "bg-brutal-red text-white"
        }`}
      >
        {status === "ok" ? "Online" : status === "checking" ? "..." : "Offline"}
      </span>
    </div>
  );
}

export default function RunLauncherPage() {
  const nav = useNavigate();

  const [marketSnapshotId, setMarketSnapshotId] = useState("MKT-DEMO-20260123");
  const [asOfTime, setAsOfTime] = useState("2026-01-23T00:00:00Z");
  const [portfolioNodeId, setPortfolioNodeId] = useState("BOOK-PRIME-LOANS");
  const [measures, setMeasures] = useState<string[]>(["PV"]);
  const [scenarioId] = useState("BASE");

  const history = useMemo(() => loadRunHistory(), []);

  const qMkt = useQuery({ queryKey: ["health", "mkt"], queryFn: healthMarket, refetchInterval: 5000 });
  const qOrch = useQuery({ queryKey: ["health", "orch"], queryFn: healthOrch, refetchInterval: 5000 });
  const qRes = useQuery({ queryKey: ["health", "results"], queryFn: healthResults, refetchInterval: 5000 });

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
    setMeasures((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Run Configuration Card */}
      <div className="brutal-card">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <h2 className="brutal-title">Run Launcher</h2>
          <span className="brutal-badge-blue">Scenario: {scenarioId}</span>
        </div>

        {/* Form Fields */}
        <div className="space-y-4">
          {/* Market Snapshot */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">Market Snapshot ID</label>
            <input
              type="text"
              className="brutal-input"
              value={marketSnapshotId}
              onChange={(e) => setMarketSnapshotId(e.target.value)}
              placeholder="Enter market snapshot ID"
            />
          </div>

          {/* As-of Time */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">As-of Time</label>
            <input
              type="text"
              className="brutal-input"
              value={asOfTime}
              onChange={(e) => setAsOfTime(e.target.value)}
              placeholder="YYYY-MM-DDTHH:MM:SSZ"
            />
          </div>

          {/* Portfolio Node */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">Portfolio Node</label>
            <input
              type="text"
              className="brutal-input"
              value={portfolioNodeId}
              onChange={(e) => setPortfolioNodeId(e.target.value)}
              placeholder="Enter portfolio node ID"
            />
          </div>

          {/* Measures */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">Measures</label>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="brutal-checkbox"
                  checked={measures.includes("PV")}
                  onChange={() => toggleMeasure("PV")}
                />
                <span className="font-bold">PV</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="brutal-checkbox"
                  checked={measures.includes("DV01")}
                  onChange={() => toggleMeasure("DV01")}
                />
                <span className="font-bold">DV01</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="brutal-checkbox"
                  checked={measures.includes("FX_DELTA")}
                  onChange={() => toggleMeasure("FX_DELTA")}
                />
                <span className="font-bold">FX_DELTA</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="brutal-checkbox"
                  checked={measures.includes("ACCRUED_INTEREST")}
                  onChange={() => toggleMeasure("ACCRUED_INTEREST")}
                />
                <span className="font-bold">ACCRUED</span>
              </label>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="mt-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <button
            className="brutal-btn-success w-full sm:w-auto"
            onClick={() => mCreate.mutate()}
            disabled={mCreate.isPending || measures.length === 0}
          >
            {mCreate.isPending ? (
              <>
                <span className="brutal-spinner mr-2"></span>
                Creating...
              </>
            ) : (
              "Create Run"
            )}
          </button>

          {mCreate.isError && (
            <div className="brutal-alert-error text-sm">
              Error: {(mCreate.error as any)?.message ?? "Failed to create run"}
            </div>
          )}
        </div>

        {/* Service Health */}
        <div className="mt-6 pt-6 border-t-3 border-black">
          <h3 className="font-bold text-sm uppercase mb-3">Service Health</h3>
          <div className="grid gap-2">
            <HealthIndicator label="Marketdata" data={qMkt.data} isLoading={qMkt.isLoading} />
            <HealthIndicator label="Orchestrator" data={qOrch.data} isLoading={qOrch.isLoading} />
            <HealthIndicator label="Results API" data={qRes.data} isLoading={qRes.isLoading} />
          </div>
        </div>

        {/* Tip */}
        <div className="mt-4 p-3 bg-brutal-yellow/30 border-3 border-black">
          <p className="text-sm">
            <span className="font-bold">Tip:</span> Start your services with{" "}
            <code className="bg-black text-white px-2 py-0.5 font-mono text-xs">
              scripts\demo_runner.ps1 -NoCleanup
            </code>
          </p>
        </div>
      </div>

      {/* Recent Runs Card */}
      <div className="brutal-card bg-brutal-pink/10">
        <h2 className="brutal-title mb-6">Recent Runs</h2>

        {history.length === 0 ? (
          <div className="text-center py-12">
            <div className="bg-brutal-purple text-white p-4 border-3 border-black inline-block mb-4">
              <svg
                className="w-12 h-12 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <p className="font-bold text-lg mb-2">No Run History Yet</p>
            <p className="text-sm text-gray-600">
              Create your first run to see it here.
              <br />
              History is stored in localStorage.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="brutal-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th className="hidden sm:table-cell">As-of</th>
                  <th className="hidden md:table-cell">Portfolio</th>
                  <th className="sm:hidden">Details</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.runId}>
                    <td>
                      <a href={`/runs/${h.runId}`} className="brutal-link break-all">
                        {h.runId}
                      </a>
                    </td>
                    <td className="hidden sm:table-cell font-mono text-xs md:text-sm">
                      {h.asOfTime}
                    </td>
                    <td className="hidden md:table-cell font-mono text-xs md:text-sm">
                      {h.portfolioNodeId}
                    </td>
                    <td className="sm:hidden">
                      <div className="text-xs font-mono">
                        <div>{h.asOfTime}</div>
                        <div className="text-gray-500">{h.portfolioNodeId}</div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
