export type EstimateResponse = {
  hop_index: number;
  timestamp: string;
  load: number;
  load_state?: string;
  variance: number;
  ci95: number;
  residual: number;
  quality: number;
  baseline_active: boolean;
  pending_prompt?: { prompt_id: number; reason: string } | null;
  context_flags: Record<string, string>;
  scheduler_state: string;
  onboarding_state?: { message?: string; percent?: number } | null;
  active_prompt_id?: number | null;
};

export type TelemetryResponse = {
  hop_index: number | null;
  residual: number | null;
  variance: number | null;
  baseline_active: boolean | null;
  load_state?: string | null;
  pending_prompt_reason: string | null;
  suppression_reason: string | null;
  scheduler_state?: string;
  cooldown_seconds?: number | null;
  snooze_seconds?: number | null;
  context_flags?: string[];
  running_apps?: string[];
  inactivity_gap_seconds?: number | null;
  consent_granted?: boolean;
  privacy_pause?: boolean;
  next_prompt_seconds?: number | null;
  onboarding_percent?: number | null;
  onboarding_message?: string | null;
  policy_prompted?: number | null;
  policy_suppressed?: number | null;
  active_prompt_id?: number | null;
};

export type PolicyEvent = {
  occurred_at: string;
  event_type: string;
  reason?: string | null;
  metadata: Record<string, unknown>;
};

export type ConsentEntry = {
  timestamp: string;
  granted: boolean;
  reason?: string | null;
};

export type TelemetryMetric = {
  snapshot_at: string;
  metric_type: string | null;
  metric_value: number | null;
  metadata: Record<string, unknown>;
};

export type StateStreamMessage = {
  telemetry: TelemetryResponse;
  estimate: EstimateResponse | null;
};

export type PermissionsStatus = {
  privacy_pause: boolean;
  consent_granted: boolean;
  context_blocklist: string[];
  context_catalog?: string[];
  idle_block_seconds?: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchEstimate(): Promise<EstimateResponse> {
  return getJSON<EstimateResponse>("/estimate");
}

export async function fetchTelemetry(): Promise<TelemetryResponse> {
  return getJSON<TelemetryResponse>("/telemetry");
}

export async function fetchPendingPrompt(): Promise<{ prompt: { prompt_id: number; reason: string; issued_at: string } | null }> {
  return getJSON<{ prompt: { prompt_id: number; reason: string; issued_at: string } | null }>("/ema/pending");
}

export function subscribeStateStream(
  onMessage: (payload: StateStreamMessage) => void,
  onError?: () => void
): () => void {
  const source = new EventSource(`${API_BASE}/stream/state`);
  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as StateStreamMessage;
      onMessage(data);
    } catch {
      // swallow malformed events
    }
  };
  source.onerror = () => {
    onError?.();
  };
  return () => source.close();
}

export async function updatePrivacy(active: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/privacy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
  if (!res.ok) {
    throw new Error(`Privacy toggle failed: ${res.status}`);
  }
}

export async function updateConsent(granted: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ granted }),
  });
  if (!res.ok) {
    throw new Error(`Consent toggle failed: ${res.status}`);
  }
}

export async function postEmaResponse(
  promptId: number,
  rating: number,
  disposition: "completed" | "dismissed" | "timeout" | "snoozed",
  note?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/ema/response`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt_id: promptId,
      rating,
      disposition,
      note,
    }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`EMA response failed: ${res.status} ${msg}`);
  }
}

export async function fetchPolicyEvents(limit = 100): Promise<PolicyEvent[]> {
  const payload = await getJSON<{ events: PolicyEvent[] }>(`/policy/events?limit=${limit}`);
  return payload.events;
}

export async function fetchConsentHistory(limit = 50): Promise<ConsentEntry[]> {
  const payload = await getJSON<{ entries: ConsentEntry[] }>("/policy/consent");
  return payload.entries.slice(-limit);
}

export async function fetchTelemetryFeed(limit = 200): Promise<TelemetryMetric[]> {
  const res = await fetch(`${API_BASE}/telemetry/feed?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`telemetry feed failed: ${res.status}`);
  }
  const text = await res.text();
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as TelemetryMetric);
}

export async function fetchPermissions(): Promise<PermissionsStatus> {
  return getJSON<PermissionsStatus>("/permissions");
}

export async function updateContextBlocklist(entries: string[]): Promise<PermissionsStatus> {
  const res = await fetch(`${API_BASE}/permissions/context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries }),
  });
  if (!res.ok) {
    throw new Error(`Context blocklist update failed: ${res.status}`);
  }
  return res.json() as Promise<PermissionsStatus>;
}

export async function updateIdleBlock(seconds: number): Promise<PermissionsStatus> {
  const res = await fetch(`${API_BASE}/permissions/idle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds }),
  });
  if (!res.ok) {
    throw new Error(`Idle block update failed: ${res.status}`);
  }
  return res.json() as Promise<PermissionsStatus>;
}
