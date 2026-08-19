import React, { useState } from 'react';
import {
  AlertTriangle,
  RotateCw,
  X,
  GitCompareArrows,
  ArrowRight,
  Hash,
  Tag,
  Clock,
  Filter,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { fetchQuarantine, fetchDuplicates } from '../api';
import {
  quarantineItems as fallbackQuarantine,
  duplicateDetections as fallbackDuplicates,
} from '../data/mockData';

const errorTypeColors = {
  StateTransitionError: 'bg-red-100 text-red-700 border-red-200',
  RedactionFailed: 'bg-purple-100 text-purple-700 border-purple-200',
  EmbeddingTimeout: 'bg-amber-100 text-amber-700 border-amber-200',
  DuplicateConflict: 'bg-blue-100 text-blue-700 border-blue-200',
};

function formatTime(isoString) {
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Triage() {
  const [filter, setFilter] = useState('All');

  const {
    data: quarantine,
    loading: qLoading,
    error: qError,
    refetch: refetchQ,
  } = useApi(fetchQuarantine, { fallback: fallbackQuarantine });

  const {
    data: duplicates,
    loading: dLoading,
    error: dError,
    refetch: refetchD,
  } = useApi(fetchDuplicates, { fallback: fallbackDuplicates });

  const quarantineData = quarantine || fallbackQuarantine;
  const duplicateData = duplicates || fallbackDuplicates;
  const usingFallback = qError || dError;

  const filteredQuarantine =
    filter === 'All'
      ? quarantineData
      : quarantineData.filter(
          (item) => item.severity?.toLowerCase() === filter.toLowerCase()
        );

  const getConfidenceClass = (score) => {
    if (score >= 0.85) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  };

  const filters = ['All', 'Critical', 'High', 'Medium', 'Low'];

  return (
    <div className="space-y-8">
      {usingFallback && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <AlertTriangle size={16} />
          <span>
            Unable to connect to backend API — displaying demo data.
            <button onClick={() => { refetchQ(); refetchD(); }} className="ml-2 font-semibold underline">
              Retry
            </button>
          </span>
        </div>
      )}

      {/* ── Quarantine Manager ── */}
      <section className="rounded-xl border border-neutral-border bg-white shadow-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-neutral-border bg-gray-50/60 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
              <AlertTriangle size={18} />
            </div>
            <h3 className="text-lg font-bold text-dark-base">Quarantine Manager</h3>
            <span className="badge badge-failed">{quarantineData.length} items</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refetchQ}
              className="mr-2 flex h-8 w-8 items-center justify-center rounded-md border border-neutral-border bg-white text-gray-500 transition-colors hover:bg-gray-50"
              disabled={qLoading}
              title="Refresh"
            >
              {qLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            </button>
            <Filter size={14} className="text-gray-400" />
            {filters.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors duration-150 ${
                  filter === f
                    ? 'bg-brand text-white'
                    : 'border border-neutral-border bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          {qLoading && !quarantine?.length ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-brand" />
              <span className="ml-3 text-sm text-gray-500">Loading quarantine data…</span>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Error Type</th>
                  <th>Severity</th>
                  <th>Message</th>
                  <th>Source</th>
                  <th>Retries</th>
                  <th>Timestamp</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredQuarantine.map((item) => {
                  const errorColor =
                    errorTypeColors[item.errorType] ||
                    'bg-gray-100 text-gray-700 border-gray-200';

                  return (
                    <tr key={item.id}>
                      <td className="font-mono text-xs font-medium text-dark-base">
                        {item.eventId}
                      </td>
                      <td>
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${errorColor}`}
                        >
                          {item.errorType}
                        </span>
                      </td>
                      <td>
                        <span className={`badge severity-${item.severity}`}>
                          {item.severity}
                        </span>
                      </td>
                      <td className="max-w-[280px] text-sm text-gray-600">{item.message}</td>
                      <td className="max-w-[200px] truncate text-sm text-gray-600">
                        {item.source}
                      </td>
                      <td>
                        <span className="font-mono text-sm">
                          <span
                            className={
                              item.retryCount >= item.maxRetries
                                ? 'font-bold text-red-600'
                                : 'text-gray-600'
                            }
                          >
                            {item.retryCount}
                          </span>
                          <span className="text-gray-400">/{item.maxRetries}</span>
                        </span>
                      </td>
                      <td className="whitespace-nowrap text-xs text-gray-500">
                        {formatTime(item.timestamp)}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button
                            className="btn-success opacity-50 cursor-not-allowed"
                            title="Coming Soon: Retry this event"
                            disabled
                          >
                            <RotateCw size={14} />
                            Retry
                          </button>
                          <button
                            className="btn-danger opacity-50 cursor-not-allowed"
                            title="Coming Soon: Dismiss this event"
                            disabled
                          >
                            <X size={14} />
                            Dismiss
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredQuarantine.length === 0 && (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-sm text-gray-400">
                      No quarantine items match the selected filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ── Duplicate Detection ── */}
      <section>
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50 text-violet-600">
              <GitCompareArrows size={18} />
            </div>
            <h3 className="text-lg font-bold text-dark-base">Duplicate Detection Insights</h3>
            <button
              onClick={refetchD}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-neutral-border bg-white text-gray-400 transition-colors hover:bg-gray-50"
              disabled={dLoading}
              title="Refresh"
            >
              {dLoading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            </button>
          </div>
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
            Threshold ≥ 0.85
          </span>
        </div>

        {dLoading && !duplicates?.length ? (
          <div className="flex items-center justify-center rounded-xl border border-neutral-border bg-white py-16 shadow-card">
            <Loader2 size={24} className="animate-spin text-brand" />
            <span className="ml-3 text-sm text-gray-500">Loading duplicate data…</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {duplicateData.map((dup) => {
              const confClass = getConfidenceClass(dup.confidence);
              const confPct = Math.round(dup.confidence * 100);
              const meetsThreshold = dup.confidence >= 0.85;

              const statusMap = {
                matched: 'badge-completed',
                reviewing: 'badge-running',
                dismissed: 'badge-failed',
              };

              return (
                <div
                  key={dup.id}
                  className={`rounded-xl border bg-white p-6 shadow-card transition-all duration-200 hover:shadow-lg ${
                    meetsThreshold ? 'border-emerald-200' : 'border-neutral-border'
                  }`}
                >
                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm font-semibold text-dark-base">
                      {dup.sourceIssue?.title || `Event ${dup.sourceIssue?.id}`}
                    </p>
                    <div className="my-2 flex items-center gap-2 text-gray-400">
                      <ArrowRight size={16} />
                      <span className="text-xs">matched with</span>
                    </div>
                    <p className="text-sm font-semibold text-dark-base">
                      {dup.targetIssue?.title || `Candidate ${dup.targetIssue?.id}`}
                    </p>
                  </div>

                  <div className="mt-5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-600">Confidence Score</span>
                      <span className="font-extrabold text-dark-base">{confPct}%</span>
                    </div>
                    <div className="confidence-bar mt-2">
                      <div
                        className={`confidence-bar-fill ${confClass}`}
                        style={{ width: `${confPct}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                      <p className="flex items-center gap-1 text-xs text-gray-500">
                        <Hash size={12} /> Vector Similarity
                      </p>
                      <p className="mt-0.5 font-mono text-sm font-semibold text-dark-base">
                        {dup.vectorSimilarity?.toFixed(3) || '—'}
                      </p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock size={12} /> Detected
                      </p>
                      <p className="mt-0.5 text-sm text-gray-600">
                        {formatTime(dup.detectedAt)}
                      </p>
                    </div>
                  </div>

                  {dup.entityOverlap?.length > 0 && (
                    <div className="mt-4">
                      <p className="mb-2 flex items-center gap-1 text-xs text-gray-500">
                        <Tag size={12} /> Entity Overlap
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {dup.entityOverlap.map((tag, i) => (
                          <span
                            key={i}
                            className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-5 flex items-center justify-between border-t border-neutral-border pt-4">
                    <span className={`badge ${statusMap[dup.status] || 'badge-pending'}`}>
                      {dup.status}
                    </span>
                    <button 
                      className="btn-outline text-xs opacity-50 cursor-not-allowed" 
                      title="Coming Soon: Review this match" 
                      disabled
                    >
                      Review Match
                    </button>
                  </div>
                </div>
              );
            })}
            {duplicateData.length === 0 && (
              <div className="col-span-2 rounded-xl border border-neutral-border bg-white py-12 text-center text-sm text-gray-400 shadow-card">
                No duplicate candidates detected.
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
