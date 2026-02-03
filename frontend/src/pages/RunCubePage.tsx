import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCube } from "../api";

const MEASURES = ["PV", "DV01", "FX_DELTA", "ACCRUED_INTEREST"];
const GROUP_BY_OPTIONS = ["product_type", "currency", "book_id", "counterparty"];

function CubeValueBar({ value, maxValue }: { value: number; maxValue: number }) {
  const percentage = maxValue > 0 ? Math.abs(value / maxValue) * 100 : 0;
  const isNegative = value < 0;

  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-6 bg-gray-200 border-2 border-black relative overflow-hidden">
        <div
          className={`h-full ${isNegative ? "bg-brutal-red" : "bg-brutal-green"}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className={`font-mono text-sm font-bold min-w-[100px] text-right ${isNegative ? "text-brutal-red" : ""}`}>
        {new Intl.NumberFormat("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(value)}
      </span>
    </div>
  );
}

export default function RunCubePage() {
  const { runId } = useParams();
  const rid = runId ?? "";

  const [measure, setMeasure] = useState("PV");
  const [groupBy, setGroupBy] = useState("product_type");

  const q = useQuery({
    queryKey: ["cube", rid, measure, groupBy],
    queryFn: () => getCube(rid, measure, groupBy, "BASE"),
    enabled: Boolean(rid),
  });

  const maxValue = Math.max(...(q.data?.map((r) => Math.abs(r.value)) ?? [0]));
  const total = q.data?.reduce((sum, r) => sum + r.value, 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="brutal-card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="brutal-title mb-2">Cube Analysis</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-bold">Run ID:</span>
              <code className="bg-black text-white px-2 py-1 font-mono text-xs break-all">
                {rid}
              </code>
              <span className="brutal-badge-yellow">Scenario: BASE</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to={`/runs/${rid}`} className="brutal-btn-secondary">
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
              Back
            </Link>
            <a
              className="brutal-btn-blue"
              target="_blank"
              rel="noreferrer"
              href={`/results/api/v1/results/${rid}/cube?measure=${measure}&by=${groupBy}&scenario_id=BASE`}
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
      </div>

      {/* Filters Card */}
      <div className="brutal-card bg-brutal-lime/20">
        <h2 className="font-bold text-sm uppercase mb-4">Cube Parameters</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Measure Selection */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">Measure</label>
            <select
              className="brutal-select"
              value={measure}
              onChange={(e) => setMeasure(e.target.value)}
            >
              {MEASURES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Group By Selection */}
          <div>
            <label className="block font-bold text-sm uppercase mb-2">Group By</label>
            <select
              className="brutal-select"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
            >
              {GROUP_BY_OPTIONS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {q.data && q.data.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 border-3 border-black bg-brutal-blue">
            <div className="text-xs font-bold uppercase">Measure</div>
            <div className="text-xl md:text-2xl font-black">{measure}</div>
          </div>
          <div className="p-4 border-3 border-black bg-brutal-pink">
            <div className="text-xs font-bold uppercase">Group By</div>
            <div className="text-xl md:text-2xl font-black">{groupBy}</div>
          </div>
          <div className="p-4 border-3 border-black bg-brutal-green">
            <div className="text-xs font-bold uppercase">Categories</div>
            <div className="text-xl md:text-2xl font-black font-mono">{q.data.length}</div>
          </div>
          <div className="p-4 border-3 border-black bg-brutal-yellow">
            <div className="text-xs font-bold uppercase">Total</div>
            <div className="text-xl md:text-2xl font-black font-mono">
              {new Intl.NumberFormat("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
                notation: "compact",
              }).format(total)}
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {q.isLoading && (
        <div className="brutal-card bg-brutal-orange/20 text-center py-8">
          <div className="brutal-spinner mx-auto mb-4"></div>
          <p className="font-bold">Loading cube data...</p>
        </div>
      )}

      {/* Error State */}
      {q.isError && (
        <div className="brutal-alert-error">
          <span className="font-black">Error:</span>{" "}
          {(q.error as any)?.message ?? "Failed to load cube"}
        </div>
      )}

      {/* Data Table */}
      {!q.isLoading && !q.isError && q.data && (
        <div className="brutal-card">
          <h2 className="font-bold text-sm uppercase mb-4">
            {measure} by {groupBy}
          </h2>

          {q.data.length === 0 ? (
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
                    d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                  />
                </svg>
              </div>
              <p className="font-bold text-lg">No Data Available</p>
              <p className="text-sm text-gray-600">
                The cube query returned no results for this configuration.
              </p>
            </div>
          ) : (
            <>
              {/* Desktop Table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="brutal-table">
                  <thead>
                    <tr>
                      <th className="w-1/4">{groupBy}</th>
                      <th>{measure} Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {q.data.map((r) => (
                      <tr key={r.key}>
                        <td className="font-mono font-bold">{r.key}</td>
                        <td>
                          <CubeValueBar value={r.value} maxValue={maxValue} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Cards */}
              <div className="md:hidden space-y-3">
                {q.data.map((r) => (
                  <div key={r.key} className="p-3 border-3 border-black bg-white">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono font-bold text-sm">{r.key}</span>
                      <span
                        className={`font-mono font-bold text-sm ${
                          r.value < 0 ? "text-brutal-red" : ""
                        }`}
                      >
                        {new Intl.NumberFormat("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        }).format(r.value)}
                      </span>
                    </div>
                    <div className="h-4 bg-gray-200 border-2 border-black">
                      <div
                        className={`h-full ${r.value < 0 ? "bg-brutal-red" : "bg-brutal-green"}`}
                        style={{
                          width: `${Math.min((Math.abs(r.value) / maxValue) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
