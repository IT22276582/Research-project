"""Event capture primitives and an in-memory ring buffer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Deque, Dict, List, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Event:
    timestamp: datetime
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)


class PermissionGuard:
    """Enforces source allowlists plus consent/privacy toggles."""

    def __init__(
        self,
        allowed_sources: List[str],
        privacy_pause: bool = False,
        consent_granted: bool = True,
        context_blocklist: List[str] | None = None,
        idle_block_seconds: int = 0,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.allowed_sources = set(allowed_sources)
        self.privacy_pause = privacy_pause
        self.consent_granted = consent_granted
        self.context_blocklist = set(context_blocklist or [])
        self._normalized_blocklist = {self._normalize(entry) for entry in self.context_blocklist}
        self.idle_block_seconds = max(0, int(idle_block_seconds))
        self._last_idle_seconds: float = 0.0
        self._last_context_flags: Dict[str, str] = {}

    def allow(self, event: Event) -> bool:
        if event.source == "system":
            self._update_context_state(event.payload)
            return True  # always ingest system snapshots to keep guard fresh

        if self.privacy_pause or not self.consent_granted:
            return False

        if event.source not in self.allowed_sources:
            return False

        if self.idle_block_seconds and self._last_idle_seconds >= self.idle_block_seconds:
            self.logger.debug("Dropping %s event due to idle >= %ss", event.source, self.idle_block_seconds)
            return False

        blocked = self.context_blocked(self._last_context_flags)
        if blocked:
            self.logger.debug("Dropping %s event due to blocked context=%s", event.source, blocked)
            return False

        return True

    def set_privacy_pause(self, active: bool) -> None:
        self.privacy_pause = active
        self.logger.info("Privacy pause updated -> %s", active)

    def set_consent(self, granted: bool) -> None:
        self.consent_granted = granted
        self.logger.info("Consent updated -> %s", granted)

    def status(self) -> Dict[str, Any]:
        return {
            "privacy_pause": self.privacy_pause,
            "consent_granted": self.consent_granted,
            "context_blocklist": self.get_context_blocklist(),
            "idle_block_seconds": self.idle_block_seconds,
        }

    def context_blocked(self, flags: Dict[str, str]) -> Optional[str]:
        """Return the block reason if the current context violates policy."""
        for key, value in flags.items():
            if self._normalize(key) in self._normalized_blocklist:
                self.logger.debug("Context blocked by key=%s", key)
                return key
            if self._normalize(value) in self._normalized_blocklist:
                self.logger.debug("Context blocked by value=%s", value)
                return value
        return None

    def set_context_blocklist(self, entries: List[str]) -> None:
        self.context_blocklist = {entry.strip() for entry in entries if entry.strip()}
        self._normalized_blocklist = {
            self._normalize(entry) for entry in self.context_blocklist
        }
        self.logger.info("Context blocklist set to %s", entries)

    def get_context_blocklist(self) -> List[str]:
        return sorted(self.context_blocklist)

    def set_idle_block_seconds(self, seconds: int) -> None:
        if seconds < 0:
            raise ValueError("idle block seconds must be >= 0")
        self.idle_block_seconds = seconds
        self.logger.info("Idle block seconds set to %s", seconds)

    @staticmethod
    def _normalize(entry: str) -> str:
        return entry.strip().lower()

    def _update_context_state(self, payload: Dict[str, Any]) -> None:
        idle_seconds = payload.get("idle_seconds")
        if isinstance(idle_seconds, (int, float)):
            self._last_idle_seconds = float(idle_seconds)
        flags: Dict[str, str] = {}
        for key in ("context_label", "focus_app", "app_blocked", "privacy_pause", "dnd", "locked"):
            if payload.get(key):
                flags[key] = str(payload[key])
        running_apps = payload.get("running_apps") or []
        if isinstance(running_apps, list):
            for app in running_apps:
                if isinstance(app, str) and app:
                    flags.setdefault(app, app)
        self._last_context_flags = flags


class EventBuffer:
    """Maintains a sliding buffer of sanitized events."""

    def __init__(self, span: timedelta) -> None:
        self.span = span
        self._events: Deque[Event] = deque()

    def append(self, event: Event) -> None:
        self._events.append(event)
        self._prune(event.timestamp - self.span)

    def window(self, end_time: datetime) -> List[Event]:
        start_time = end_time - self.span
        self._prune(start_time)
        return [evt for evt in self._events if evt.timestamp >= start_time]

    def _prune(self, cutoff: datetime) -> None:
        while self._events and self._events[0].timestamp < cutoff:
            self._events.popleft()
