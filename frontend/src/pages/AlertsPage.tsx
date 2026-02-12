import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

interface AlertConfig {
  alert_id: string;
  alert_type: string;
  portfolio_node_id?: string;
  threshold_value: number;
  threshold_operator: string;
  metric_name: string;
  notification_channels: string[];
  enabled: boolean;
}

interface AlertLog {
  log_id: string;
  alert_id: string;
  triggered_at: string;
  metric_value: number;
  threshold_value: number;
  portfolio_node_id?: string;
  position_id?: string;
  notification_sent: boolean;
  resolved: boolean;
}

interface EvaluateResult {
  portfolio_node_id: string;
  evaluated_at: string;
  triggered_count: number;
  triggered_alerts: Array<{
    alert_id: string;
    alert_type: string;
    metric_name: string;
    metric_value: number;
    threshold_value: number;
  }>;
}

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [portfolioId, setPortfolioId] = useState("test-portfolio-1");
  const [showForm, setShowForm] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluateResult | null>(null);

  const [form, setForm] = useState({
    alert_type: "CONCENTRATION_LIMIT",
    threshold_value: 0.1,
    threshold_operator: "GT",
    metric_name: "CECL_ALLOWANCE",
    notification_channels: ["email"],
    enabled: true,
  });

  // Fetch configs
  const { data: configs } = useQuery<AlertConfig[]>({
    queryKey: ["alerts", "config", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (portfolioId) params.append("portfolio_node_id", portfolioId);
      const res = await api.get(`/regulatory/alerts/config?${params}`);
      return res.data;
    },
  });

  // Fetch logs
  const { data: logs } = useQuery<AlertLog[]>({
    queryKey: ["alerts", "log", portfolioId],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "50" });
      if (portfolioId) params.append("portfolio_node_id", portfolioId);
      const res = await api.get(`/regulatory/alerts/log?${params}`);
      return res.data;
    },
  });

  // Create alert
  const createMut = useMutation({
    mutationFn: async () => {
      const res = await api.post("/regulatory/alerts/config", {
        ...form,
        portfolio_node_id: portfolioId,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts", "config"] });
      setShowForm(false);
    },
  });

  // Evaluate
  const evalMut = useMutation({
    mutationFn: async () => {
      const res = await api.post("/regulatory/alerts/evaluate", {
        portfolio_node_id: portfolioId,
      });
      return res.data as EvaluateResult;
    },
    onSuccess: (data) => {
      setEvalResult(data);
      queryClient.invalidateQueries({ queryKey: ["alerts", "log"] });
    },
  });

  // Resolve
  const resolveMut = useMutation({
    mutationFn: async (logId: string) => {
      const res = await api.post(`/regulatory/alerts/log/${logId}/resolve`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts", "log"] });
    },
  });

  const activeCount = logs?.filter((l) => !l.resolved).length ?? 0;

  return (
    <div className="space-y-6">
      <div className="brutal-card bg-white">
        <div className="flex items-center justify-between mb-4">
          <h1 className="brutal-title text-2xl">Alerts & Monitoring</h1>
          <div className="flex gap-3">
            <button
              onClick={() => setShowForm(!showForm)}
              className="brutal-btn bg-brutal-lime"
            >
              {showForm ? "Cancel" : "+ New Alert"}
            </button>
            <button
              onClick={() => evalMut.mutate()}
              disabled={evalMut.isPending}
              className="brutal-btn bg-brutal-yellow"
            >
              {evalMut.isPending ? "Evaluating..." : "Evaluate Now"}
            </button>
          </div>
        </div>

        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-black mb-1">Portfolio ID</label>
            <input
              type="text"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="w-full border-3 border-black p-2 font-mono"
            />
          </div>
          <div className="text-sm font-bold">
            {activeCount > 0 ? (
              <span className="bg-brutal-red text-white px-3 py-2 border-3 border-black">
                {activeCount} Active
              </span>
            ) : (
              <span className="bg-brutal-lime px-3 py-2 border-3 border-black">
                All Clear
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Eval result banner */}
      {evalResult && (
        <div
          className={`brutal-card ${
            evalResult.triggered_count > 0 ? "bg-brutal-red text-white" : "bg-brutal-lime"
          }`}
        >
          <p className="font-black">
            Evaluation: {evalResult.triggered_count} alert(s) triggered
          </p>
        </div>
      )}

      {/* New alert form */}
      {showForm && (
        <div className="brutal-card bg-brutal-yellow">
          <h2 className="font-black text-lg mb-4">Create Alert</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-black mb-1">Type</label>
              <select
                value={form.alert_type}
                onChange={(e) => setForm({ ...form, alert_type: e.target.value })}
                className="w-full border-3 border-black p-2"
              >
                <option value="DURATION_THRESHOLD">Duration Threshold</option>
                <option value="CONCENTRATION_LIMIT">Concentration Limit</option>
                <option value="CREDIT_DETERIORATION">Credit Deterioration</option>
                <option value="LIQUIDITY_RATIO">Liquidity Ratio</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-black mb-1">Metric</label>
              <select
                value={form.metric_name}
                onChange={(e) => setForm({ ...form, metric_name: e.target.value })}
                className="w-full border-3 border-black p-2"
              >
                <option value="CECL_ALLOWANCE">CECL Allowance</option>
                <option value="BASEL_RWA">Basel RWA</option>
                <option value="CAPITAL_RATIO">Capital Ratio</option>
                <option value="GAAP_VALUATION">GAAP Valuation</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-black mb-1">Operator</label>
              <select
                value={form.threshold_operator}
                onChange={(e) => setForm({ ...form, threshold_operator: e.target.value })}
                className="w-full border-3 border-black p-2"
              >
                <option value="GT">Greater Than (&gt;)</option>
                <option value="GTE">Greater or Equal (&gt;=)</option>
                <option value="LT">Less Than (&lt;)</option>
                <option value="LTE">Less or Equal (&lt;=)</option>
                <option value="EQ">Equal (=)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-black mb-1">Threshold</label>
              <input
                type="number"
                value={form.threshold_value}
                onChange={(e) =>
                  setForm({ ...form, threshold_value: parseFloat(e.target.value) })
                }
                step="0.01"
                className="w-full border-3 border-black p-2 font-mono"
              />
            </div>
          </div>
          <button
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending}
            className="brutal-btn bg-black text-white mt-4"
          >
            {createMut.isPending ? "Creating..." : "Create Alert"}
          </button>
        </div>
      )}

      {/* Alert configs table */}
      {configs && configs.length > 0 && (
        <div className="brutal-card bg-white">
          <h2 className="font-black text-lg mb-3">Alert Configurations</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-3 border-black">
              <thead>
                <tr className="bg-brutal-black text-white">
                  <th className="p-2 text-left border-r border-gray-700">Type</th>
                  <th className="p-2 text-left border-r border-gray-700">Metric</th>
                  <th className="p-2 text-left border-r border-gray-700">Condition</th>
                  <th className="p-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((c) => (
                  <tr key={c.alert_id} className="border-t-2 border-black hover:bg-gray-50">
                    <td className="p-2 border-r border-gray-300 font-mono text-sm">
                      {c.alert_type}
                    </td>
                    <td className="p-2 border-r border-gray-300">{c.metric_name}</td>
                    <td className="p-2 border-r border-gray-300 font-mono">
                      {c.threshold_operator} {c.threshold_value}
                    </td>
                    <td className="p-2 text-center">
                      <span
                        className={`px-2 py-1 text-xs font-black border-2 border-black ${
                          c.enabled ? "bg-brutal-lime" : "bg-gray-200"
                        }`}
                      >
                        {c.enabled ? "ON" : "OFF"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Alert log table */}
      <div className="brutal-card bg-white">
        <h2 className="font-black text-lg mb-3">Trigger History</h2>
        {logs && logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-3 border-black">
              <thead>
                <tr className="bg-brutal-black text-white">
                  <th className="p-2 text-left border-r border-gray-700">Triggered</th>
                  <th className="p-2 text-left border-r border-gray-700">Alert</th>
                  <th className="p-2 text-right border-r border-gray-700">Value</th>
                  <th className="p-2 text-right border-r border-gray-700">Threshold</th>
                  <th className="p-2 text-center border-r border-gray-700">Status</th>
                  <th className="p-2 text-center">Action</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.log_id} className="border-t-2 border-black hover:bg-gray-50">
                    <td className="p-2 border-r border-gray-300 text-sm">
                      {new Date(log.triggered_at).toLocaleString()}
                    </td>
                    <td className="p-2 border-r border-gray-300 font-mono text-xs">
                      {log.alert_id.substring(0, 16)}...
                    </td>
                    <td className="p-2 border-r border-gray-300 text-right font-mono">
                      {log.metric_value.toFixed(4)}
                    </td>
                    <td className="p-2 border-r border-gray-300 text-right font-mono">
                      {log.threshold_value.toFixed(4)}
                    </td>
                    <td className="p-2 border-r border-gray-300 text-center">
                      <span
                        className={`px-2 py-1 text-xs font-black border-2 border-black ${
                          log.resolved ? "bg-gray-200" : "bg-brutal-red text-white"
                        }`}
                      >
                        {log.resolved ? "Resolved" : "ACTIVE"}
                      </span>
                    </td>
                    <td className="p-2 text-center">
                      {!log.resolved && (
                        <button
                          onClick={() => resolveMut.mutate(log.log_id)}
                          className="text-sm font-bold text-blue-700 hover:underline"
                        >
                          Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 font-mono text-sm">No alert triggers recorded.</p>
        )}
      </div>
    </div>
  );
}
