"use client";

import styles from "./Home.module.css";

type AlertTone = "error" | "warning" | "info";

type AlertBannerProps = {
  title: string;
  message: string;
  tone?: AlertTone;
};

export function AlertBanner({ title, message, tone = "info" }: AlertBannerProps) {
  const toneClass =
    tone === "error"
      ? styles.alertError
      : tone === "warning"
      ? styles.alertWarning
      : styles.alertInfo;

  return (
    <div className={`${styles.alert} ${toneClass}`}>
      <div className={styles.alertTitle}>{title}</div>
      <div className={styles.alertMessage}>{message}</div>
    </div>
  );
}
