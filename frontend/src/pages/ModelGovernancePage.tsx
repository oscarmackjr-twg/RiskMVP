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
  calibration_date?: string;
  notes?: string;
}

function StatusBadge({ status }: { status: string }) {
  const badgeClass = {
    APPROVED: 'twg-badge-success',
    TESTING: 'twg-badge-warning',
    DEPRECATED: 'twg-badge-error',
    PENDING: 'twg-badge-primary',
  }[status] || 'twg-badge-neutral';

  return <span className={badgeClass}>{status}</span>;
}

export default function ModelGovernancePage() {
  const { data: models, isLoading, isError, error } = useQuery<ModelVersion[]>({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/regulatory/models/');
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="twg-card">
        <h1 className="twg-title mb-2">Model Governance</h1>
        <p className="twg-subtitle">
          Model version registry with approval tracking and backtesting results
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="twg-card text-center py-8">
          <span className="twg-spinner mr-2"></span>
          <span className="text-sm text-twg-muted">Loading models...</span>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="twg-alert-warning">
          <p className="font-medium">Unable to load model versions</p>
          <p className="text-sm mt-1">
            The regulatory service may not be running.{' '}
            {(error as any)?.message && (
              <span className="font-mono text-xs">({(error as any).message})</span>
            )}
          </p>
        </div>
      )}

      {/* Models Table */}
      {models && models.length > 0 && (
        <div className="twg-card">
          <h2 className="text-lg font-semibold mb-4">
            Model Versions ({models.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="twg-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Type</th>
                  <th>Git Hash</th>
                  <th>Deployment Date</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {models.map((model) => (
                  <tr key={model.model_version}>
                    <td className="font-mono font-medium">{model.model_version}</td>
                    <td>{model.model_type}</td>
                    <td className="font-mono text-xs">
                      {model.git_hash?.substring(0, 10) || (
                        <span className="text-twg-muted">N/A</span>
                      )}
                    </td>
                    <td className="text-sm">
                      {new Date(model.deployment_date).toLocaleDateString()}
                    </td>
                    <td>
                      <StatusBadge status={model.approval_status} />
                    </td>
                    <td className="text-sm max-w-xs truncate">
                      {model.notes || <span className="text-twg-muted">--</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {models && models.length === 0 && (
        <div className="twg-alert-info">
          <p className="font-medium">No model versions registered</p>
          <p className="text-sm mt-1">
            Register model versions via the API to track governance lifecycle.
          </p>
        </div>
      )}

      {/* Info Card */}
      <div className="twg-card bg-gray-50">
        <h3 className="text-base font-semibold mb-3">About Model Governance</h3>
        <ul className="space-y-2 text-sm text-twg-muted">
          <li>All pricing and risk models are versioned with git hashes for traceability</li>
          <li>Approval status tracks model validation and testing lifecycle (TESTING / APPROVED / DEPRECATED)</li>
          <li>Backtesting results stored in JSONB for auditor review</li>
          <li>Model changes trigger re-approval workflow before production deployment</li>
        </ul>
      </div>
    </div>
  );
}
