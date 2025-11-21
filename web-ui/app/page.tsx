"use client";

import { useMemo } from "react";
import { EstimateCard } from "./components/EstimateCard";
import { PromptPanel } from "./components/PromptPanel";
import { Surface } from "./components/Surface";
import { useToasts } from "./components/ToastProvider";
import { AlertBanner } from "./components/home/AlertBanner";
import { HomeHeader } from "./components/home/HomeHeader";
import { NavigationPanel } from "./components/home/NavigationPanel";
import { RuntimeSnapshot } from "./components/home/RuntimeSnapshot";
import { StatCardView, StatHighlights } from "./components/home/StatHighlights";
import { VisualizationPanel } from "./components/home/VisualizationPanel";
import { WorkspacePanel } from "./components/home/WorkspacePanel";
import { useEstimatorStream } from "./hooks/useEstimatorStream";
import { toneForLoadState, Tone } from "../lib/format";
import styles from "./page.module.css";
import homeStyles from "./components/home/Home.module.css";

function formatMetric(value?: number | null, digits = 3) {
  if (value === null || value === undefined) return "--";
  if (!Number.isFinite(value)) return "--";
  return value.toFixed(digits);
}

export default function Home() {
  const { addToast } = useToasts();
  const { estimate, telemetry, history, status, error, hydratedPrompt, setHydratedPrompt } =
    useEstimatorStream({
      onConnect: () => addToast("Telemetry stream connected", "success"),
      onDisconnect: () => addToast("Telemetry stream disconnected", "error"),
    });

  const schedulerState =
    telemetry?.scheduler_state ?? estimate?.scheduler_state ?? "unknown";
  const contextFlags =
    telemetry?.context_flags ??
    (estimate ? Object.values(estimate.context_flags ?? {}) : []);
  const onboarding = estimate?.onboarding_state ?? null;
  const onboardingPercent =
    typeof onboarding?.percent === "number"
      ? onboarding.percent
      : telemetry?.onboarding_percent ?? null;
  const onboardingMessage =
    onboarding?.message ?? telemetry?.onboarding_message ?? null;
  const streamHealthy = !error;
  const pendingReason = telemetry?.pending_prompt_reason ?? "none";
  const baselineActive =
    telemetry?.baseline_active ?? estimate?.baseline_active ?? null;
  const loadState =
    telemetry?.load_state ?? estimate?.load_state ?? "unknown cognitive load";
  const loadTone: Tone = toneForLoadState(loadState);

  const statCards: StatCardView[] = useMemo(
    () => [
      {
        id: "cognitive_state",
        label: "Cognitive state",
        value: loadState,
        hint: "Real-time classification",
        tone: loadTone,
      },
      // {
      //   id: "residual",
      //   label: "Residual RMS",
      //   value: formatMetric(telemetry?.residual, 3),
      //   hint: "Live model error (lower is better)",
      //   tone: "amber",
      //   variant: "compact",
      // },
      {
        id: "variance",
        label: "Variance",
        value: formatMetric(telemetry?.variance, 3),
        hint: "Posterior uncertainty",
        tone: "indigo",
        variant: "compact",
      },
      {
        id: "scheduler",
        label: "Scheduler state",
        value: schedulerState,
        hint:
          pendingReason === "none"
            ? "Ready for new prompts"
            : `Pending: ${pendingReason}`,
        tone: "cyan",
      },
      {
        id: "baseline",
        label: "Baseline",
        value:
          baselineActive === null
            ? "--"
            : baselineActive
            ? "calibrating"
            : "steady",
        hint:
          onboardingPercent !== null
            ? `Onboarding ${Math.round(onboardingPercent * 100)}%`
            : "Adaptive profile locked in",
        tone: "emerald",
      },
    ],
    [
      baselineActive,
      loadState,
      loadTone,
      onboardingPercent,
      pendingReason,
      schedulerState,
      telemetry?.residual,
      telemetry?.variance,
    ]
  );

  const hopLabel = `Hop ${estimate?.hop_index ?? telemetry?.hop_index ?? "--"}`;
  const baselineLabel =
    baselineActive === null
      ? "Baseline --"
      : `Baseline ${baselineActive ? "calibrating" : "steady"}`;

  const promptEstimate = estimate
    ? {
        ...estimate,
        pending_prompt: estimate.pending_prompt ?? hydratedPrompt ?? undefined,
      }
    : null;

  return (
    <main className={styles.page}>
      <div className={styles.glow} />
      <div className={`${styles.container} container-dashboard`}>
        {error && (
          <AlertBanner
            tone="error"
            title="Stream issue"
            message={`Stream disconnected. Ensure the estimator service is running at ${
              process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"
            } and network access is allowed.`}
          />
        )}

        {onboardingMessage && (
          <AlertBanner
            tone="warning"
            title="Baseline calibration"
            message={`${onboardingMessage}${
              onboardingPercent !== null
                ? ` (${Math.round(onboardingPercent * 100)}%)`
                : ""
            }`}
          />
        )}

        <Surface padding="lg" className="surface">
          <HomeHeader
            status={status}
            streamHealthy={streamHealthy}
            baselineLabel={baselineLabel}
            hopLabel={hopLabel}
            pendingReason={pendingReason}
          />
        </Surface>

        <StatHighlights cards={statCards} />

        <div className={styles.columns}>
          <div className={styles.primaryColumn}>
            <div className={styles.primaryGrid}>
              <Surface padding="lg" className="surface">
                <RuntimeSnapshot
                  schedulerState={schedulerState}
                  loadState={loadState}
                  loadTone={loadTone}
                  cooldownSeconds={telemetry?.cooldown_seconds}
                  snoozeSeconds={telemetry?.snooze_seconds}
                  nextPromptSeconds={telemetry?.next_prompt_seconds}
                  policyPrompted={telemetry?.policy_prompted}
                  policySuppressed={telemetry?.policy_suppressed}
                  contextFlags={contextFlags}
                />
              </Surface>

              <Surface padding="lg" className="surface">
                {estimate ? (
                  <EstimateCard estimate={estimate} />
                ) : (
                  <div className={`${styles.placeholder} text-fluid-base text-muted`}>
                    Waiting for the first estimate. Keep the estimator running and
                    interact with keyboard/mouse to generate signal.
                  </div>
                )}
              </Surface>
            </div>

            <Surface padding="lg" className="surface">
              <VisualizationPanel history={history} />
            </Surface>
          </div>

          <div className={styles.secondaryColumn}>
            <Surface padding="lg" className="surface">
              <div className={homeStyles.section}>
                <div className={homeStyles.sectionHeader}>
                  <h2 className={homeStyles.sectionTitle}>EMA prompt</h2>
                </div>
                {promptEstimate ? (
                  <PromptPanel
                    estimate={promptEstimate}
                    onSubmit={(result) => {
                      if (result) {
                        addToast(
                          `Prompt ${result.promptId} ${result.status}`,
                          result.status === "completed" ? "success" : "info"
                        );
                        setHydratedPrompt(null);
                      }
                    }}
                  />
                ) : (
                  <div className={`${styles.placeholder} text-fluid-base text-muted`}>
                    Waiting for estimate before prompts can be shown.
                  </div>
                )}
              </div>
            </Surface>

            <Surface padding="lg" className="surface">
              <WorkspacePanel
                privacyPause={telemetry?.privacy_pause}
                consentGranted={telemetry?.consent_granted}
                loadState={loadState}
                loadTone={loadTone}
                contextFlags={contextFlags}
              />
            </Surface>

            <Surface padding="lg" className="surface">
              <NavigationPanel />
            </Surface>
          </div>
        </div>
      </div>
    </main>
  );
}
