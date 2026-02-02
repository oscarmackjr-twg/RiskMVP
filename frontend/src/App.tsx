import React from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import RunLauncherPage from "./pages/RunLauncherPage";
import RunResultsPage from "./pages/RunResultsPage";
import RunCubePage from "./pages/RunCubePage";

function TopNav() {
  return (
    <div className="header">
      <div>
        <div style={{ fontSize: 18, fontWeight: 800 }}>Risk MVP</div>
        <div className="small">Run Orchestrator (8002) • Results API (8003) • Marketdata (8001)</div>
      </div>
      <div className="nav">
        <NavLink to="/" className="badge">Launcher</NavLink>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="container">
      <TopNav />
      <Routes>
        <Route path="/" element={<RunLauncherPage />} />
        <Route path="/runs/:runId" element={<RunResultsPage />} />
        <Route path="/runs/:runId/cube" element={<RunCubePage />} />
        <Route path="*" element={<div className="card">Not found. <Link to="/">Go home</Link></div>} />
      </Routes>
    </div>
  );
}
