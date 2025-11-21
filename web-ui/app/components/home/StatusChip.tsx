"use client";

import { Tone } from "../../../lib/format";
import styles from "./Home.module.css";

type StatusChipProps = {
  label: string;
  tone?: Tone;
};

const toneClassMap: Record<Tone, string> = {
  rose: styles.toneRose,
  amber: styles.toneAmber,
  emerald: styles.toneEmerald,
  cyan: styles.toneCyan,
  indigo: styles.toneIndigo,
  slate: styles.toneSlate,
};

export function StatusChip({ label, tone = "slate" }: StatusChipProps) {
  const toneClass = toneClassMap[tone] ?? "";
  return <span className={`${styles.statusChip} ${toneClass}`}>{label}</span>;
}
