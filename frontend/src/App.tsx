import React, { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import RunLauncherPage from "./pages/RunLauncherPage";
import RunResultsPage from "./pages/RunResultsPage";
import RunCubePage from "./pages/RunCubePage";
import RegulatoryPage from "./pages/RegulatoryPage";
import AuditTrailPage from "./pages/AuditTrailPage";
import ModelGovernancePage from "./pages/ModelGovernancePage";
import ExportPage from "./pages/ExportPage";
import AlertsPage from "./pages/AlertsPage";

function TopNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="mb-6 md:mb-8">
      {/* Main nav bar */}
      <div className="bg-brutal-black text-white border-3 border-black p-4">
        <div className="flex items-center justify-between">
          {/* Logo and title */}
          <div className="flex items-center gap-3 md:gap-4">
            <div className="bg-brutal-yellow text-black p-2 md:p-3 border-3 border-black shadow-brutal">
              <span className="font-black text-lg md:text-xl">RISK</span>
            </div>
            <div>
              <h1 className="text-lg md:text-xl lg:text-2xl font-black tracking-tight">
                MVP / IPRS
              </h1>
              <p className="text-xs md:text-sm font-mono text-gray-300 hidden sm:block">
                Instrument Pricing & Risk System
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-3">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Launcher
            </NavLink>
            <NavLink
              to="/regulatory"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Regulatory
            </NavLink>
            <NavLink
              to="/audit-trail"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Audit Trail
            </NavLink>
            <NavLink
              to="/model-governance"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Models
            </NavLink>
            <NavLink
              to="/export"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Export
            </NavLink>
            <NavLink
              to="/alerts"
              className={({ isActive }) =>
                `brutal-btn ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Alerts
            </NavLink>
          </nav>

          {/* Mobile menu button */}
          <button
            className="md:hidden bg-brutal-yellow text-black p-2 border-3 border-black"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden mt-4 pt-4 border-t-3 border-gray-700 flex flex-col gap-2">
            <NavLink
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Launcher
            </NavLink>
            <NavLink
              to="/regulatory"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Regulatory
            </NavLink>
            <NavLink
              to="/audit-trail"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Audit Trail
            </NavLink>
            <NavLink
              to="/model-governance"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Models
            </NavLink>
            <NavLink
              to="/export"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Export
            </NavLink>
            <NavLink
              to="/alerts"
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `brutal-btn w-full ${isActive ? 'bg-brutal-pink' : 'bg-brutal-yellow'}`
              }
            >
              Alerts
            </NavLink>
          </nav>
        )}
      </div>

      {/* Service status bar */}
      <div className="bg-brutal-lime border-3 border-t-0 border-black p-2 md:p-3">
        <div className="flex flex-wrap items-center justify-center gap-2 md:gap-4 text-xs md:text-sm font-bold">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-black rounded-full"></span>
            Orchestrator :8002
          </span>
          <span className="hidden sm:inline">|</span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-black rounded-full"></span>
            Results API :8003
          </span>
          <span className="hidden sm:inline">|</span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-black rounded-full"></span>
            Marketdata :8001
          </span>
        </div>
      </div>
    </header>
  );
}

function NotFoundPage() {
  return (
    <div className="brutal-card bg-brutal-red text-white text-center">
      <h2 className="brutal-title mb-4">404</h2>
      <p className="text-lg mb-6">Page not found</p>
      <Link to="/" className="brutal-btn bg-white text-black">
        Go Home
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-brutal-dots bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-4 md:px-6 md:py-6 lg:px-8">
        <TopNav />
        <main>
          <Routes>
            <Route path="/" element={<RunLauncherPage />} />
            <Route path="/runs/:runId" element={<RunResultsPage />} />
            <Route path="/runs/:runId/cube" element={<RunCubePage />} />
            <Route path="/regulatory" element={<RegulatoryPage />} />
            <Route path="/audit-trail" element={<AuditTrailPage />} />
            <Route path="/model-governance" element={<ModelGovernancePage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="mt-8 md:mt-12 pt-6 border-t-3 border-black">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm font-bold">
            <p>Risk MVP - Financial Risk Computation Engine</p>
            <p className="font-mono text-xs md:text-sm text-gray-600">
              Built with FastAPI + React + PostgreSQL
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
