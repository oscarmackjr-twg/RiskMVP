export type RunHistoryItem = {
  runId: string;
  asOfTime: string;
  portfolioNodeId: string;
  createdAt: string;
};

const KEY = "riskmvp.runHistory.v1";

export function loadRunHistory(): RunHistoryItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr;
  } catch {
    return [];
  }
}

export function addRunHistory(item: RunHistoryItem) {
  const existing = loadRunHistory();
  const next = [item, ...existing.filter(x => x.runId !== item.runId)].slice(0, 20);
  localStorage.setItem(KEY, JSON.stringify(next));
}
