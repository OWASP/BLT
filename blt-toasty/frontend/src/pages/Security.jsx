import React, { useState, useMemo } from 'react';
import {
  Search,
  Download,
  Shield,
  Mail,
  Key,
  Lock,
  Phone,
  CreditCard,
  Globe,
  Hash,
  FileText,
  Loader2,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { fetchRedactions } from '../api';
import { redactionLog as fallbackRedactions } from '../data/mockData';

const entityBadgeMap = {
  EMAIL_ADDRESS: 'severity-info',
  JWT: 'severity-critical',
  AWS_KEY: 'severity-critical',
  GITHUB_TOKEN: 'severity-critical',
  SSN: 'severity-critical',
  API_KEY: 'severity-high',
  CREDIT_CARD: 'severity-high',
  PHONE_NUMBER: 'severity-medium',
  IP_ADDRESS: 'severity-medium',
};

const entityIconMap = {
  EMAIL_ADDRESS: Mail,
  PHONE_NUMBER: Phone,
  AWS_KEY: Key,
  API_KEY: Key,
  JWT: Key,
  GITHUB_TOKEN: Lock,
  CREDIT_CARD: CreditCard,
  IP_ADDRESS: Globe,
  SSN: Hash,
};

const entityIconBgMap = {
  'severity-critical': 'bg-red-50 text-red-600',
  'severity-high': 'bg-orange-50 text-orange-600',
  'severity-medium': 'bg-amber-50 text-amber-600',
  'severity-info': 'bg-sky-50 text-sky-600',
};

export default function Security() {
  const [search, setSearch] = useState('');

  const {
    data: redactions,
    loading,
    error,
    refetch,
  } = useApi(fetchRedactions, { fallback: fallbackRedactions });

  const redactionData = redactions || fallbackRedactions;

  const { presidioCount, regexCount, entityBreakdown } = useMemo(() => {
    let presidio = 0;
    let regex = 0;
    const typeMap = new Map();

    for (const log of redactionData) {
      if (log.redactionMethod === 'presidio') presidio++;
      else regex++;
      typeMap.set(log.entityType, (typeMap.get(log.entityType) || 0) + 1);
    }

    const breakdown = Array.from(typeMap.entries())
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);

    return { presidioCount: presidio, regexCount: regex, entityBreakdown: breakdown };
  }, [redactionData]);

  const filteredLog = useMemo(() => {
    if (!search) return redactionData;
    const q = search.toLowerCase();
    return redactionData.filter(
      (log) =>
        log.eventId.toLowerCase().includes(q) ||
        log.entityType.toLowerCase().includes(q)
    );
  }, [redactionData, search]);

  return (
    <div className="space-y-6">
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <AlertTriangle size={16} />
          <span>
            Unable to connect to backend API — displaying demo data.
            <button onClick={refetch} className="ml-2 font-semibold underline">Retry</button>
          </span>
        </div>
      )}

      {/* Summary stats row */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <div className={`rounded-xl border border-neutral-border bg-white p-6 shadow-card ${loading ? 'animate-pulse' : ''}`}>
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Shield size={20} />
            </div>
            <h3 className="text-sm font-semibold text-gray-600">Total Redactions</h3>
          </div>
          <div className="text-3xl font-extrabold text-dark-base">{redactionData.length}</div>
        </div>

        <div className={`rounded-xl border border-neutral-border bg-white p-6 shadow-card ${loading ? 'animate-pulse' : ''}`}>
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <FileText size={20} />
            </div>
            <h3 className="text-sm font-semibold text-gray-600">Detection Methods</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-dark-base">{presidioCount}</span>
            <span className="text-sm font-medium text-gray-500">Presidio</span>
            <span className="mx-1 text-gray-300">|</span>
            <span className="text-3xl font-extrabold text-dark-base">{regexCount}</span>
            <span className="text-sm font-medium text-gray-500">Regex</span>
          </div>
        </div>

        <div className={`rounded-xl border border-neutral-border bg-white p-6 shadow-card ${loading ? 'animate-pulse' : ''}`}>
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 text-purple-600">
              <Key size={20} />
            </div>
            <h3 className="text-sm font-semibold text-gray-600">Entity Types</h3>
          </div>
          <div className="text-3xl font-extrabold text-dark-base">{entityBreakdown.length}</div>
        </div>
      </div>

      {/* Redaction Log Table */}
      <div className="rounded-xl border border-neutral-border bg-white shadow-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-neutral-border px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-lg font-bold text-dark-base">Audit Log</h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                placeholder="Search event ID or type…"
                className="w-64 rounded-lg border border-gray-200 py-2 pl-9 pr-4 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button
              onClick={refetch}
              className="btn-ghost"
              disabled={loading}
              title="Refresh data"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              Refresh
            </button>
            <button className="btn-ghost">
              <Download size={14} />
              Export
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          {loading && !redactions?.length ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-brand" />
              <span className="ml-3 text-sm text-gray-500">Loading redaction log…</span>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event ID</th>
                  <th>Entity Type</th>
                  <th>Original Bytes</th>
                  <th>Redaction Method</th>
                  <th>Source File</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {filteredLog.map((log) => (
                  <tr key={log.id}>
                    <td className="whitespace-nowrap text-sm text-gray-600">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td>
                      <span className="rounded bg-gray-100 px-2 py-1 font-mono text-xs text-gray-500">
                        {log.eventId}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${entityBadgeMap[log.entityType] || 'severity-low'}`}>
                        {log.entityType.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="text-sm text-gray-600">{log.originalByteLength} B</td>
                    <td>
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600">
                        {log.redactionMethod.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="font-mono text-xs text-gray-500">{log.sourceFile}</span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div
                          className={`h-2 w-2 rounded-full ${
                            log.confidence >= 0.95
                              ? 'bg-green-500'
                              : log.confidence >= 0.8
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                          }`}
                        />
                        <span className="text-sm font-medium text-gray-700">
                          {(log.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredLog.length === 0 && (
                  <tr>
                    <td colSpan="7" className="py-8 text-center text-gray-500">
                      No logs found matching "{search}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Entity Type Breakdown */}
      <div>
        <h3 className="mb-4 text-lg font-bold text-dark-base">Entity Type Breakdown</h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-5">
          {entityBreakdown.map((item) => {
            const badgeClass = entityBadgeMap[item.type] || 'severity-low';
            const IconComp = entityIconMap[item.type] || Shield;
            const bgClass = entityIconBgMap[badgeClass] || 'bg-gray-50 text-gray-600';

            return (
              <div
                key={item.type}
                className="flex items-center gap-4 rounded-xl border border-neutral-border bg-white p-4 shadow-soft transition-colors hover:border-gray-300"
              >
                <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${bgClass}`}>
                  <IconComp size={16} />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-[10px] font-bold uppercase tracking-wider text-gray-500">
                    {item.type.replace(/_/g, ' ')}
                  </div>
                  <div className="text-lg font-extrabold text-dark-base">{item.count}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
