"use client";

import Link from "next/link";
import styles from "./Home.module.css";

export function NavigationPanel() {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Navigation</h2>
      <p className={styles.sectionHint}>Dive deeper into the console or refine guard rails.</p>
      <div className={styles.navGrid}>
        <Link href="/console" className={`${styles.navLink} ${styles.navPrimary}`}>
          <div className={styles.navTitle}>Telemetry console</div>
          <p className={styles.navSubtitle}>NDJSON metrics, policy logs, and advanced analytics.</p>
        </Link>
        <Link href="/settings" className={styles.navLink}>
          <div className={styles.navTitle}>Permissions &amp; settings</div>
          <p className={styles.navSubtitle}>Manage context guard, idle rules, and privacy pause.</p>
        </Link>
      </div>
    </div>
  );
}
