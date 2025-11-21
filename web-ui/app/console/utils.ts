import { TelemetryMetric } from "../../lib/api";

export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString();
};

export const calculateTrend = (current: number, previous: number): "up" | "down" | "stable" => {
  if (current > previous * 1.05) return "up";
  if (current < previous * 0.95) return "down";
  return "stable";
};

export const calculateTrendPercentage = (current: number, previous: number): number => {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
};

export const getStatusFromValue = (
  value: number,
  thresholds: { warning: number; critical: number },
): "normal" | "warning" | "critical" => {
  if (value >= thresholds.critical) return "critical";
  if (value >= thresholds.warning) return "warning";
  return "normal";
};

export const buildHistoricalSeries = (metrics: TelemetryMetric[], metricType: string) => {
  return metrics
    .filter((m) => m.metric_type === metricType && m.metric_value !== null)
    .slice(-10)
    .map((m) => ({
      timestamp: new Date(m.snapshot_at),
      value: m.metric_value as number,
    }));
};
