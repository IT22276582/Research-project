"use client";

import { useEffect, useRef, useState } from "react";
import {
  EstimateResponse,
  TelemetryResponse,
  fetchPendingPrompt,
  subscribeStateStream,
} from "../../lib/api";

export type HistoryPoint = { t: number; load: number; residual: number };
export type HydratedPrompt = { prompt_id: number; reason: string } | null;

type StreamHandlers = {
  onConnect?: () => void;
  onDisconnect?: () => void;
};

export function useEstimatorStream(handlers?: StreamHandlers) {
  const [estimate, setEstimate] = useState<EstimateResponse | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [status, setStatus] = useState<string>("connecting...");
  const [error, setError] = useState<string | null>(null);
  const [hydratedPrompt, setHydratedPrompt] = useState<HydratedPrompt>(null);

  const handlersRef = useRef<StreamHandlers | undefined>(handlers);
  const connectionAnnounced = useRef(false);
  const pendingFetch = useRef(false);
  const hydratedPromptRef = useRef<HydratedPrompt>(null);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    hydratedPromptRef.current = hydratedPrompt;
  }, [hydratedPrompt]);

  useEffect(() => {
    const disconnect = subscribeStateStream(
      (payload) => {
        const nextTelemetry = payload.telemetry;
        const nextEstimate = payload.estimate;
        setTelemetry(nextTelemetry);

        const scheduler =
          nextTelemetry.scheduler_state ?? nextEstimate?.scheduler_state ?? "unknown";
        const promptFromEstimate = nextEstimate?.pending_prompt ?? null;

        if (promptFromEstimate) {
          setHydratedPrompt(null);
        } else if (
          scheduler === "awaiting_response" &&
          !pendingFetch.current &&
          !hydratedPromptRef.current
        ) {
          pendingFetch.current = true;
          fetchPendingPrompt()
            .then((res) => {
              if (res.prompt) {
                setHydratedPrompt({
                  prompt_id: res.prompt.prompt_id,
                  reason: res.prompt.reason,
                });
              }
            })
            .catch(() => undefined)
            .finally(() => {
              pendingFetch.current = false;
            });
        } else if (scheduler !== "awaiting_response") {
          setHydratedPrompt(null);
        }

        const mergedEstimate = nextEstimate
          ? {
              ...nextEstimate,
              pending_prompt:
                nextEstimate.pending_prompt ?? hydratedPromptRef.current ?? undefined,
            }
          : null;

        if (mergedEstimate) {
          setEstimate(mergedEstimate);
          setHistory((prev) => {
            // Anchor history points to receive-time so prompts/EMA don't pull
            // the chart back to the prompt timestamp. Enforce monotonic time.
            const receiveTime = Date.now();
            const lastT = prev[prev.length - 1]?.t ?? receiveTime;
            const t = Math.max(receiveTime, lastT + 1);

            const updated = [
              ...prev,
              {
                t,
                load: mergedEstimate.load,
                residual: mergedEstimate.residual,
              },
            ];
            return updated.slice(-120);
          });
          setStatus(
            `online (${scheduler}) | hop ${mergedEstimate.hop_index} | baseline ${
              mergedEstimate.baseline_active ? "on" : "off"
            }`
          );
        } else {
          setStatus(`online (${scheduler}) | waiting for estimate`);
        }

        if (!connectionAnnounced.current) {
          handlersRef.current?.onConnect?.();
          connectionAnnounced.current = true;
        }
        setError(null);
      },
      () => {
        setStatus("offline");
        setError("Stream disconnected");
        handlersRef.current?.onDisconnect?.();
        connectionAnnounced.current = false;
      }
    );
    return () => disconnect();
  }, []);

  return {
    estimate,
    telemetry,
    history,
    status,
    error,
    hydratedPrompt,
    setHydratedPrompt,
  };
}
