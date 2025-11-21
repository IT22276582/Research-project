"use client";

import styles from "./MetricCard.module.css";
import { MetricCardProps } from "../types";

const statusClasses: Record<NonNullable<MetricCardProps["status"]>, string> = {
  normal: "border-emerald-500/40 bg-emerald-500/5",
  warning: "border-amber-500/40 bg-amber-500/5",
  critical: "border-rose-500/40 bg-rose-500/5",
};

const trendColors: Record<NonNullable<MetricCardProps["trend"]>, string> = {
  up: "text-emerald-400",
  down: "text-rose-400",
  stable: "text-slate-400",
};

const trendIcons: Record<NonNullable<MetricCardProps["trend"]>, string> = {
  up: "▲",
  down: "▼",
  stable: "–",
};

export function MetricCard({
  title,
  value,
  trend,
  trendPercentage,
  historicalData = [],
  status = "normal",
  onClick,
}: MetricCardProps) {
  return (
    <button type="button" onClick={onClick} className={`${styles.card} ${statusClasses[status]}`}>
      <div className={styles.overlay} />
      <div className={styles.content}>
        <p className={styles.title}>{title}</p>
        <p className={styles.value}>{value}</p>
        {trend && trendPercentage !== undefined && (
          <div className={`${styles.trend} ${trendColors[trend]}`}>
            <span>{trendIcons[trend]}</span>
            <span>{Math.abs(trendPercentage).toFixed(1)}%</span>
          </div>
        )}
        {historicalData.length > 0 && (
          <div className={styles.sparkline}>
            <svg className="h-full w-full text-cyan-400" viewBox="0 0 100 30" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                points={historicalData
                  .slice(-10)
                  .map((point, index) => {
                    const x = (index / (historicalData.length - 1 || 1)) * 100;
                    const values = historicalData.map((d) => d.value);
                    const maxValue = Math.max(...values);
                    const minValue = Math.min(...values);
                    const range = maxValue - minValue || 1;
                    const y = 30 - ((point.value - minValue) / range) * 25;
                    return `${x},${y}`;
                  })
                  .join(" ")}
              />
            </svg>
          </div>
        )}
      </div>
    </button>
  );
}
