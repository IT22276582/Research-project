"use client";

import { useMemo } from "react";
import { Sparkline } from "../Sparkline";
import { HistoryPoint } from "../../hooks/useEstimatorStream";
import { StatusChip } from "./StatusChip";
import styles from "./Home.module.css";

type VisualizationPanelProps = {
  history: HistoryPoint[];
};

export function VisualizationPanel({ history }: VisualizationPanelProps) {
  const loadPoints = useMemo(() => {
    return [...history]
      .sort((a, b) => a.t - b.t)
      .map((p) => ({ x: p.t, y: p.load }));
  }, [history]);

  const residualPoints = useMemo(() => {
    return [...history]
      .sort((a, b) => a.t - b.t)
      .map((p) => ({ x: p.t, y: p.residual }));
  }, [history]);
  const latest = history[history.length - 1];

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.overline}>Live visualization</p>
          <p className={styles.sectionHint}>
            {history.length
              ? "Rolling history for load and residuals."
              : "Charts will appear once telemetry arrives."}
          </p>
        </div>
        {latest && (
          <StatusChip
            label={`Hop ${new Date(latest.t).toLocaleTimeString()}`}
            tone="slate"
          />
        )}
      </div>

      {history.length === 0 ? (
        <div className={styles.emptyState}>
          No samples yet. Interact with your keyboard and mouse to populate the stream.
        </div>
      ) : (
        <div className={styles.sparklineGrid}>
          <Sparkline
            points={loadPoints}
            label="Load"
            value={latest ? latest.load.toFixed(2) : "Waiting for first estimate..."}
            color="#22d3ee"
          />
          <Sparkline
            points={residualPoints}
            label="Residual"
            value={latest ? latest.residual.toFixed(3) : "Waiting for first estimate..."}
            color="#f97316"
          />
        </div>
      )}
    </div>
  );
}
