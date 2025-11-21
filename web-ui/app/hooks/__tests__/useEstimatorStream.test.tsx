import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEstimatorStream } from "../useEstimatorStream";

type Subscriber = {
  onMessage: (payload: any) => void;
  onError?: () => void;
};

const mockApi = vi.hoisted(() => ({
  subscribers: [] as Subscriber[],
  fetchPendingPrompt: vi.fn(),
}));

vi.mock("../../../lib/api", () => ({
  fetchPendingPrompt: mockApi.fetchPendingPrompt,
  subscribeStateStream: (onMessage: Subscriber["onMessage"], onError?: Subscriber["onError"]) => {
    mockApi.subscribers.push({ onMessage, onError });
    return () => {
      /* noop */
    };
  },
}));

describe("useEstimatorStream", () => {
  beforeEach(() => {
    mockApi.subscribers.length = 0;
    mockApi.fetchPendingPrompt.mockReset();
  });

  it("updates estimate, history, and connection status from stream events", async () => {
    const connectSpy = vi.fn();
    const disconnectSpy = vi.fn();
    const { result } = renderHook(() =>
      useEstimatorStream({ onConnect: connectSpy, onDisconnect: disconnectSpy })
    );

    const firstPayload = {
      telemetry: {
        hop_index: 1,
        residual: 0.05,
        variance: 0.1,
        baseline_active: false,
        scheduler_state: "ready",
        pending_prompt_reason: "none",
        suppression_reason: null,
      },
      estimate: {
        hop_index: 1,
        timestamp: new Date().toISOString(),
        load: 0.25,
        variance: 0.1,
        ci95: 0.2,
        residual: 0.05,
        quality: 1.0,
        baseline_active: false,
        pending_prompt: null,
        context_flags: {},
        scheduler_state: "ready",
      },
    };

    await waitFor(() => expect(mockApi.subscribers.length).toBe(1));
    act(() => mockApi.subscribers[0].onMessage(firstPayload));

    await waitFor(() => expect(result.current.estimate?.load).toBeCloseTo(0.25));
    expect(result.current.history).toHaveLength(1);
    expect(result.current.status).toContain("online");
    expect(connectSpy).toHaveBeenCalledTimes(1);
    expect(disconnectSpy).not.toHaveBeenCalled();
  });

  it("hydrates pending prompt when scheduler awaits a response and handles disconnects", async () => {
    mockApi.fetchPendingPrompt.mockResolvedValue({ prompt: { prompt_id: 42, reason: "manual", issued_at: "now" } });
    const { result } = renderHook(() => useEstimatorStream());

    const awaitingPayload = {
      telemetry: {
        hop_index: 2,
        residual: 0.02,
        variance: 0.08,
        baseline_active: true,
        scheduler_state: "awaiting_response",
        pending_prompt_reason: "residual spike",
        suppression_reason: null,
      },
      estimate: {
        hop_index: 2,
        timestamp: new Date().toISOString(),
        load: 0.6,
        variance: 0.08,
        ci95: 0.2,
        residual: 0.02,
        quality: 0.9,
        baseline_active: true,
        pending_prompt: null,
        context_flags: {},
        scheduler_state: "awaiting_response",
      },
    };

    await waitFor(() => expect(mockApi.subscribers.length).toBe(1));
    act(() => mockApi.subscribers[0].onMessage(awaitingPayload));

    await waitFor(() => expect(mockApi.fetchPendingPrompt).toHaveBeenCalledOnce());
    await waitFor(() => expect(result.current.hydratedPrompt?.prompt_id).toBe(42));
    expect(result.current.history).toHaveLength(1);

    act(() => mockApi.subscribers[0].onError?.());
    await waitFor(() => expect(result.current.error).toBe("Stream disconnected"));
    expect(result.current.status).toBe("offline");
  });
});
