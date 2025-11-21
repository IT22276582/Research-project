"use client";

import { useMemo } from "react";
import { ConsentEntry } from "../../../lib/api";
import { DataTable } from "./DataTable";
import { MetricCard } from "./MetricCard";
import styles from "./ConsentAnalytics.module.css";
import { calculateTrend, calculateTrendPercentage } from "../utils";

interface ConsentAnalyticsProps {
  entries: ConsentEntry[];
}

export function ConsentAnalytics({ entries }: ConsentAnalyticsProps) {
  const stats = useMemo(() => {
    const granted = entries.filter((entry) => entry.granted).length;
    const revoked = entries.length - granted;
    const grantedPercentage = entries.length ? (granted / entries.length) * 100 : 0;
    const recent = entries.slice(-5);
    const recentGranted = recent.filter((entry) => entry.granted).length || 0;
    const trend = calculateTrend(recentGranted, recent.length - recentGranted);
    const trendPct = calculateTrendPercentage(recentGranted, recent.length || 1);

    return {
      granted,
      revoked,
      total: entries.length,
      grantedPercentage,
      trend,
      trendPct,
    };
  }, [entries]);

  return (
    <div className={styles.wrapper}>
      <div className={styles.summaryGrid}>
        <MetricCard title="Total consents" value={stats.total} status="normal" />
        <MetricCard
          title="Granted percentage"
          value={`${stats.grantedPercentage.toFixed(1)}%`}
          trend={stats.trend}
          trendPercentage={stats.trendPct}
          status={stats.grantedPercentage > 70 ? "normal" : stats.grantedPercentage > 40 ? "warning" : "critical"}
        />
        <MetricCard title="Revoked" value={stats.revoked} status="warning" />
      </div>
      <DataTable
        data={entries}
        columns={[
          {
            key: "timestamp",
            title: "Timestamp",
            render: (value) => new Date(value as string).toLocaleString(),
          },
          {
            key: "granted",
            title: "Status",
            render: (value: boolean) => (
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  value ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"
                }`}
              >
                {value ? "Granted" : "Revoked"}
              </span>
            ),
          },
          {
            key: "reason",
            title: "Reason",
            render: (value) => value || "n/a",
          },
        ]}
        filterable
        sortable
        pagination
      />
    </div>
  );
}
