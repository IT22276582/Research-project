"""Sliding window orchestration with context extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from .config import WindowConfig
from .events import Event
from .features import FeatureWindow, fuse_features


@dataclass
class WindowContext:
    """Describes contextual flags applied to the latest hop."""

    context_flags: Dict[str, str] = field(default_factory=dict)
    inactivity_gap_seconds: float = 0.0
    missing_window: bool = False
    running_apps: List[str] = field(default_factory=list)

    def as_list(self) -> List[str]:
        items = [value for value in self.context_flags.values()]
        if self.inactivity_gap_seconds > 0:
            items.append(f"idle {self.inactivity_gap_seconds:.0f}s")
        if self.missing_window:
            items.append("recent gap")
        return items


class WindowManager:
    """Aligns the 60s/15s hop windows and extracts contextual hints."""

    def __init__(self, config: WindowConfig) -> None:
        self.window_span = timedelta(seconds=config.window_seconds)
        self.hop = timedelta(seconds=config.hop_seconds)
        self.inactivity_gap = timedelta(seconds=config.inactivity_gap_seconds)
        self._last_window_end: datetime | None = None
        self._last_activity_at: datetime | None = None

    def build_window(
        self,
        events: List[Event],
        hop_index: int,
        window_end: datetime,
        last_vector: Optional[np.ndarray] = None,
    ) -> Tuple[FeatureWindow, WindowContext]:
        window_start = window_end - self.window_span
        fused = fuse_features(events, hop_index, window_start, window_end, last_vector=last_vector)
        context = self._context_from_events(events)
        most_recent_event = self._most_recent_event(events)
        if most_recent_event:
            self._last_activity_at = most_recent_event

        gap_seconds = 0.0
        if self._last_activity_at is not None:
            gap_seconds = max(0.0, (window_end - self._last_activity_at).total_seconds())

        missing_window = False
        if (
            self._last_window_end is not None
            and (window_end - self._last_window_end) > self.hop * 1.5
        ):
            missing_window = True

        if gap_seconds >= self.inactivity_gap.total_seconds():
            context.context_flags.setdefault(
                "inactive", f"idle>{self.inactivity_gap.total_seconds():.0f}s"
            )

        context.inactivity_gap_seconds = gap_seconds
        context.missing_window = missing_window
        self._last_window_end = window_end
        return fused, context

    def _context_from_events(self, events: Iterable[Event]) -> WindowContext:
        flags: Dict[str, str] = {}
        running_apps: set[str] = set()
        for event in events:
            if event.source != "system":
                continue
            payload = event.payload
            if payload.get("locked"):
                flags["locked"] = "workstation locked"
            if payload.get("dnd"):
                flags["dnd"] = "do-not-disturb"
            if payload.get("app_blocked"):
                labels = payload.get("focus_app") or "sensitive app"
                flags["app_blocked"] = f"blocked app: {labels}"
            if payload.get("privacy_pause"):
                flags["privacy_pause"] = "privacy pause active"
            custom = payload.get("context_label")
            if isinstance(custom, str):
                flags.setdefault("context_label", custom)
            focus_app = payload.get("focus_app")
            if isinstance(focus_app, str):
                flags.setdefault("focus_app", focus_app)
            apps = payload.get("running_apps")
            if isinstance(apps, list):
                for entry in apps:
                    if isinstance(entry, str) and entry:
                        running_apps.add(entry)
        return WindowContext(context_flags=flags, running_apps=sorted(running_apps))

    @staticmethod
    def _most_recent_event(events: Iterable[Event]) -> datetime | None:
        latest: datetime | None = None
        for event in events:
            if latest is None or event.timestamp > latest:
                latest = event.timestamp
        return latest
