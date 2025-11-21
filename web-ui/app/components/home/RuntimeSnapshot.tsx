"use client";

import { formatSeconds, Tone } from "../../../lib/format";
import styles from "./Home.module.css";
import { StatusChip } from "./StatusChip";

type RuntimeSnapshotProps = {
  schedulerState: string;
  loadState: string;
  loadTone: Tone;
  cooldownSeconds?: number | null;
  snoozeSeconds?: number | null;
  nextPromptSeconds?: number | null;
  policyPrompted?: number | null;
  policySuppressed?: number | null;
  contextFlags: string[];
};

export function RuntimeSnapshot({
  schedulerState,
  loadState,
  loadTone,
  cooldownSeconds,
  snoozeSeconds,
  nextPromptSeconds,
  policyPrompted,
  policySuppressed,
  contextFlags,
}: RuntimeSnapshotProps) {
  const contextPreview = contextFlags.slice(0, 3);
  const extraContexts = Math.max(0, contextFlags.length - contextPreview.length);

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Runtime snapshot</h2>
          <p className={styles.sectionHint}>Live context, cooldowns, and policy counters.</p>
        </div>
        <div className={styles.chipRow}>
          <StatusChip label={schedulerState} tone="cyan" />
          <StatusChip label={loadState} tone={loadTone} />
        </div>
      </div>

      <div className={styles.runtimeGrid}>
        <div className={styles.runtimeItem}>
          <p className={styles.overline}>Cooldown</p>
          <p className={styles.runtimeValue}>{formatSeconds(cooldownSeconds)}</p>
          <p className={styles.helper}>Snooze {formatSeconds(snoozeSeconds)}</p>
        </div>
        <div className={styles.runtimeItem}>
          <p className={styles.overline}>Next prompt</p>
          <p className={styles.runtimeValue}>{formatSeconds(nextPromptSeconds)}</p>
          <p className={styles.helper}>
            Policy counters: {policyPrompted ?? "--"} prompted - {policySuppressed ?? "--"} suppressed
          </p>
        </div>
      </div>

      <div className={styles.contextPanel}>
        <p className={styles.overline}>Active contexts</p>
        <div className={styles.contextList}>
          {contextPreview.length ? (
            contextPreview.map((flag) => (
              <span key={flag} className={styles.contextChip}>
                {flag}
              </span>
            ))
          ) : (
            <span className={styles.helper}>No suppressors detected</span>
          )}
          {extraContexts > 0 && (
            <span className={styles.contextChip}>+{extraContexts} more</span>
          )}
        </div>
      </div>
    </div>
  );
}
