import axios from "axios";

export type RunCreateRequest = {
  run_id: string;
  run_type: "SANDBOX" | "INTRADAY" | "EOD_OFFICIAL";
  as_of_time: string;
  market_snapshot_id: string;
  model_set_id?: string;
  portfolio_scope: { node_ids: string[] };
  measures: string[];
  scenarios?: any;
  execution?: { hash_mod?: number };
};

export type RunCreateResponse = {
  run_id: string;
  status?: string;
};

export type ResultsSummary = {
  rows: number;
  pv_sum: number;
};

export type CubeRow = {
  key: string;
  value: number;
};

export type HealthResponse = { ok: boolean } | boolean;

export async function healthMarket() {
  const { data } = await axios.get<HealthResponse>("/mkt/health");
  return data;
}
export async function healthOrch() {
  const { data } = await axios.get<HealthResponse>("/orch/health");
  return data;
}
export async function healthResults() {
  const { data } = await axios.get<HealthResponse>("/results/health");
  return data;
}

export async function postMarketSnapshot(payload: any) {
  const { data } = await axios.post<{ snapshot_id: string }>("/mkt/api/v1/marketdata/snapshots", payload);
  return data;
}

export async function createRun(req: RunCreateRequest) {
  const { data } = await axios.post<RunCreateResponse>("/orch/api/v1/runs", req);
  return data;
}

export async function getSummary(runId: string, scenarioId: string = "BASE") {
  const { data } = await axios.get<ResultsSummary>(`/results/api/v1/results/${runId}/summary`, {
    params: { scenario_id: scenarioId },
  });
  return data;
}

export async function getCube(runId: string, measure: string = "PV", by: string = "product_type", scenarioId: string = "BASE") {
  const { data } = await axios.get<CubeRow[]>(`/results/api/v1/results/${runId}/cube`, {
    params: { measure, by, scenario_id: scenarioId },
  });
  return data;
}
