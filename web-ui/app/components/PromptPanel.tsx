"use client";

import { useState } from "react";
import { EstimateResponse, postEmaResponse } from "../../lib/api";
import styles from "./PromptPanel.module.css";

type Props = {
  estimate: EstimateResponse;
  onSubmit: (
    result:
      | { promptId: number; status: "completed" | "dismissed" | "timeout" | "snoozed" }
      | null
  ) => void;
  className?: string;
};

export function PromptPanel({ estimate, onSubmit, className = "" }: Props) {
  const prompt = estimate.pending_prompt;
  const [rating, setRating] = useState(4);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  if (!prompt) {
    return (
      <div className={`${styles.panel} ${className}`}>
        <div className={styles.placeholder}>
          No pending EMA prompt. You'll be notified when a new one arrives.
        </div>
      </div>
    );
  }

  const submit = async (disposition: "completed" | "dismissed" | "timeout" | "snoozed") => {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await postEmaResponse(prompt.prompt_id, rating, disposition, note || undefined);
      onSubmit({ promptId: prompt.prompt_id, status: disposition });
      setInfo(
        disposition === "completed"
          ? "Thanks! Your answer will adapt the model."
          : "Response recorded."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit response");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`${styles.panel} ${className}`}>
      <div className={styles.header}>
        <div>
          <div className={styles.promptLabel}>Prompt #{prompt.prompt_id}</div>
          <div className={styles.promptReason}>Reason: {prompt.reason}</div>
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>
          Rating (1-7) <span className={styles.labelHint}>(Likert)</span>
        </label>
        <input
          type="range"
          min={1}
          max={7}
          value={rating}
          disabled={busy}
          onChange={(e) => setRating(Number(e.target.value))}
          className={styles.range}
        />
        <div className={styles.helperText}>
          Selected: {rating} — lower = lighter load, higher = heavier load.
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Notes (optional)</label>
        <textarea
          value={note}
          disabled={busy}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          className={styles.textarea}
          placeholder="What were you doing? Any blockers?"
        />
      </div>

      {error && <div className={styles.error}>Error: {error}</div>}
      {info && !error && <div className={styles.info}>{info}</div>}

      <div className={styles.actions}>
        <button
          className={`${styles.button} ${styles.primary}`}
          disabled={busy}
          onClick={() => submit("completed")}
        >
          {busy ? "Submitting..." : "Submit"}
        </button>
        <button
          className={`${styles.button} ${styles.warn}`}
          disabled={busy}
          onClick={() => submit("dismissed")}
        >
          Dismiss
        </button>
        <button
          className={`${styles.button} ${styles.infoButton}`}
          disabled={busy}
          onClick={() => submit("snoozed")}
        >
          Snooze 5 min
        </button>
        <button
          className={`${styles.button} ${styles.muted}`}
          disabled={busy}
          onClick={() => submit("timeout")}
        >
          Timeout
        </button>
      </div>
    </div>
  );
}
