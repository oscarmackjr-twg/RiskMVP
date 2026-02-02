import React, { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getSummary } from "../api";

export default function RunResultsPage() {
  const { runId } = useParams();
  const rid = runId ?? "";

  const q = useQuery({
    queryKey: ["summary", rid],
    queryFn: () => getSummary(rid, "BASE"),
    enabled: Boolean(rid),
    refetchInterval: (data) => {
      if (!data) return 2000;
      return (data.rows ?? 0) >= 1 ? 8000 : 2000;
    },
  });

  const status = useMemo(() => {
    if (q.isLoading) return "Loading…";
    if (q.isError) return "Error";
    if (!q.data) return "No data";
    if ((q.data.rows ?? 0) >= 1) return "Results Ready";
    return "Waiting for worker…";
  }, [q.isLoading, q.isError, q.data]);

  return (
    <div className="card">
      <div className="hstack" style={{ justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>Run Results</div>
          <div className="small">run_id: <span className="code">{rid}</span> • scenario: BASE</div>
        </div>
        <span className="badge">{status}</span>
      </div>

      <div style={{ height: 14 }} />

      {q.isError && (
        <div className="small" style={{ color: "#b91c1c" }}>
          {(q.error as any)?.message ?? "Failed to fetch summary"}
        </div>
      )}

      <div className="kv" style={{ marginTop: 8 }}>
        <div>rows</div>
        <div className="code">{q.data?.rows ?? "—"}</div>
        <div>pv_sum</div>
        <div className="code">{q.data?.pv_sum ?? "—"}</div>
      </div>

      <div style={{ height: 14 }} />
      <div className="hstack">
        <Link className="btn secondary" to="/">Back</Link>
        <Link className="btn" to={`/runs/${rid}/cube`}>View Cube</Link>
        <a className="btn secondary" target="_blank" rel="noreferrer"
          href={`/results/api/v1/results/${rid}/summary?scenario_id=BASE`}
        >
          Open Summary JSON
        </a>
      </div>
    </div>
  );
}
