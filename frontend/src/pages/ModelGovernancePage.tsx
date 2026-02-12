import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface ModelVersion {
  model_version: string;
  model_type: string;
  git_hash?: string;
  deployment_date: string;
  approval_status: string;
  backtesting_results_json?: Record<string, any>;
  notes?: string;
}

function StatusBadge({ status }: { status: string }) {
  const colorClass = {
    APPROVED: 'bg-brutal-green text-black',
    TESTING: 'bg-brutal-yellow text-black',
    DEPRECATED: 'bg-brutal-red text-white',
    PENDING: 'bg-brutal-blue text-black',
  }[status] || 'bg-gray-400 text-white';

  return (
    <span className={`brutal-badge ${colorClass}`}>
      {status}
    </span>
  );
}

export default function ModelGovernancePage() {
  const { data: models, isLoading } = useQuery<ModelVersion[]>({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/regulatory/models/');
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="brutal-card">
        <h1 className="brutal-title mb-2">Model Governance</h1>
        <p className="text-sm text-gray-600 font-bold">
          Model version registry with approval tracking and backtesting results
        </p>
      </div>

      {isLoading && (
        <div className="brutal-card">
          <p className="text-center font-bold animate-pulse">Loading models...</p>
        </div>
      )}

      {models && models.length > 0 && (
        <div className="brutal-card">
          <h2 className="text-xl font-black mb-4 border-b-3 border-black pb-2">
            Model Versions ({models.length})
          </h2>
          <div className="border-3 border-black overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-black text-white">
                  <th className="p-3 text-left font-black uppercase text-sm">Version</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Type</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Git Hash</th>
                  <th className="p-3 text-left font-black uppercase text-sm">
                    Deployment Date
                  </th>
                  <th className="p-3 text-left font-black uppercase text-sm">Status</th>
                  <th className="p-3 text-left font-black uppercase text-sm">Notes</th>
                </tr>
              </thead>
              <tbody>
                {models.map((model, idx) => (
                  <tr
                    key={model.model_version}
                    className={idx % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-100 hover:bg-gray-200'}
                  >
                    <td className="p-3 font-mono font-bold">{model.model_version}</td>
                    <td className="p-3 font-bold">{model.model_type}</td>
                    <td className="p-3 font-mono text-xs">
                      {model.git_hash?.substring(0, 10) || (
                        <span className="text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="p-3 text-sm">
                      {new Date(model.deployment_date).toLocaleDateString()}
                    </td>
                    <td className="p-3">
                      <StatusBadge status={model.approval_status} />
                    </td>
                    <td className="p-3 text-sm max-w-xs truncate">
                      {model.notes || <span className="text-gray-400">--</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {models && models.length === 0 && !isLoading && (
        <div className="brutal-card bg-brutal-yellow">
          <p className="text-center font-bold">No model versions registered</p>
        </div>
      )}

      {/* Info Card */}
      <div className="brutal-card bg-brutal-blue">
        <h3 className="text-lg font-black mb-3 uppercase">About Model Governance</h3>
        <ul className="space-y-2 text-sm font-bold">
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>
              All pricing and risk models are versioned with git hashes for traceability
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>
              Approval status tracks model validation and testing lifecycle
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>
              Backtesting results stored in JSONB for auditor review
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-2xl leading-none">•</span>
            <span>
              Model changes trigger re-approval workflow before production deployment
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
