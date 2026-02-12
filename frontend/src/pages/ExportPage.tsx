import React, { useState } from 'react';
import axios from 'axios';

export default function ExportPage() {
  const [portfolioId, setPortfolioId] = useState('test-portfolio-1');
  const [format, setFormat] = useState<'csv' | 'xlsx'>('xlsx');
  const [includeAuditTrail, setIncludeAuditTrail] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setExportStatus(null);
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      params.append('include_audit_trail', includeAuditTrail.toString());

      const response = await axios.get(
        `/api/v1/regulatory/reports/regulatory/${portfolioId}/export?${params.toString()}`,
        {
          responseType: 'blob',
        }
      );

      // Trigger download
      const url = window.URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `regulatory-${portfolioId}-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setExportStatus('success');
    } catch (error: any) {
      console.error('Export failed:', error);
      setExportStatus('error');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="brutal-card">
        <h1 className="brutal-title mb-2">Export Regulatory Report</h1>
        <p className="text-sm text-gray-600 font-bold">
          Download regulatory metrics and audit trails in CSV or Excel format
        </p>
      </div>

      {/* Configuration Form */}
      <div className="brutal-card max-w-2xl mx-auto">
        <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Portfolio ID
            </label>
            <input
              type="text"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="w-full border-3 border-black px-3 py-2 font-mono text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
              placeholder="test-portfolio-1"
            />
          </div>

          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Format
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as 'csv' | 'xlsx')}
              className="w-full border-3 border-black px-3 py-2 font-bold text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            >
              <option value="xlsx">Excel (.xlsx)</option>
              <option value="csv">CSV (.csv)</option>
            </select>
          </div>

          <div className="border-3 border-black p-4 bg-gray-50">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeAuditTrail}
                onChange={(e) => setIncludeAuditTrail(e.target.checked)}
                className="w-5 h-5 border-3 border-black"
              />
              <span className="text-sm font-bold">Include Audit Trail</span>
            </label>
            <p className="text-xs text-gray-600 mt-2 ml-8">
              Adds calculation provenance and assumptions for regulatory review
            </p>
          </div>

          <button
            onClick={handleExport}
            disabled={isExporting || !portfolioId}
            className="brutal-btn bg-brutal-green w-full text-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? 'Exporting...' : `Export as ${format.toUpperCase()}`}
          </button>
        </div>

        {/* Status Messages */}
        {exportStatus === 'success' && (
          <div className="mt-4 brutal-alert-success">
            <span className="font-black">Success!</span> Report downloaded successfully
          </div>
        )}

        {exportStatus === 'error' && (
          <div className="mt-4 brutal-alert-error">
            <span className="font-black">Error!</span> Export failed. Check console for details.
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className="brutal-card max-w-2xl mx-auto bg-brutal-lime">
        <h3 className="text-lg font-black mb-3 uppercase">Export Contents</h3>
        <ul className="space-y-2 text-sm font-bold">
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>CECL allowance by segment and lifetime PD calculations</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>Basel III RWA breakdown by counterparty type and rating</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>GAAP/IFRS classification and valuation results</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>Audit trail with calculation methods and assumptions (if enabled)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>Timestamped metadata for regulatory filing compliance</span>
          </li>
        </ul>
      </div>

      {/* Sample Data Preview */}
      <div className="brutal-card max-w-2xl mx-auto">
        <h3 className="text-lg font-black mb-3 uppercase border-b-3 border-black pb-2">
          Sample Export Structure
        </h3>
        <div className="bg-gray-100 border-3 border-black p-4 overflow-auto">
          <pre className="font-mono text-xs">
{`Portfolio ID: ${portfolioId}
Export Date: ${new Date().toISOString()}
Format: ${format.toUpperCase()}

Sections:
1. CECL Allowance Summary
   - Total allowance
   - Segment breakdown
   - Lifetime PD by position

2. Basel III Capital Ratios
   - Risk-weighted assets (RWA)
   - CET1 / Tier 1 / Total capital ratios
   - RWA by counterparty type

3. GAAP/IFRS Valuation
   - Asset classification (HTM/AFS/Trading)
   - Amortized cost vs. fair value
   - Impairment analysis

${includeAuditTrail ? '4. Audit Trail\n   - Calculation provenance\n   - Model versions\n   - Assumptions snapshot' : ''}`}
          </pre>
        </div>
      </div>
    </div>
  );
}
