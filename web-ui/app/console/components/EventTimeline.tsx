"use client";

import { PolicyEvent } from "../../../lib/api";
import { EventFilters } from "../types";
import { formatTimestamp } from "../utils";
import styles from "./EventTimeline.module.css";

interface EventTimelineProps {
  events: PolicyEvent[];
  filters: EventFilters;
}

const severityColors: Record<string, string> = {
  high: "border-rose-400/60",
  medium: "border-amber-400/60",
  low: "border-emerald-400/60",
};

const determineSeverity = (eventType: string): keyof typeof severityColors => {
  if (eventType.toLowerCase().includes("error")) return "high";
  if (eventType.toLowerCase().includes("warning")) return "medium";
  return "low";
};

export function EventTimeline({ events, filters }: EventTimelineProps) {
  const filteredEvents = events.filter((event) => {
    if (filters.eventType && event.event_type !== filters.eventType) return false;
    if (filters.search && !event.event_type.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="relative">
      <div className={styles.rail} />
      <div className={styles.timeline}>
        {filteredEvents.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">No events found.</p>
        ) : (
          filteredEvents.map((event) => {
            const severity = determineSeverity(event.event_type);
            return (
              <div key={`${event.occurred_at}-${event.event_type}`} className={styles.event}>
                <div className={`${styles.marker} ${severityColors[severity]}`} />
                <div className={styles.card}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className={styles.title}>{event.event_type}</h4>
                    <span className={styles.timestamp}>{formatTimestamp(event.occurred_at)}</span>
                  </div>
                  {event.reason && <p className="mt-1 text-xs text-amber-400">reason: {event.reason}</p>}
                  {event.metadata && Object.keys(event.metadata).length > 0 && (
                    <details className="mt-3 text-xs text-slate-400">
                      <summary className="cursor-pointer text-slate-400 hover:text-slate-200">View metadata</summary>
                      <pre className={styles.metadata}>{JSON.stringify(event.metadata, null, 2)}</pre>
                    </details>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
