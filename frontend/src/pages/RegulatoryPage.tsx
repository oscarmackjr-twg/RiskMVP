import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface RegulatoryMetrics {
  total_allowance?: number;
  by_segment?: Record<string, number>;
  capital_ratios?: {
    cet1_ratio: number;
    tier1_ratio: number;
    total_capital_ratio: number;
  };
  total_rwa?: number;
  by_counterparty_type?: Record<string, number>;
  audit_id?: string;
}

interface CECLRequest {
  portfolio_node_id: string;
  as_of_date: string;
  q_factor: number;
}

interface BaselRequest {
  portfolio_node_id: string;
  as_of_date: string;
  tier1_capital: number;
  tier2_capital: number;
}

function MetricCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className={`p-4 md:p-6 border-3 border-black ${color}`}>
      <div className="text-xs md:text-sm font-bold uppercase tracking-wide mb-1 text-gray-700">{label}</div>
      <div className="text-2xl md:text-3xl font-black font-mono">{value}</div>
    </div>
  );
}

export default function RegulatoryPage() {
  const [portfolioId, setPortfolioId] = useState('test-portfolio-1');
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0]);
  const [qFactor, setQFactor] = useState(0.0);
  const [tier1Capital, setTier1Capital] = useState(10000000);
  const [tier2Capital, setTier2Capital] = useState(5000000);

  // Fetch CECL allowance
  const {
    data: ceclData,
    isLoading: ceclLoading,
    refetch: refetchCecl,
  } = useQuery<RegulatoryMetrics>({
    queryKey: ['cecl', portfolioId, asOfDate, qFactor],
    queryFn: async () => {
      const response = await axios.post('/api/v1/regulatory/cecl/compute', {
        portfolio_node_id: portfolioId,
        as_of_date: asOfDate,
        q_factor: qFactor,
      } as CECLRequest);
      return response.data;
    },
    enabled: false,  // Manual trigger
  });

  // Fetch Basel RWA
  const {
    data: baselData,
    isLoading: baselLoading,
    refetch: refetchBasel,
  } = useQuery<RegulatoryMetrics>({
    queryKey: ['basel', portfolioId, asOfDate, tier1Capital, tier2Capital],
    queryFn: async () => {
      const response = await axios.post('/api/v1/regulatory/basel/compute', {
        portfolio_node_id: portfolioId,
        as_of_date: asOfDate,
        tier1_capital: tier1Capital,
        tier2_capital: tier2Capital,
      } as BaselRequest);
      return response.data;
    },
    enabled: false,  // Manual trigger
  });

  const formatCurrency = (num: number | undefined) => {
    if (num === undefined || num === null) return '--';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  };

  const formatPercent = (num: number | undefined) => {
    if (num === undefined || num === null) return '--';
    return (num * 100).toFixed(2) + '%';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="brutal-card">
        <h1 className="brutal-title mb-2">Regulatory Analytics</h1>
        <p className="text-sm text-gray-600 font-bold">
          CECL Allowance (ASC 326) & Basel III Capital Ratios
        </p>
      </div>

      {/* Configuration Form */}
      <div className="brutal-card">
        <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Portfolio ID
            </label>
            <input
              type="text"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="w-full border-3 border-black px-3 py-2 font-mono text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              As Of Date
            </label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="w-full border-3 border-black px-3 py-2 font-mono text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Q-Factor (CECL)
            </label>
            <input
              type="number"
              value={qFactor}
              onChange={(e) => setQFactor(parseFloat(e.target.value))}
              step="0.01"
              min="0"
              max="0.5"
              className="w-full border-3 border-black px-3 py-2 font-mono text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            />
          </div>
        </div>
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => refetchCecl()}
            disabled={ceclLoading}
            className="brutal-btn bg-brutal-blue flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {ceclLoading ? 'Calculating...' : 'Calculate CECL'}
          </button>
          <button
            onClick={() => refetchBasel()}
            disabled={baselLoading}
            className="brutal-btn bg-brutal-green flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {baselLoading ? 'Calculating...' : 'Calculate Basel RWA'}
          </button>
        </div>
      </div>

      {/* CECL Allowance Summary */}
      {ceclData && (
        <div className="brutal-card">
          <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">
            CECL Allowance
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <MetricCard
              label="Total Allowance"
              value={formatCurrency(ceclData.total_allowance)}
              color="bg-brutal-blue"
            />
            <MetricCard
              label="Segments"
              value={Object.keys(ceclData.by_segment || {}).length}
              color="bg-brutal-yellow"
            />
            <MetricCard
              label="Audit ID"
              value={(ceclData.audit_id || '').substring(0, 12) + '...'}
              color="bg-brutal-lime"
            />
          </div>

          {ceclData.by_segment && Object.keys(ceclData.by_segment).length > 0 && (
            <>
              <h3 className="text-lg font-black mb-3 uppercase tracking-wide">By Segment</h3>
              <div className="border-3 border-black overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-black text-white">
                      <th className="p-3 text-left font-black uppercase text-sm">Segment</th>
                      <th className="p-3 text-right font-black uppercase text-sm">Allowance</th>
                      <th className="p-3 text-right font-black uppercase text-sm">% of Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(ceclData.by_segment).map(([segment, allowance], idx) => (
                      <tr
                        key={segment}
                        className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-100'}
                      >
                        <td className="p-3 font-bold">{segment}</td>
                        <td className="p-3 text-right font-mono">
                          {formatCurrency(allowance)}
                        </td>
                        <td className="p-3 text-right font-mono font-bold">
                          {((allowance / (ceclData.total_allowance || 1)) * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Basel RWA Summary */}
      {baselData && (
        <div className="brutal-card">
          <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">
            Basel III Capital Ratios
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Total RWA"
              value={formatCurrency(baselData.total_rwa)}
              color="bg-brutal-green"
            />
            <MetricCard
              label="CET1 Ratio"
              value={formatPercent(baselData.capital_ratios?.cet1_ratio)}
              color="bg-brutal-blue"
            />
            <MetricCard
              label="Tier 1 Ratio"
              value={formatPercent(baselData.capital_ratios?.tier1_ratio)}
              color="bg-brutal-blue"
            />
            <MetricCard
              label="Total Capital Ratio"
              value={formatPercent(baselData.capital_ratios?.total_capital_ratio)}
              color="bg-brutal-blue"
            />
          </div>

          {baselData.by_counterparty_type && Object.keys(baselData.by_counterparty_type).length > 0 && (
            <>
              <h3 className="text-lg font-black mb-3 uppercase tracking-wide">
                RWA by Counterparty Type
              </h3>
              <div className="border-3 border-black overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-black text-white">
                      <th className="p-3 text-left font-black uppercase text-sm">
                        Counterparty Type
                      </th>
                      <th className="p-3 text-right font-black uppercase text-sm">RWA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(baselData.by_counterparty_type).map(([type, rwa], idx) => (
                      <tr
                        key={type}
                        className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-100'}
                      >
                        <td className="p-3 font-bold">{type}</td>
                        <td className="p-3 text-right font-mono">{formatCurrency(rwa)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
