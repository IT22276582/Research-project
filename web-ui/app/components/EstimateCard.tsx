import { EstimateResponse } from "../../lib/api";
import styles from "./EstimateCard.module.css";

function formatNumber(value: number, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

export function EstimateCard({ estimate }: { estimate: EstimateResponse }) {
  const contextValues = Object.values(estimate.context_flags ?? {});
  const loadState = estimate.load_state ?? "unknown cognitive load";
  const loadStateClasses = getLoadStateClasses(loadState);

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div>
          <div className={styles.metaLabel}>Hop #{estimate.hop_index}</div>
          <div className={styles.metricValue}>
            Load: {formatNumber(estimate.load, 2)}
          </div>
          <p className={styles.metaSub}>
            State: <span className={`${styles.loadChip} ${loadStateClasses}`}>{loadState}</span>
          </p>
        </div>
        <span className={styles.modePill}>
          {estimate.baseline_active ? "Baseline" : "Active"}
        </span>
      </div>

      <dl className={styles.metrics}>
        <div>
          <dt className={styles.metricLabel}>Variance</dt>
          <dd className={styles.metricData}>{formatNumber(estimate.variance, 4)}</dd>
        </div>
        <div>
          <dt className={styles.metricLabel}>95% CI</dt>
          <dd className={styles.metricData}>{formatNumber(estimate.ci95, 3)}</dd>
        </div>
        <div>
          <dt className={styles.metricLabel}>Residual</dt>
          <dd className={styles.metricData}>{formatNumber(estimate.residual, 3)}</dd>
        </div>
        <div>
          <dt className={styles.metricLabel}>Quality</dt>
          <dd className={styles.metricData}>{formatNumber(estimate.quality, 2)}</dd>
        </div>
      </dl>

      <div className={styles.meta}>
        <div>Scheduler: {estimate.scheduler_state}</div>
        <div>
          Context: {contextValues.length ? contextValues.join(", ") : "no active flags"}
        </div>
      </div>
      <div className={styles.timestamp}>
        Timestamp: {new Date(estimate.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

function getLoadStateClasses(state: string) {
  const normalized = state.toLowerCase();
  if (normalized.includes("high")) {
    return styles.loadHigh;
  }
  if (normalized.includes("medium")) {
    return styles.loadMedium;
  }
  if (normalized.includes("low")) {
    return styles.loadLow;
  }
  return styles.loadNeutral;
}
