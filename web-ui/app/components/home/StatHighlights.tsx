"use client";

import { Tone } from "../../../lib/format";
import { Surface } from "../Surface";
import styles from "./Home.module.css";

export type StatCardView = {
  id: string;
  label: string;
  value: string;
  hint: string;
  tone: Tone;
  variant?: "compact";
};

const toneClassMap: Record<Tone, string> = {
  rose: styles.toneRose,
  amber: styles.toneAmber,
  emerald: styles.toneEmerald,
  cyan: styles.toneCyan,
  indigo: styles.toneIndigo,
  slate: styles.toneSlate,
};

export function StatHighlights({ cards }: { cards: StatCardView[] }) {
  return (
    <div className={styles.statGrid}>
      {cards.map((card) => {
        const toneClass = toneClassMap[card.tone] ?? styles.toneSlate;
        const variantClass =
          card.variant === "compact" ? styles.statCardCompact : "";
        return (
          <Surface
            key={card.id}
            padding="sm"
            className={`${styles.statCard} ${variantClass}`}
          >
            <p className={styles.statLabel}>{card.label}</p>
            <p className={`${styles.statValue} ${toneClass}`}>{card.value}</p>
            <p className={styles.statHint}>{card.hint}</p>
          </Surface>
        );
      })}
    </div>
  );
}
