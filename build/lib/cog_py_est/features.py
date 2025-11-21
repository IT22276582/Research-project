"""Feature fusion and quality scoring for interaction events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from .events import Event

FEATURE_VECTOR_DIM = 10

@dataclass
class FeatureWindow:
    hop_index: int
    window_start: datetime
    window_end: datetime
    raw_features: Dict[str, float]
    vector: np.ndarray
    quality: float


def _idle_fraction(events: List[Event], window_start: datetime, window_end: datetime) -> float:
    """Approximate idle time as gaps between events within the window."""

    span_seconds = max((window_end - window_start).total_seconds(), 1e-6)
    if not events:
        return 1.0

    sorted_events = sorted(events, key=lambda e: e.timestamp)
    total_idle = max((sorted_events[0].timestamp - window_start).total_seconds(), 0.0)
    # Assume each interaction consumes ~50 ms of active time
    active_epsilon = 0.05
    for first, second in zip(sorted_events, sorted_events[1:]):
        gap = max((second.timestamp - first.timestamp).total_seconds() - active_epsilon, 0.0)
        total_idle += gap
    total_idle += max((window_end - sorted_events[-1].timestamp).total_seconds(), 0.0)
    return min(1.0, total_idle / span_seconds)


def _keystroke_features(events: Iterable[Event]) -> Tuple[List[float], Dict[str, float]]:
    latencies = []
    errors = 0
    backspaces = 0
    count = 0
    for event in events:
        count += 1
        latency = event.payload.get("latency_ms")
        if latency is not None:
            latencies.append(latency)
        if event.payload.get("is_error"):
            errors += 1
        if event.payload.get("is_backspace"):
            backspaces += 1
    lat_array = np.array(latencies) if latencies else np.array([0.0])
    stats = {
        "keystrokes": float(count),
        "iki_mean_ms": float(np.mean(lat_array)),
        "iki_std_ms": float(np.std(lat_array)),
        "error_rate": float(errors / count) if count else 0.0,
        "backspace_rate": float(backspaces / count) if count else 0.0,
    }
    vector = [
        stats["keystrokes"],
        stats["iki_mean_ms"],
        stats["iki_std_ms"],
        stats["error_rate"],
        stats["backspace_rate"],
    ]
    return vector, stats


def _pointer_features(events: Iterable[Event]) -> Tuple[List[float], Dict[str, float]]:
    speeds = []
    accel = []
    prev_speed = None
    for event in events:
        dx = event.payload.get("dx", 0.0)
        dy = event.payload.get("dy", 0.0)
        dt_ms = event.payload.get("dt_ms", 1.0)
        speed = sqrt(dx * dx + dy * dy) / max(dt_ms, 1e-3)
        speeds.append(speed)
        if prev_speed is not None:
            accel.append(speed - prev_speed)
        prev_speed = speed
    speed_arr = np.array(speeds) if speeds else np.array([0.0])
    accel_arr = np.array(accel) if accel else np.array([0.0])
    stats = {
        "pointer_events": float(len(speeds)),
        "pointer_speed_mean": float(np.mean(speed_arr)),
        "pointer_speed_std": float(np.std(speed_arr)),
        "pointer_accel_mean": float(np.mean(accel_arr)),
    }
    vector = [
        stats["pointer_events"],
        stats["pointer_speed_mean"],
        stats["pointer_speed_std"],
        stats["pointer_accel_mean"],
    ]
    return vector, stats

def _classify_focus_app(label: Optional[str]) -> str:
    if not label:
        return "unknown"
    lowered = label.lower()
    if any(key in lowered for key in ["teams", "zoom", "meet", "slack"]):
        return "collaboration"
    if any(key in lowered for key in ["word", "docs", "notepad"]):
        return "writing"
    if any(key in lowered for key in ["excel", "sheets"]):
        return "analysis"
    if any(key in lowered for key in ["outlook", "mail"]):
        return "communication"
    return "other"


def _context_features(events: Iterable[Event]) -> Tuple[List[float], Dict[str, str]]:
    events = list(events)
    total = max(len(events), 1)
    locked_count = sum(1 for e in events if e.payload.get("locked"))
    dnd_count = sum(1 for e in events if e.payload.get("dnd"))
    idle_values = [float(e.payload.get("idle_seconds", 0.0)) for e in events if "idle_seconds" in e.payload]
    focus_app = None
    if events:
        for event in reversed(events):
            focus_app = event.payload.get("focus_app")
            if focus_app:
                break
    category = _classify_focus_app(focus_app)
    avg_idle = float(np.mean(idle_values)) if idle_values else 0.0
    stats = {
        "focus_app": focus_app or "unknown",
        "focus_category": category,
        "locked_ratio": float(locked_count / total),
        "dnd_ratio": float(dnd_count / total),
        "avg_idle_seconds": avg_idle,
    }
    vector = [
        stats["locked_ratio"],
        stats["dnd_ratio"],
        stats["avg_idle_seconds"],
    ]
    return vector, stats


def fuse_features(
    events: List[Event],
    hop_index: int,
    window_start: datetime,
    window_end: datetime,
    last_vector: Optional[np.ndarray] = None,
) -> FeatureWindow:
    keyboard_events = [e for e in events if e.source == "keyboard"]
    pointer_events = [e for e in events if e.source == "pointer"]
    system_events = [e for e in events if e.source == "system"]
    key_vec, key_stats = _keystroke_features(keyboard_events)
    pointer_vec, pointer_stats = _pointer_features(pointer_events)
    _, context_stats = _context_features(system_events)
    idle = _idle_fraction(events, window_start, window_end)

    imputed_keyboard = False
    imputed_pointer = False
    if not keyboard_events and last_vector is not None:
        key_vec = last_vector[: len(key_vec)].tolist()
        imputed_keyboard = True
    if not pointer_events and last_vector is not None:
        pointer_vec = last_vector[len(key_vec) : len(key_vec) + len(pointer_vec)].tolist()
        imputed_pointer = True

    raw = {
        **key_stats,
        **pointer_stats,
        **context_stats,
        "idle_fraction": idle,
        "keyboard_imputed": imputed_keyboard,
        "pointer_imputed": imputed_pointer,
    }
    vector = np.array(
        key_vec
        + pointer_vec
        + [idle],
        dtype=float,
    )
    coverage = 1.0 - idle
    quality = max(0.0, min(1.0, coverage))
    return FeatureWindow(
        hop_index=hop_index,
        window_start=window_start,
        window_end=window_end,
        raw_features=raw,
        vector=vector,
        quality=quality,
    )
