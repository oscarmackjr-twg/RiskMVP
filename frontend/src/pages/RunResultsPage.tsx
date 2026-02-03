import React, { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getSummary } from "../api";

function StatusBadge({ status }: { status: string }) {
  const colorClass = {
    "Loading...": "bg-brutal-orange animate-pulse",
    Error: "bg-brutal-red text-white",
    "No data": "bg-gray-400",
    "Results Ready": "bg-brutal-green",
    "Waiting for worker...": "bg-brutal-blue animate-pulse",
  }[status] || "bg-gray-400";

  return (
    <span className={`brutal-badge ${colorClass}`}>
      {status}
    </span>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className={`p-4 md:p-6 border-3 border-black ${color}`}>
      <div className="text-xs md:text-sm font-bold uppercase tracking-wide mb-1">{label}</div>
      <div className="text-2xl md:text-3xl lg:text-4xl font-black font-mono">{value}</div>
    </div>
  );
}

export default function RunResultsPage() {
  const { runId } = useParams();
  const rid = runId ?? "";

  const q = useQuery({
    queryKey: ["summary", rid],
    queryFn: () => getSummary(rid, "BASE"),
    enabled: Boolean(rid),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      return (data.rows ?? 0) >= 1 ? 8000 : 2000;
    },
  });

  const status = useMemo(() => {
    if (q.isLoading) return "Loading...";
    if (q.isError) return "Error";
    if (!q.data) return "No data";
    if ((q.data.rows ?? 0) >= 1) return "Results Ready";
    return "Waiting for worker...";
  }, [q.isLoading, q.isError, q.data]);

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return "--";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="brutal-card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="brutal-title mb-2">Run Results</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-bold">Run ID:</span>
              <code className="bg-black text-white px-2 py-1 font-mono text-xs break-all">
                {rid}
              </code>
              <span className="brutal-badge-yellow">Scenario: BASE</span>
            </div>
          </div>
          <StatusBadge status={status} />
        </div>
      </div>

      {/* Error Alert */}
      {q.isError && (
        <div className="brutal-alert-error">
          <span className="font-black">Error:</span>{" "}
          {(q.error as any)?.message ?? "Failed to fetch summary"}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-6">
        <MetricCard
          label="Total Rows"
          value={q.data?.rows ?? "--"}
          color="bg-brutal-blue"
        />
        <MetricCard
          label="PV Sum"
          value={formatNumber(q.data?.pv_sum)}
          color="bg-brutal-green"
        />
      </div>

      {/* Actions Card */}
      <div className="brutal-card bg-brutal-pink/10">
        <h2 className="font-bold text-sm uppercase mb-4">Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/" className="brutal-btn-secondary">
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back to Launcher
          </Link>
          <Link to={`/runs/${rid}/cube`} className="brutal-btn">
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
            View Cube
          </Link>
          <a
            className="brutal-btn-blue"
            target="_blank"
            rel="noreferrer"
            href={`/results/api/v1/results/${rid}/summary?scenario_id=BASE`}
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
            Open JSON
          </a>
        </div>
      </div>

      {/* Run Details Card */}
      <div className="brutal-card">
        <h2 className="font-bold text-sm uppercase mb-4">Run Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 bg-gray-100 border-3 border-black">
            <div className="text-xs font-bold uppercase text-gray-500 mb-1">Run ID</div>
            <div className="font-mono text-sm break-all">{rid}</div>
          </div>
          <div className="p-3 bg-gray-100 border-3 border-black">
            <div className="text-xs font-bold uppercase text-gray-500 mb-1">Scenario</div>
            <div className="font-mono text-sm">BASE</div>
          </div>
          <div className="p-3 bg-gray-100 border-3 border-black">
            <div className="text-xs font-bold uppercase text-gray-500 mb-1">Status</div>
            <div className="font-mono text-sm">{status}</div>
          </div>
          <div className="p-3 bg-gray-100 border-3 border-black">
            <div className="text-xs font-bold uppercase text-gray-500 mb-1">Last Updated</div>
            <div className="font-mono text-sm">
              {q.dataUpdatedAt ? new Date(q.dataUpdatedAt).toLocaleTimeString() : "--"}
            </div>
          </div>
        </div>
      </div>

      {/* Loading indicator */}
      {q.isLoading && (
        <div className="brutal-card bg-brutal-orange/20 text-center py-8">
          <div className="brutal-spinner mx-auto mb-4 border-brutal-orange"></div>
          <p className="font-bold">Loading results...</p>
        </div>
      )}
    </div>
  );
}
