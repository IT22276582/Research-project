"use client";

import { useMemo, useState } from "react";
import { TelemetryMetric } from "../../../lib/api";
import { MetricCard } from "./MetricCard";
import styles from "./MetricExplorer.module.css";
import { calculateTrend, calculateTrendPercentage } from "../utils";

interface MetricExplorerProps {
  metrics: TelemetryMetric[];
}

export function MetricExplorer({ metrics }: MetricExplorerProps) {
  const [viewMode, setViewMode] = useState<"structured" | "raw" | "visualized">("structured");
  const [selectedMetricType, setSelectedMetricType] = useState<string>("");

  const metricTypes = useMemo(() => {
    const types = new Set(metrics.map((metric) => metric.metric_type).filter(Boolean) as string[]);
    return Array.from(types);
  }, [metrics]);

  const metricsByType = useMemo(() => {
    return metricTypes.reduce<Record<string, TelemetryMetric[]>>((acc, type) => {
      acc[type] = metrics.filter((metric) => metric.metric_type === type);
      return acc;
    }, {});
  }, [metrics, metricTypes]);

  const filteredTypes = selectedMetricType ? [selectedMetricType] : metricTypes;

  const metricStats = filteredTypes.map((type) => {
    const typeMetrics = metricsByType[type] ?? [];
    const values = typeMetrics.filter((m) => typeof m.metric_value === "number") as TelemetryMetric[];
    const latest = values.at(-1)?.metric_value as number | undefined;
    const previous = values.length > 1 ? (values.at(-2)?.metric_value as number) : latest ?? 0;
    const trend = latest !== undefined ? calculateTrend(latest, previous || 0) : "stable";
    const trendPct = latest !== undefined ? calculateTrendPercentage(latest, previous || 0) : 0;
    return {
      type,
      latest: latest ?? "--",
      trend,
      trendPct,
      historical: values.map((metric) => ({
        timestamp: new Date(metric.snapshot_at),
        value: metric.metric_value as number,
      })),
    };
  });

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        <div className="flex gap-2">
          {(["structured", "visualized", "raw"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setViewMode(mode)}
              className={`${styles.viewButton} ${viewMode === mode ? styles.viewButtonActive : ""}`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
        <select
          className={styles.select}
          value={selectedMetricType}
          onChange={(event) => setSelectedMetricType(event.target.value)}
        >
          <option value="">All metric types</option>
          {metricTypes.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </div>

      {viewMode === "raw" && (
        <div className={styles.rawList}>
          {metrics.length === 0 ? (
            <p className="text-slate-500">No metrics captured yet.</p>
          ) : (
            metrics
              .filter((metric) => !selectedMetricType || metric.metric_type === selectedMetricType)
              .map((metric) => (
                <div
                  key={`${metric.snapshot_at}-${metric.metric_type}-${metric.metric_value}`}
                  className="rounded-lg border border-slate-900/60 bg-slate-900/70 px-3 py-2"
                >
                  {JSON.stringify(metric)}
                </div>
              ))
          )}
        </div>
      )}

      {viewMode === "structured" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {metricStats.map((stat) => (
            <MetricCard
              key={stat.type}
              title={stat.type}
              value={typeof stat.latest === "number" ? stat.latest.toFixed(2) : stat.latest}
              trend={stat.trend}
              trendPercentage={stat.trendPct}
              historicalData={stat.historical}
            />
          ))}
        </div>
      )}

      {viewMode === "visualized" && (
        <div className={styles.structuredGrid}>
          {metricStats.map((stat) => (
            <div key={stat.type} className={styles.statCard}>
              <p className={styles.statTitle}>{stat.type}</p>
              <p className={styles.statValue}>
                {typeof stat.latest === "number" ? stat.latest.toFixed(2) : stat.latest}
              </p>
              <svg className="mt-4 h-32 w-full text-cyan-400" viewBox="0 0 120 60" preserveAspectRatio="none">
                <polyline
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  points={stat.historical
                    .map((point, index) => {
                      const x = (index / (stat.historical.length - 1 || 1)) * 120;
                      const values = stat.historical.map((d) => d.value);
                      const max = Math.max(...values, 1);
                      const min = Math.min(...values, 0);
                      const range = max - min || 1;
                      const y = 60 - ((point.value - min) / range) * 50;
                      return `${x},${y}`;
                    })
                    .join(" ")}
                />
              </svg>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
