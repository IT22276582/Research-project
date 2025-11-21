"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useToasts } from "../components/ToastProvider";
import {
  PermissionsStatus,
  fetchPermissions,
  subscribeStateStream,
  updateConsent,
  updateContextBlocklist,
  updateIdleBlock,
  updatePrivacy,
} from "../../lib/api";
import styles from "./page.module.css";

function uniqueMerge(current: string[], incoming: string[]) {
  const next = new Set(current);
  incoming.forEach((entry) => {
    if (entry) {
      next.add(entry);
    }
  });
  return Array.from(next);
}

function secondsToTimeInput(seconds: number): string {
  const safe = Math.max(0, Math.min(86399, seconds));
  const hours = Math.floor(safe / 3600)
    .toString()
    .padStart(2, "0");
  const minutes = Math.floor((safe % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const secs = Math.floor(safe % 60)
    .toString()
    .padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

function timeInputToSeconds(value: string): number {
  if (!value) return 0;
  const parts = value.split(":").map((part) => Number(part));
  if (parts.some((part) => Number.isNaN(part))) {
    return 0;
  }
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  if (parts.length === 2) {
    return parts[0] * 3600 + parts[1] * 60;
  }
  return 0;
}

function describeDuration(seconds: number): string {
  if (seconds === 0) return "Immediate";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) {
    return `${seconds}s`;
  }
  if (minutes < 60) {
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  }
  const hours = (seconds / 3600).toFixed(1);
  return `${hours.replace(/\\.0$/, "")} hours`;
}

export default function SettingsPage() {
  const { addToast } = useToasts();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [privacyPause, setPrivacyPause] = useState(false);
  const [consentGranted, setConsentGranted] = useState(true);
  const [contextBlocklist, setContextBlocklist] = useState<string[]>([]);
  const [contextOptions, setContextOptions] = useState<string[]>([]);
  const [applicationOptions, setApplicationOptions] = useState<string[]>([]);
  const [contextSaving, setContextSaving] = useState(false);
  const [newContext, setNewContext] = useState("");
  const [idleBlockSeconds, setIdleBlockSeconds] = useState(900);
  const [idleSaving, setIdleSaving] = useState(false);

  useEffect(() => {
    fetchPermissions()
      .then((state) => {
        applyPermissionsState(state);
        setLoading(false);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Failed to load permissions";
        setError(message);
        addToast(message, "error");
        setLoading(false);
      });
  }, [addToast]);

  useEffect(() => {
    const disconnect = subscribeStateStream((snapshot) => {
      const contexts = snapshot.telemetry?.context_flags ?? [];
      if (contexts.length) {
        setContextOptions((prev) => uniqueMerge(prev, contexts));
      }
      const runningApps = snapshot.telemetry?.running_apps ?? [];
      if (runningApps.length) {
        setApplicationOptions((prev) => uniqueMerge(prev, runningApps));
      }
    });
    return () => disconnect();
  }, []);

  const applyPermissionsState = (state: PermissionsStatus) => {
    setPrivacyPause(state.privacy_pause);
    setConsentGranted(state.consent_granted);
    setContextBlocklist(state.context_blocklist ?? []);
    setContextOptions((prev) => uniqueMerge(prev, state.context_blocklist ?? []));
    setApplicationOptions((prev) =>
      uniqueMerge(prev, [...(state.context_catalog ?? []), ...(state.context_blocklist ?? [])]),
    );
    if (typeof state.idle_block_seconds === "number") {
      setIdleBlockSeconds(state.idle_block_seconds);
    }
  };

  const togglePrivacy = async () => {
    try {
      const next = !privacyPause;
      setPrivacyPause(next);
      await updatePrivacy(next);
      addToast(next ? "Privacy pause enabled" : "Privacy pause disabled", "success");
    } catch (err) {
      setPrivacyPause(privacyPause);
      const message = err instanceof Error ? err.message : "Failed to toggle privacy pause";
      setError(message);
      addToast(message, "error");
    }
  };

  const toggleConsent = async () => {
    try {
      const next = !consentGranted;
      setConsentGranted(next);
      await updateConsent(next);
      addToast(next ? "Consent granted" : "Consent revoked", "success");
    } catch (err) {
      setConsentGranted(consentGranted);
      const message = err instanceof Error ? err.message : "Failed to toggle consent";
      setError(message);
      addToast(message, "error");
    }
  };

  const persistContextList = async (list: string[]) => {
    setContextSaving(true);
    try {
      const state = await updateContextBlocklist(list);
      applyPermissionsState(state);
      setError(null);
      addToast("Context guard updated", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update context guard";
      setError(message);
      addToast(message, "error");
    } finally {
      setContextSaving(false);
    }
  };

  const handleContextToggle = (value: string, enabled: boolean) => {
    const next = enabled
      ? uniqueMerge(contextBlocklist, [value])
      : contextBlocklist.filter((entry) => entry !== value);
    setContextBlocklist(next);
    persistContextList(next);
  };

  const handleAddContext = () => {
    const trimmed = newContext.trim();
    if (!trimmed) return;
    if (contextBlocklist.includes(trimmed)) {
      setNewContext("");
      return;
    }
    const next = [...contextBlocklist, trimmed];
    setContextBlocklist(next);
    setContextOptions(uniqueMerge(contextOptions, [trimmed]));
    setApplicationOptions(uniqueMerge(applicationOptions, [trimmed]));
    setNewContext("");
    persistContextList(next);
  };

  const handleIdlePickerChange = (value: string) => {
    const seconds = Math.max(0, Math.min(86399, timeInputToSeconds(value)));
    setIdleBlockSeconds(seconds);
  };

  const persistIdleBlock = async () => {
    setIdleSaving(true);
    try {
      const state = await updateIdleBlock(idleBlockSeconds);
      applyPermissionsState(state);
      setError(null);
      addToast("Idle guard updated", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update idle guard";
      setError(message);
      addToast(message, "error");
    } finally {
      setIdleSaving(false);
    }
  };

  const workspaceChips = uniqueMerge(contextOptions, contextBlocklist);
  const applicationChips = uniqueMerge(applicationOptions, contextBlocklist);

  return (
    <main className={styles.settingsPage}>
      <div className={styles.settingsContainer}>
        <header className={styles.settingsHeader}>
          <div>
            <h1 className="text-fluid-3xl font-bold text-primary">Local telemetry settings</h1>
            <p className="mt-2 text-fluid-lg text-secondary leading-relaxed">
              Configure privacy pause, consent, and context-aware suppression rules.
            </p>
          </div>
          <div className={styles.buttonGroup}>
            <Link
              href="/"
              className="rounded-full border border-slate-700/60 px-4 py-2 text-fluid-sm text-secondary hover:bg-slate-800/40 focus-ring"
            >
              Home
            </Link>
            <Link
              href="/console"
              className="rounded-full border border-slate-700/60 px-4 py-2 text-fluid-sm text-secondary hover:bg-slate-800/40 focus-ring"
            >
              Console
            </Link>
          </div>
        </header>

        {error && <div className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-fluid-sm text-rose-200">{error}</div>}

        <section className={`${styles.settingsSection} surface`}>
          <h2 className="text-fluid-xl font-bold text-primary">Capture permissions</h2>
          <p className="mt-2 text-fluid-base text-secondary leading-relaxed">
            Toggle telemetry capture and consent requirements. These changes apply immediately across the service.
          </p>
          <div className={styles.actionRow}>
            <button
              type="button"
              onClick={togglePrivacy}
              className="rounded-full bg-cyan-600 px-5 py-3 text-fluid-sm font-semibold text-white transition hover:bg-cyan-500 disabled:opacity-50 focus-ring"
              disabled={loading}
            >
              {privacyPause ? "Resume capture" : "Enable privacy pause"}
            </button>
            <button
              type="button"
              onClick={toggleConsent}
              className="rounded-full bg-indigo-600 px-5 py-3 text-fluid-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50 focus-ring"
              disabled={loading}
            >
              {consentGranted ? "Revoke consent" : "Grant consent"}
            </button>
          </div>
          <div className="mt-4 text-fluid-xs text-muted space-y-1">
            <div>Privacy pause: {privacyPause ? "on" : "off"}</div>
            <div>Consent granted: {consentGranted ? "yes" : "no"}</div>
          </div>
        </section>

        <section className={`${styles.settingsSection} surface`}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className="text-fluid-xl font-bold text-primary">Context guard</h2>
              <p className="mt-2 text-fluid-base text-secondary leading-relaxed">
                Choose which detected workspaces or applications should pause EMA prompts automatically.
              </p>
            </div>
            <span className="text-fluid-xs text-muted">
              {contextSaving ? "Saving..." : `Blocking ${contextBlocklist.length} context${contextBlocklist.length === 1 ? "" : "s"}`}
            </span>
          </div>

          <div className={styles.formGrid}>
            <div className={`${styles.contextPanel} surface`}>
              <div className="flex items-center justify-between">
                <h3 className="text-fluid-sm font-semibold text-primary">Workspace contexts</h3>
                <span className="text-fluid-xs text-muted">{workspaceChips.length} observed</span>
              </div>
              {workspaceChips.length === 0 ? (
                <p className="mt-3 text-fluid-xs text-muted">No context signals observed yet.</p>
              ) : (
                <div className={styles.chipContainer}>
                  {workspaceChips.map((flag) => (
                    <label
                      key={`workspace-${flag}`}
                      className={`flex items-center gap-2 rounded-full border px-3 py-1 text-fluid-xs transition focus-ring ${
                        contextBlocklist.includes(flag)
                          ? "border-cyan-400 bg-cyan-500/10 text-cyan-100"
                          : "border-slate-700 text-secondary hover:border-cyan-500/50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="h-3 w-3 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
                        checked={contextBlocklist.includes(flag)}
                        onChange={(event) => handleContextToggle(flag, event.target.checked)}
                      />
                      <span>{flag}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className={`${styles.contextPanel} surface`}>
              <div className="flex items-center justify-between">
                <h3 className="text-fluid-sm font-semibold text-primary">Running applications</h3>
                <span className="text-fluid-xs text-muted">{applicationChips.length} detected</span>
              </div>
              {applicationChips.length === 0 ? (
                <p className="mt-3 text-fluid-xs text-muted">Start interacting with your workspace to populate this list.</p>
              ) : (
                <div className={styles.chipContainer}>
                  {applicationChips.map((flag) => (
                    <label
                      key={`app-${flag}`}
                      className={`flex items-center gap-2 rounded-full border px-3 py-1 text-fluid-xs transition focus-ring ${
                        contextBlocklist.includes(flag)
                          ? "border-cyan-400 bg-cyan-500/10 text-cyan-100"
                          : "border-slate-700 text-secondary hover:border-cyan-500/50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="h-3 w-3 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
                        checked={contextBlocklist.includes(flag)}
                        onChange={(event) => handleContextToggle(flag, event.target.checked)}
                      />
                      <span>{flag}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className={styles.actionRow}>
            <input
              type="text"
              value={newContext}
              onChange={(event) => setNewContext(event.target.value)}
              placeholder="Add application or keyword"
              className="flex-1 rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-2 text-fluid-sm text-secondary placeholder-slate-500 focus:border-cyan-500/60 focus:outline-none focus-ring"
            />
            <button
              type="button"
              onClick={handleAddContext}
              className="rounded-full border border-slate-700/60 px-5 py-2 text-fluid-sm font-semibold text-secondary hover:bg-slate-800/40 focus-ring"
            >
              Add context
            </button>
          </div>
        </section>

        <section className={`${styles.settingsSection} surface`}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className="text-lg font-semibold">Idle guard</h2>
              <p className="text-sm text-slate-400">
                Automatically pause prompts when no activity is detected for a custom duration.
              </p>
            </div>
            <span className="text-xs text-slate-400">Current threshold: {describeDuration(idleBlockSeconds)}</span>
          </div>

          <div className={styles.actionRow}>
            <label className="flex flex-1 flex-col gap-1 text-xs text-slate-400">
              Idle duration
              <input
                type="time"
                step={60}
                min="00:00:00"
                max="23:59:59"
                value={secondsToTimeInput(idleBlockSeconds)}
                onChange={(event) => handleIdlePickerChange(event.target.value)}
                className="rounded-lg border border-slate-700/60 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 focus:border-cyan-500/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
              />
            </label>
            <button
              type="button"
              onClick={persistIdleBlock}
              className="rounded-full bg-cyan-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-cyan-500 disabled:opacity-50"
              disabled={idleSaving}
            >
              {idleSaving ? "Saving..." : "Save idle guard"}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Prompts will resume automatically after activity resumes or the idle guard timer expires.
          </p>
        </section>
      </div>
    </main>
  );
}
