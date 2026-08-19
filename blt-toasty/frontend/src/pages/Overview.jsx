import React from 'react';
import {
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Webhook,
  ShieldCheck,
  AlertTriangle,
  Shield,
  FileText,
  Database,
  Search,
  ExternalLink,
  Timer,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { fetchMetrics, fetchActivity } from '../api';
import {
  overviewMetrics as fallbackMetrics,
  activityFeed as fallbackActivity,
} from '../data/mockData';

const iconMap = {
  Activity,
  Webhook,
  ShieldCheck,
  Clock,
  AlertTriangle,
  Shield,
  FileText,
  Database,
  Search,
  Timer,
};

const typeConfig = {
  webhook_received: { label: 'Webhook', color: 'bg-blue-100 text-blue-700' },
  redaction_check: { label: 'Redaction', color: 'bg-purple-100 text-purple-700' },
  summarization: { label: 'Summary', color: 'bg-amber-100 text-amber-700' },
  embedding: { label: 'Embed', color: 'bg-emerald-100 text-emerald-700' },
  duplicate_check: { label: 'Dedup', color: 'bg-rose-100 text-rose-700' },
};

const statusConfig = {
  pending: 'badge-pending',
  redaction_passed: 'badge-completed',
  summarized: 'badge-completed',
  embedded: 'badge-completed',
  failed: 'badge-failed',
  quarantined: 'badge-failed',
  exported: 'badge-completed',
};

function formatTime(isoString) {
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatLatency(ms) {
  if (!ms || ms === 0) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function Overview() {
  const {
    data: metrics,
    loading: metricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useApi(fetchMetrics, { fallback: fallbackMetrics });

  const {
    data: activity,
    loading: activityLoading,
    error: activityError,
    refetch: refetchActivity,
  } = useApi(fetchActivity, { fallback: fallbackActivity, pollMs: 30000 });

  const usingFallback = metricsError || activityError;

  return (
    <div className="space-y-8">
      {/* Fallback indicator */}
      {usingFallback && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <AlertTriangle size={16} />
          <span>
            Unable to connect to backend API — displaying demo data.
            <button onClick={() => { refetchMetrics(); refetchActivity(); }} className="ml-2 font-semibold underline">
              Retry
            </button>
          </span>
        </div>
      )}

      {/* Metrics Bar */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {(metrics || fallbackMetrics).map((metric) => {
          const Icon = iconMap[metric.icon] || Activity;
          const isAttention = metric.icon === 'AlertTriangle' && metric.changeType === 'up';

          return (
            <div
              key={metric.id}
              className={`metric-card rounded-xl border border-neutral-border bg-white p-5 shadow-card ${metricsLoading ? 'animate-pulse' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    metric.icon === 'AlertTriangle'
                      ? 'bg-amber-50 text-amber-600'
                      : metric.icon === 'ShieldCheck'
                      ? 'bg-emerald-50 text-emerald-600'
                      : metric.icon === 'Timer'
                      ? 'bg-sky-50 text-sky-600'
                      : 'bg-blue-50 text-blue-600'
                  }`}
                >
                  <Icon size={20} />
                </div>
                {metric.change && (
                  <div
                    className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                      isAttention
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-emerald-50 text-emerald-700'
                    }`}
                  >
                    {metric.changeType === 'up' ? (
                      <ArrowUpRight size={14} />
                    ) : (
                      <ArrowDownRight size={14} />
                    )}
                    {metric.change}
                  </div>
                )}
              </div>
              <p className="mt-4 text-3xl font-extrabold text-dark-base">{metric.value}</p>
              <p className="mt-1 text-xs font-semibold uppercase tracking-[0.15em] text-gray-500">
                {metric.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* Live Activity Feed */}
      <div className="rounded-xl border border-neutral-border bg-white shadow-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-neutral-border bg-gray-50/60 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="live-dot" />
            <h3 className="text-lg font-bold text-dark-base">Live Pipeline Activity</h3>
            <span className="badge badge-running">
              {(activity || fallbackActivity).length} events
            </span>
          </div>
          <button
            onClick={refetchActivity}
            className="btn-ghost text-xs"
            disabled={activityLoading}
          >
            {activityLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
        </div>

        <div className="divide-y divide-neutral-border max-h-[640px] overflow-y-auto">
          {activityLoading && !activity?.length ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-brand" />
              <span className="ml-3 text-sm text-gray-500">Loading activity…</span>
            </div>
          ) : (
            (activity || fallbackActivity).map((item) => {
              const type = typeConfig[item.type] || {
                label: item.type,
                color: 'bg-gray-100 text-gray-700',
              };
              const statusClass = statusConfig[item.status] || 'badge-pending';
              const displayStatus = item.status.replace(/_/g, ' ');

              return (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 px-6 py-4 transition-colors duration-150 hover:bg-gray-50/50 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-center gap-3 sm:min-w-[200px]">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${type.color}`}
                    >
                      {type.label}
                    </span>
                    <span className="font-mono text-xs text-gray-400">{item.eventId}</span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-dark-base">{item.source}</p>
                    <p className="mt-0.5 truncate font-mono text-xs text-gray-400">
                      {item.target}
                    </p>
                  </div>

                  <div className="flex items-center gap-4 sm:min-w-[260px] sm:justify-end">
                    <span className={`badge ${statusClass}`}>{displayStatus}</span>
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <Clock size={12} />
                      {formatLatency(item.latencyMs)}
                    </span>
                    <span className="min-w-[70px] text-right text-xs text-gray-400">
                      {formatTime(item.timestamp)}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
