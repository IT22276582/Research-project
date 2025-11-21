"use client";

import Link from "next/link";
import styles from "./Home.module.css";

type HomeHeaderProps = {
  status: string;
  streamHealthy: boolean;
  baselineLabel: string;
  hopLabel: string;
  pendingReason: string;
};

export function HomeHeader({
  status,
  streamHealthy,
  baselineLabel,
  hopLabel,
  pendingReason,
}: HomeHeaderProps) {
  return (
    <div className={styles.hero}>
      <div className={styles.heroText}>
        <p className={styles.eyebrow}>Cognitive load estimator</p>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Realtime telemetry for your workspace</h1>
          <span
            className={`${styles.statusPill} ${
              streamHealthy ? styles.statusOnline : styles.statusOffline
            }`}
          >
            <span className={styles.statusIndicator} />
            {status}
          </span>
        </div>
        <p className={styles.subhead}>
          Observe estimator health, suppression causes, and respond to EMA without scrolling.
        </p>
      </div>
      <div className={styles.heroActions}>
        <div className={styles.actionRow}>
          <Link href="/console" className={styles.primaryAction}>
            Open console
          </Link>
          <Link href="/settings" className={styles.secondaryAction}>
            Settings
          </Link>
        </div>
        <div className={styles.metaChips}>
          <span className={styles.metaChip}>{hopLabel}</span>
          <span className={styles.metaChip}>{baselineLabel}</span>
          <span className={styles.metaChip}>Pending {pendingReason}</span>
        </div>
      </div>
    </div>
  );
}
