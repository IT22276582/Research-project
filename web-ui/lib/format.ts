export type Tone = "rose" | "amber" | "emerald" | "cyan" | "indigo" | "slate";

export function formatSeconds(value?: number | null): string {
  if (value === null || value === undefined) {
    return "none";
  }
  const clamped = Math.max(0, Math.round(value));
  if (clamped <= 0) return "none";
  return `${clamped}s`;
}

export function toneForLoadState(loadState?: string | null): Tone {
  const normalized = (loadState ?? "").toLowerCase();
  if (normalized.includes("high")) return "rose";
  if (normalized.includes("medium")) return "amber";
  if (normalized.includes("low")) return "emerald";
  return "slate";
}
