import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface AuditEntry {
  audit_id: string;
  audit_type: string;
  calculation_method: string;
  entity_id: string;
  computed_at: string;
  assumptions_json: Record<string, any>;
  results_json: Record<string, any>;
}

export default function AuditTrailPage() {
  const [entityId, setEntityId] = useState('');
  const [auditType, setAuditType] = useState('');
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);

  const { data: auditEntries, isLoading, refetch } = useQuery<AuditEntry[]>({
    queryKey: ['audit', 'search', entityId, auditType],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (entityId) params.append('entity_id', entityId);
      if (auditType) params.append('audit_type', auditType);
      params.append('limit', '50');

      const response = await axios.get(`/api/v1/regulatory/audit/events?${params.toString()}`);
      return response.data;
    },
    enabled: false,
  });

  const { data: selectedEntry } = useQuery<AuditEntry>({
    queryKey: ['audit', selectedAuditId],
    queryFn: async () => {
      const response = await axios.get(`/api/v1/regulatory/audit/events/${selectedAuditId}`);
      return response.data;
    },
    enabled: !!selectedAuditId,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="brutal-card">
        <h1 className="brutal-title mb-2">Audit Trail</h1>
        <p className="text-sm text-gray-600 font-bold">
          Immutable calculation provenance for regulatory compliance
        </p>
      </div>

      {/* Search Form */}
      <div className="brutal-card">
        <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">Search</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Entity ID
            </label>
            <input
              type="text"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="portfolio-1, position-123..."
              className="w-full border-3 border-black px-3 py-2 font-mono text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2 uppercase tracking-wide">
              Audit Type
            </label>
            <select
              value={auditType}
              onChange={(e) => setAuditType(e.target.value)}
              className="w-full border-3 border-black px-3 py-2 font-bold text-sm focus:outline-none focus:ring-4 focus:ring-brutal-yellow"
            >
              <option value="">All</option>
              <option value="CECL">CECL</option>
              <option value="BASEL">Basel III</option>
              <option value="GAAP">GAAP</option>
              <option value="IFRS">IFRS</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="brutal-btn bg-brutal-blue w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>
      </div>

      {/* Results Table */}
      {auditEntries && auditEntries.length > 0 && (
        <div className="brutal-card">
          <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">
            Results ({auditEntries.length})
          </h2>
          <div className="border-3 border-black overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-black text-white">
                  <th className="p-3 text-left font-black uppercase text-sm">Audit ID</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Type</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Method</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Entity ID</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Computed At</th>
                  <th className="p-3 text-center font-black uppercase text-sm">Action</th>
                </tr>
              </thead>
              <tbody>
                {auditEntries.map((entry, idx) => (
                  <tr
                    key={entry.audit_id}
                    className={idx % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-100 hover:bg-gray-200'}
                  >
                    <td className="p-3 font-mono text-xs">
                      {entry.audit_id.substring(0, 12)}...
                    </td>
                    <td className="p-3 font-bold">
                      <span className="brutal-badge-yellow">{entry.audit_type}</span>
                    </td>
                    <td className="p-3 font-mono text-xs">{entry.calculation_method}</td>
                    <td className="p-3 font-mono text-xs">{entry.entity_id}</td>
                    <td className="p-3 text-sm">
                      {new Date(entry.computed_at).toLocaleString()}
                    </td>
                    <td className="p-3 text-center">
                      <button
                        onClick={() => setSelectedAuditId(entry.audit_id)}
                        className="brutal-btn bg-brutal-lime text-xs px-3 py-1"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail View */}
      {selectedEntry && (
        <div className="brutal-card">
          <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">
            Audit Entry Detail
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-1">Audit ID</p>
              <p className="font-mono text-sm bg-black text-white p-2 break-all">
                {selectedEntry.audit_id}
              </p>
            </div>
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-1">
                Calculation Method
              </p>
              <p className="font-mono text-sm bg-black text-white p-2">
                {selectedEntry.calculation_method}
              </p>
            </div>
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-1">Entity ID</p>
              <p className="font-mono text-sm bg-black text-white p-2">
                {selectedEntry.entity_id}
              </p>
            </div>
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-1">Computed At</p>
              <p className="font-mono text-sm bg-black text-white p-2">
                {new Date(selectedEntry.computed_at).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-2">Assumptions</p>
              <div className="bg-gray-100 border-3 border-black p-4 overflow-auto max-h-96">
                <pre className="font-mono text-xs">
                  {JSON.stringify(selectedEntry.assumptions_json, null, 2)}
                </pre>
              </div>
            </div>
            <div>
              <p className="text-sm font-bold uppercase text-gray-600 mb-2">Results</p>
              <div className="bg-gray-100 border-3 border-black p-4 overflow-auto max-h-96">
                <pre className="font-mono text-xs">
                  {JSON.stringify(selectedEntry.results_json, null, 2)}
                </pre>
              </div>
            </div>
          </div>

          <div className="mt-6 bg-brutal-yellow border-3 border-black p-4">
            <p className="text-sm font-black uppercase">
              This audit entry is immutable and cannot be modified
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
