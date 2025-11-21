"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useToasts } from "../components/ToastProvider";
import {
  ConsentEntry,
  PolicyEvent,
  TelemetryMetric,
  fetchConsentHistory,
  fetchPermissions,
  fetchPolicyEvents,
  fetchTelemetryFeed,
  subscribeStateStream,
  updateContextBlocklist,
} from "../../lib/api";
import styles from "./ConsolePage.module.css";
import { SectionCard } from "./components/SectionCard";
import { MetricCard } from "./components/MetricCard";
import { TabNavigation } from "./components/TabNavigation";
import { DataTable } from "./components/DataTable";
import { EventTimeline } from "./components/EventTimeline";
import { ConsentAnalytics } from "./components/ConsentAnalytics";
import { MetricExplorer } from "./components/MetricExplorer";
import { ColumnDef, EventFilters } from "./types";
import {
  buildHistoricalSeries,
  formatTimestamp,
  getStatusFromValue,
} from "./utils";

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "events", label: "Events" },
  { id: "consent", label: "Consent" },
  { id: "metrics", label: "Metrics" },
  { id: "logs", label: "Logs" },
];
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

const mergeUnique = (current: string[], incoming: string[]) => {
  const next = new Set(current);
  incoming.forEach((entry) => {
    if (entry) {
      next.add(entry);
    }
  });
  return Array.from(next);
};

const formatSecondsCompact = (seconds?: number | null) => {
  if (seconds === null || seconds === undefined) return "--";
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(1)}m`;
  const hours = minutes / 60;
  return `${hours.toFixed(1)}h`;
};

export default function ConsolePage() {
  const { addToast } = useToasts();
  const [policyEvents, setPolicyEvents] = useState<PolicyEvent[]>([]);
  const [policyTotal, setPolicyTotal] = useState(0);
  const [consentEntries, setConsentEntries] = useState<ConsentEntry[]>([]);
  const [consentTotal, setConsentTotal] = useState(0);
  const [metrics, setMetrics] = useState<TelemetryMetric[]>([]);
  const [metricTotal, setMetricTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [liveStream, setLiveStream] = useState(true);
  const [streamConnected, setStreamConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [eventFilters, setEventFilters] = useState<EventFilters>({});
  const streamTriggerRef = useRef<NodeJS.Timeout | null>(null);
  const [contextBlocklist, setContextBlocklist] = useState<string[]>([]);
  const [contextOptions, setContextOptions] = useState<string[]>([]);
  const [runningApps, setRunningApps] = useState<string[]>([]);
  const [activeApps, setActiveApps] = useState<string[]>([]);
  const [liveContextFlags, setLiveContextFlags] = useState<string[]>([]);
  const [idleBlockSeconds, setIdleBlockSeconds] = useState<number | null>(null);
  const [inactivitySeconds, setInactivitySeconds] = useState<number | null>(
    null
  );
  const [loadState, setLoadState] = useState<string>("--");
  const [contextSaving, setContextSaving] = useState(false);
  const [contextError, setContextError] = useState<string | null>(null);
  const streamToastState = useRef<"connected" | "disconnected" | null>(null);

  const loadData = useCallback(
    async (notify = false) => {
      setLoading(true);
      try {
        const [events, consent, feed] = await Promise.all([
          fetchPolicyEvents(50),
          fetchConsentHistory(25),
          fetchTelemetryFeed(200),
        ]);
        setPolicyEvents(events.slice(0, 20));
        setPolicyTotal(events.length);
        setConsentEntries(consent.slice(-20));
        setConsentTotal(consent.length);
        setMetrics(feed.slice(0, 60));
        setMetricTotal(feed.length);
        setLastUpdate(new Date());
        setError(null);
        if (notify) {
          addToast("Console data refreshed", "success");
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load console data";
        setError(message);
        addToast(message, "error");
      } finally {
        setLoading(false);
      }
    },
    [addToast]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    fetchPermissions()
      .then((status) => {
        setContextBlocklist(status.context_blocklist ?? []);
        setContextOptions((previous) =>
          mergeUnique(previous, status.context_blocklist ?? [])
        );
        setRunningApps((previous) =>
          mergeUnique(previous, status.context_catalog ?? [])
        );
        setIdleBlockSeconds(status.idle_block_seconds ?? null);
        setContextError(null);
      })
      .catch((err) => {
        const message =
          err instanceof Error ? err.message : "Failed to load permissions";
        setContextError(message);
        addToast(message, "error");
      });
  }, [addToast]);

  useEffect(() => {
    if (!liveStream) {
      setStreamConnected(false);
      return undefined;
    }

    const disconnect = subscribeStateStream(
      (snapshot) => {
        setStreamConnected(true);
        if (streamToastState.current !== "connected") {
          addToast("Console stream connected", "success");
          streamToastState.current = "connected";
        }
        if (snapshot.telemetry) {
          setLoadState(snapshot.telemetry.load_state ?? "--");
        }
        const contexts = Array.from(
          new Set(snapshot.telemetry?.context_flags ?? [])
        );
        if (contexts.length) {
          setContextOptions((previous) => mergeUnique(previous, contexts));
        }
        setLiveContextFlags(contexts);
        const apps = Array.from(
          new Set(snapshot.telemetry?.running_apps ?? [])
        );
        setActiveApps(apps);
        if (apps.length) {
          setRunningApps((previous) => mergeUnique(previous, apps));
        }
        if (typeof snapshot.telemetry?.inactivity_gap_seconds === "number") {
          setInactivitySeconds(snapshot.telemetry.inactivity_gap_seconds);
        }

        if (streamTriggerRef.current) {
          return;
        }
        streamTriggerRef.current = setTimeout(() => {
          loadData();
          streamTriggerRef.current = null;
        }, 1200);
      },
      () => {
        setStreamConnected(false);
        if (streamToastState.current !== "disconnected") {
          addToast("Console stream disconnected", "error");
          streamToastState.current = "disconnected";
        }
      }
    );

    return () => {
      disconnect();
      if (streamTriggerRef.current) {
        clearTimeout(streamTriggerRef.current);
        streamTriggerRef.current = null;
      }
    };
  }, [liveStream, loadData, addToast]);

  useEffect(() => {
    if (liveStream) {
      return undefined;
    }
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [liveStream, loadData]);

  useEffect(() => {
    setEventFilters((previous) => ({
      ...previous,
      search: searchQuery || undefined,
    }));
  }, [searchQuery]);

  useEffect(() => {
    if (contextBlocklist.length === 0) {
      return;
    }
    setContextOptions((previous) => {
      const next = new Set(previous);
      contextBlocklist.forEach((entry) => next.add(entry));
      return Array.from(next);
    });
  }, [contextBlocklist]);

  const latestResidual = metrics.find(
    (metric) => metric.metric_type === "residual_rms"
  );
  const latestSuppression = metrics.find(
    (metric) => metric.metric_type === "ema_suppression"
  );

  const residualHistory = useMemo(
    () => buildHistoricalSeries(metrics, "residual_rms"),
    [metrics]
  );
  const suppressionHistory = useMemo(
    () => buildHistoricalSeries(metrics, "ema_suppression"),
    [metrics]
  );

  const consentColumns = useMemo<ColumnDef<ConsentEntry>[]>(
    () => [
      {
        key: "timestamp",
        title: "Timestamp",
        render: (value: string) => formatTimestamp(value),
      },
      {
        key: "granted",
        title: "Status",
        render: (value: boolean) => (
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              value
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-rose-500/15 text-rose-300"
            }`}
          >
            {value ? "Granted" : "Revoked"}
          </span>
        ),
      },
      {
        key: "reason",
        title: "Reason",
        render: (value: string | null) => value || "n/a",
      },
    ],
    []
  );

  const filteredLogs = useMemo(() => {
    if (!searchQuery) return metrics;
    return metrics.filter((metric) =>
      JSON.stringify(metric).toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [metrics, searchQuery]);

  const workspaceChips = mergeUnique(contextOptions, contextBlocklist);
  const applicationChips = mergeUnique(runningApps, contextBlocklist);
  const cognitiveStateLabel = loadState || "--";
  const normalizedLoadState = cognitiveStateLabel.toLowerCase();
  const cognitiveCardStatus: "normal" | "warning" | "critical" =
    normalizedLoadState.includes("high")
      ? "critical"
      : normalizedLoadState.includes("medium")
      ? "warning"
      : "normal";

  const renderContextChip = (flag: string) => (
    <label
      key={`context-chip-${flag}`}
      className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] transition ${
        contextBlocklist.includes(flag)
          ? "border-cyan-400/70 bg-cyan-500/10 text-cyan-100"
          : "border-slate-700 text-slate-300 hover:border-cyan-400/40"
      }`}
    >
      <input
        type="checkbox"
        className={`${styles.chipCheckbox} rounded border-slate-700 text-cyan-500 focus:ring-cyan-500`}
        checked={contextBlocklist.includes(flag)}
        onChange={(event) => handleContextToggle(flag, event.target.checked)}
      />
      <span>{flag}</span>
    </label>
  );

  const handleContextToggle = (value: string, enabled: boolean) => {
    setContextSaving(true);
    const next = enabled
      ? Array.from(new Set([...contextBlocklist, value]))
      : contextBlocklist.filter((entry) => entry !== value);
    setContextBlocklist(next);
    updateContextBlocklist(next)
      .then((status) => {
        setContextBlocklist(status.context_blocklist ?? []);
        setContextError(null);
        addToast("Context guard updated", "success");
      })
      .catch((err) => {
        const message =
          err instanceof Error ? err.message : "Failed to update context guard";
        setContextError(message);
        addToast(message, "error");
      })
      .finally(() => setContextSaving(false));
  };

  const exportData = () => {
    const bundle = {
      policyEvents,
      consentEntries,
      metrics,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `telemetry-console-${
      new Date().toISOString().split("T")[0]
    }.json`;
    link.click();
    URL.revokeObjectURL(url);
    addToast("Console data exported", "success");
  };

  return (
    <main className={styles.page}>
      <div className={styles.gradient} />
      <div className={`${styles.container} container-wide`}>
        <div className={styles.shell}>
          <header className={styles.header}>
            <div className={styles.headerPrimary}>
              <div>
                <p className={styles.eyebrow}>
                  On-device policy · workspace overview
                </p>
                <h1 className={styles.heroTitle}>Local Telemetry Console</h1>
                <p className="mt-2 text-sm text-slate-400">
                  Live diagnostics streaming from the estimator runtime with
                  adaptive policy instrumentation.
                </p>
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  onClick={() => loadData(true)}
                  disabled={loading}
                  className="w-full rounded-full bg-cyan-600 px-6 py-3 text-fluid-sm font-semibold text-white transition hover:bg-cyan-500 disabled:opacity-50 focus-ring sm:w-auto"
                >
                  {loading ? "Refreshing..." : "Refresh data"}
                </button>
                <button
                  type="button"
                  onClick={exportData}
                  className="w-full rounded-full border border-slate-700/60 px-6 py-3 text-fluid-sm font-semibold text-secondary hover:bg-slate-800/40 focus-ring sm:w-auto"
                >
                  Export JSON
                </button>
                <Link
                  href="/settings"
                  className="w-full rounded-full border border-slate-700/60 px-6 py-3 text-center text-fluid-sm font-semibold text-secondary hover:bg-slate-800/40 focus-ring sm:w-auto"
                >
                  Open settings
                </Link>
              </div>
            </div>
            <div className={styles.headerStats}>
              <div className={styles.statusCard}>
                <span className="text-fluid-xs uppercase tracking-wide text-muted font-semibold">
                  Stream
                </span>
                <div className="mt-2 flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      liveStream
                        ? streamConnected
                          ? "bg-emerald-400"
                          : "bg-amber-400"
                        : "bg-slate-600"
                    } animate-pulse`}
                  />
                  <span className="text-fluid-sm text-primary">
                    {liveStream
                      ? streamConnected
                        ? "SSE connected"
                        : "Connecting…"
                      : "Stream paused"}
                  </span>
                </div>
                <p className="mt-2 text-fluid-xs text-muted">
                  Last update:{" "}
                  {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
                </p>
              </div>
              <div className={styles.statusCard}>
                <span className="text-fluid-xs uppercase tracking-wide text-muted font-semibold">
                  Data window
                </span>
                <p className="mt-2 text-fluid-sm font-semibold text-primary">
                  {policyEvents.length}/{policyTotal} policy ·{" "}
                  {consentEntries.length}/{consentTotal} consent
                </p>
                <p className="text-fluid-xs text-muted">
                  Telemetry samples: {metrics.length}/{metricTotal}
                </p>
              </div>
              <div className={styles.statusCard}>
                <span className="text-fluid-xs uppercase tracking-wide text-muted font-semibold">
                  API endpoint
                </span>
                <p className="mt-2 text-fluid-sm font-semibold text-info">
                  {API_BASE_URL}
                </p>
                <p className="text-fluid-xs text-muted">
                  Console ↔ CLE microservice
                </p>
              </div>
            </div>
          </header>

          {error && <div className={styles.errorBanner}>{error}</div>}

          <div className={styles.layout}>
            <section className={styles.mainPanel}>
              <section className={styles.metrics}>
                <MetricCard
                  title="Cognitive state"
                  value={cognitiveStateLabel}
                  status={cognitiveCardStatus}
                  onClick={() => setActiveTab("metrics")}
                />
                <MetricCard
                  title="Policy events"
                  value={`${policyEvents.length}/${policyTotal}`}
                  status={policyEvents.length > 10 ? "warning" : "normal"}
                  onClick={() => setActiveTab("events")}
                />
                <MetricCard
                  title="Consent entries"
                  value={`${consentEntries.length}/${consentTotal}`}
                  status="normal"
                  onClick={() => setActiveTab("consent")}
                />
                <MetricCard
                  title="Latest residual RMS"
                  value={latestResidual?.metric_value?.toFixed(2) ?? "--"}
                  status={
                    latestResidual && latestResidual.metric_value
                      ? getStatusFromValue(latestResidual.metric_value, {
                          warning: 0.5,
                          critical: 0.8,
                        })
                      : "normal"
                  }
                  historicalData={residualHistory}
                  onClick={() => setActiveTab("metrics")}
                />
                <MetricCard
                  title="Latest suppression"
                  value={latestSuppression?.metric_value ?? "--"}
                  status="normal"
                  historicalData={suppressionHistory}
                  onClick={() => setActiveTab("metrics")}
                />
              </section>

              <TabNavigation
                activeTab={activeTab}
                tabs={tabs}
                onTabChange={setActiveTab}
              />

              <div className={styles.tabContent}>
                {activeTab === "overview" && (
                  <div className="grid gap-6 lg:grid-cols-2">
                    <SectionCard
                      title="Recent policy events"
                      action={
                        <span className="text-fluid-xs text-muted">
                          Showing {policyEvents.length} of {policyTotal}
                        </span>
                      }
                    >
                      <div className="h-80 overflow-y-auto">
                        <EventTimeline
                          events={policyEvents}
                          filters={eventFilters}
                        />
                      </div>
                    </SectionCard>
                    <SectionCard
                      title="Consent history"
                      action={
                        <span className="text-fluid-xs text-muted">
                          Showing {consentEntries.length} of {consentTotal}
                        </span>
                      }
                    >
                      <div className="h-80 overflow-y-auto">
                        <DataTable
                          data={consentEntries}
                          columns={consentColumns}
                          pagination={false}
                        />
                      </div>
                    </SectionCard>
                  </div>
                )}

                {activeTab === "events" && (
                  <SectionCard
                    title="Policy timeline"
                    action={
                      <select
                        value={eventFilters.eventType || ""}
                        onChange={(event) =>
                          setEventFilters((previous) => ({
                            ...previous,
                            eventType: event.target.value || undefined,
                          }))
                        }
                        className="rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-1 text-fluid-xs text-secondary focus:border-cyan-500/60 focus:outline-none focus-ring"
                      >
                        <option value="">All events</option>
                        {[
                          ...new Set(
                            policyEvents.map((event) => event.event_type)
                          ),
                        ].map((type) => (
                          <option key={type}>{type}</option>
                        ))}
                      </select>
                    }
                  >
                    <div className="h-80 overflow-y-auto">
                      <EventTimeline
                        events={policyEvents}
                        filters={eventFilters}
                      />
                    </div>
                  </SectionCard>
                )}

                {activeTab === "consent" && (
                  <ConsentAnalytics entries={consentEntries} />
                )}

                {activeTab === "metrics" && (
                  <SectionCard
                    title="Telemetry Explorer"
                    action={
                      <span className="text-fluid-xs text-muted">
                        Showing {metrics.length} of {metricTotal}
                      </span>
                    }
                  >
                    <MetricExplorer metrics={metrics} />
                  </SectionCard>
                )}

                {activeTab === "logs" && (
                  <SectionCard
                    title="Raw telemetry feed"
                    action={
                      <span className="text-fluid-xs text-muted">
                        Filtered results: {filteredLogs.length}
                      </span>
                    }
                  >
                    <div className={styles.logs}>
                      {filteredLogs.length === 0 ? (
                        <p className="text-fluid-base text-muted">
                          No metrics captured yet.
                        </p>
                      ) : (
                        filteredLogs.map((metric) => (
                          <div
                            key={`${metric.snapshot_at}-${metric.metric_type}-${metric.metric_value}`}
                            className="rounded-lg border border-slate-900/60 bg-slate-900/70 px-3 py-2 text-fluid-sm text-secondary"
                          >
                            {JSON.stringify(metric)}
                          </div>
                        ))
                      )}
                    </div>
                  </SectionCard>
                )}
              </div>
            </section>

            <aside className={styles.sidePanel}>
              <SectionCard title="Explorer filters">
                <div className="space-y-4">
                  <div>
                    <label className="text-fluid-xs uppercase text-muted font-semibold">
                      Keyword search
                    </label>
                    <input
                      className="mt-1 w-full rounded-lg border border-slate-800/60 bg-slate-950/40 px-3 py-2 text-fluid-sm text-secondary focus:border-cyan-500/60 focus:outline-none focus-ring"
                      placeholder="Search telemetry, metrics, logs..."
                      value={searchQuery}
                      onChange={(event) => setSearchQuery(event.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-900/60 px-3 py-2 text-fluid-xs text-secondary">
                    <span>Live stream (SSE)</span>
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={liveStream}
                        onChange={(event) =>
                          setLiveStream(event.target.checked)
                        }
                        className="h-4 w-4 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 focus-ring"
                      />
                      <span>{liveStream ? "Enabled" : "Paused"}</span>
                    </label>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-fluid-xs text-muted">
                    <div className="rounded-lg border border-slate-900/60 bg-slate-950/40 p-3">
                      <p>Policy events</p>
                      <p className="text-fluid-sm font-semibold text-primary">
                        {policyTotal}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-900/60 bg-slate-950/40 p-3">
                      <p>Consent records</p>
                      <p className="text-fluid-sm font-semibold text-primary">
                        {consentTotal}
                      </p>
                    </div>
                  </div>
                </div>
              </SectionCard>

              <SectionCard
                title="Context guard"
                action={
                  <span className="text-fluid-xs text-muted">
                    {contextSaving
                      ? "Saving..."
                      : `Blocking ${contextBlocklist.length} context${
                          contextBlocklist.length === 1 ? "" : "s"
                        }`}
                  </span>
                }
              >
                <p className="text-fluid-xs text-muted">
                  Choose which workspaces or applications pause EMA prompts.
                </p>
                <div className="mt-3 space-y-3">
                  <div>
                    <p className="text-fluid-xs uppercase tracking-wide text-muted font-semibold">
                      Workspaces
                    </p>
                    <div className="h-60 overflow-y-auto">
                      <div className={styles.chipGrid}>
                        {workspaceChips.length === 0 ? (
                          <span className="text-fluid-xs text-muted">
                            No contexts observed yet.
                          </span>
                        ) : (
                          workspaceChips.map((flag) => renderContextChip(flag))
                        )}
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-fluid-xs uppercase tracking-wide text-muted font-semibold">
                      Applications
                    </p>
                    <div className="h-60 overflow-y-auto">
                      <div className={styles.chipGrid}>
                        {applicationChips.length === 0 ? (
                          <span className="text-fluid-xs text-muted">
                            Waiting for local activity.
                          </span>
                        ) : (
                          applicationChips.map((flag) =>
                            renderContextChip(flag)
                          )
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                {contextError && (
                  <p className="mt-2 text-fluid-xs text-rose-400">
                    {contextError}
                  </p>
                )}
              </SectionCard>

              <SectionCard title="Live context">
                <div className={styles.liveContext}>
                  <div>
                    <span className="text-fluid-xs text-muted">Idle guard</span>
                    <p className="text-fluid-sm font-semibold text-primary">
                      {formatSecondsCompact(inactivitySeconds)} /{" "}
                      {formatSecondsCompact(idleBlockSeconds)}
                    </p>
                  </div>
                  <div>
                    <span className="text-fluid-xs text-muted">
                      Active contexts
                    </span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {liveContextFlags.length === 0 ? (
                        <span className="text-fluid-xs text-muted">None</span>
                      ) : (
                        liveContextFlags.map((flag) => (
                          <span
                            key={`live-${flag}`}
                            className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[11px] text-slate-200"
                          >
                            {flag}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                  <div>
                    <span className="text-fluid-xs text-muted">
                      Now running
                    </span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {(activeApps.length ? activeApps : applicationChips)
                        .slice(0, 5)
                        .map((app) => (
                          <span
                            key={`active-${app}`}
                            className="rounded-full border border-slate-800 px-2 py-0.5 text-[11px] text-slate-200"
                          >
                            {app}
                          </span>
                        ))}
                    </div>
                  </div>
                </div>
              </SectionCard>
            </aside>
          </div>

          <footer className={styles.statusBar}>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      liveStream
                        ? streamConnected
                          ? "bg-emerald-400"
                          : "bg-amber-400"
                        : "bg-slate-500"
                    } animate-pulse`}
                  />
                  {liveStream
                    ? streamConnected
                      ? "SSE connected"
                      : "Connecting to stream..."
                    : "Live stream disabled"}
                </span>
                <span>API: {API_BASE_URL}</span>
              </div>
              <div className="flex items-center gap-4">
                <span>
                  Updates: {liveStream ? "push (SSE)" : "poll every 30s"}
                </span>
                {lastUpdate && (
                  <span>Last update: {lastUpdate.toLocaleTimeString()}</span>
                )}
              </div>
            </div>
          </footer>
        </div>
      </div>
    </main>
  );
}
