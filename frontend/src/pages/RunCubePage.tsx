import React from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCube } from "../api";

export default function RunCubePage() {
  const { runId } = useParams();
  const rid = runId ?? "";

  const q = useQuery({
    queryKey: ["cube", rid],
    queryFn: () => getCube(rid, "PV", "product_type", "BASE"),
    enabled: Boolean(rid),
  });

  return (
    <div className="card">
      <div className="hstack" style={{ justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>Cube</div>
          <div className="small">PV by product_type • run_id: <span className="code">{rid}</span> • scenario: BASE</div>
        </div>
        <div className="hstack">
          <Link className="btn secondary" to={`/runs/${rid}`}>Back</Link>
          <a className="btn secondary" target="_blank" rel="noreferrer"
            href={`/results/api/v1/results/${rid}/cube?measure=PV&by=product_type&scenario_id=BASE`}
          >
            Open Cube JSON
          </a>
        </div>
      </div>

      <div style={{ height: 14 }} />

      {q.isLoading && <div className="small">Loading cube…</div>}
      {q.isError && <div className="small" style={{ color: "#b91c1c" }}>{(q.error as any)?.message ?? "Failed to load cube"}</div>}

      {!q.isLoading && !q.isError && (
        <table className="table">
          <thead>
            <tr>
              <th>key</th>
              <th>value</th>
            </tr>
          </thead>
          <tbody>
            {(q.data ?? []).map((r) => (
              <tr key={r.key}>
                <td className="code">{r.key}</td>
                <td className="code">{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
