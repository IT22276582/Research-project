"use client";

import { Tone } from "../../../lib/format";
import styles from "./Home.module.css";

type WorkspacePanelProps = {
  privacyPause?: boolean | null;
  consentGranted?: boolean | null;
  loadState: string;
  loadTone: Tone;
  contextFlags: string[];
};

const toneClassMap: Record<Tone, string> = {
  rose: styles.toneRose,
  amber: styles.toneAmber,
  emerald: styles.toneEmerald,
  cyan: styles.toneCyan,
  indigo: styles.toneIndigo,
  slate: styles.toneSlate,
};

export function WorkspacePanel({
  privacyPause,
  consentGranted,
  loadState,
  loadTone,
  contextFlags,
}: WorkspacePanelProps) {
  const loadToneClass = toneClassMap[loadTone] ?? styles.toneSlate;
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Workspace activity</h2>
      <p className={styles.sectionHint}>Snapshot of current inputs, context flags, and privacy posture.</p>

      <div className={styles.infoList}>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Privacy pause</span>
          <span className={styles.infoValue}>{privacyPause ? "ON" : "OFF"}</span>
        </div>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Consent</span>
          <span className={styles.infoValue}>
            {consentGranted ? "GRANTED" : "REVOKED"}
          </span>
        </div>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Cognitive state</span>
          <span className={`${styles.infoValue} ${loadToneClass}`}>{loadState}</span>
        </div>
      </div>

      <div className={styles.contextLog}>
        <p className={styles.overline}>Context log</p>
        <p className={styles.helper}>
          {contextFlags.length ? contextFlags.join(", ") : "Ambient signals look clear."}
        </p>
      </div>
    </div>
  );
}
