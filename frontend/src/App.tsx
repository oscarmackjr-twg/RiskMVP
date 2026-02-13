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

const navItems = [
  { to: "/", label: "Launcher" },
  { to: "/regulatory", label: "Regulatory" },
  { to: "/audit-trail", label: "Audit Trail" },
  { to: "/model-governance", label: "Models" },
  { to: "/export", label: "Export" },
  { to: "/alerts", label: "Alerts" },
];

function TopNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="mb-6 md:mb-8">
      {/* Main nav bar */}
      <div className="bg-twg-navy rounded-t-lg px-4 py-3 md:px-6 md:py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <img
              src="/twg-logo-white.svg"
              alt="TWG Global"
              className="h-7 md:h-8"
            />
            <div className="hidden sm:block w-px h-8 bg-white/20" />
            <div className="hidden sm:block">
              <p className="text-white/90 text-sm font-medium tracking-wide">
                IPRS
              </p>
              <p className="text-white/50 text-xs">
                Portfolio Risk & Analytics
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `twg-nav-link ${isActive ? 'twg-nav-link-active' : ''}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Mobile menu button */}
          <button
            className="md:hidden text-white/80 hover:text-white p-1.5 rounded-md hover:bg-white/10"
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
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden mt-3 pt-3 border-t border-white/10 flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `twg-nav-link block ${isActive ? 'twg-nav-link-active' : ''}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </div>

      {/* Service status bar */}
      <div className="bg-white border border-t-0 border-gray-200 rounded-b-lg px-4 py-2">
        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-6 text-xs text-twg-muted">
          <span className="twg-status twg-status-ok">
            <span className="twg-status-dot"></span>
            Orchestrator
          </span>
          <span className="twg-status twg-status-ok">
            <span className="twg-status-dot"></span>
            Results API
          </span>
          <span className="twg-status twg-status-ok">
            <span className="twg-status-dot"></span>
            Marketdata
          </span>
        </div>
      </div>
    </header>
  );
}

function NotFoundPage() {
  return (
    <div className="twg-card text-center py-12">
      <h2 className="text-4xl font-semibold text-black mb-4">404</h2>
      <p className="text-twg-muted mb-6">Page not found</p>
      <Link to="/" className="twg-btn">
        Go Home
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-twg-tech-white">
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
        <footer className="mt-8 md:mt-12 pt-6 border-t border-gray-200">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-twg-muted">
            <p>TWG Global - Institutional Portfolio Risk & Analytics</p>
            <p className="text-xs">
              IPRS v1.0
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
