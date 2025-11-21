"""Policy-related helpers (consent logging, suppression auditing)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .ema import PromptDecision, SchedulerState
from .events import PermissionGuard
from .storage import Storage
from .window_manager import WindowContext


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConsentEntry:
    timestamp: str
    granted: bool
    reason: Optional[str]


class ConsentLog:
    """JSONL-backed consent history."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def append(self, granted: bool, reason: Optional[str] = None) -> None:
        entry = {
            "timestamp": _utc_iso(),
            "granted": granted,
            "reason": reason,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def list_recent(self, limit: int = 50) -> List[ConsentEntry]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        entries: List[ConsentEntry] = []
        for raw in lines[-limit:]:
            try:
                payload = json.loads(raw)
                entries.append(
                    ConsentEntry(
                        timestamp=payload.get("timestamp", ""),
                        granted=bool(payload.get("granted")),
                        reason=payload.get("reason"),
                    )
                )
            except json.JSONDecodeError:
                continue
        return entries


@dataclass
class PolicyEvent:
    timestamp: str
    event_type: str
    reason: Optional[str]
    metadata: Dict[str, str]


class PolicyActor:
    """Applies policy constraints beyond the EMA scheduler."""

    def __init__(self, storage: Storage, guard: PermissionGuard) -> None:
        self.storage = storage
        self.guard = guard
        self._prompt_count = 0
        self._suppressed_count = 0

    async def enforce(
        self, decision: PromptDecision, context: WindowContext
    ) -> PromptDecision:
        reason: Optional[str] = None
        state = decision.state

        if self.guard.privacy_pause:
            reason = "privacy_pause"
            state = SchedulerState.HARD_SUPPRESSED
        elif not self.guard.consent_granted:
            reason = "no_consent"
            state = SchedulerState.DORMANT
        else:
            idle_threshold = getattr(self.guard, "idle_block_seconds", 0)
            if idle_threshold and context.inactivity_gap_seconds >= idle_threshold:
                reason = f"idle>{int(idle_threshold)}s"
                state = SchedulerState.CONTEXT_SUPPRESSED
            else:
                blocked = self.guard.context_blocked(context.context_flags)
                if blocked:
                    reason = blocked
                    state = SchedulerState.CONTEXT_SUPPRESSED
            if not reason and context.context_flags.get("dnd"):
                reason = "dnd"
                state = SchedulerState.CONTEXT_SUPPRESSED

        if reason:
            self._suppressed_count += 1
            await self.storage.record_policy_event(
                "suppressed", reason, metadata=context.context_flags
            )
            return PromptDecision(
                should_prompt=False,
                reason=reason,
                suppressed=True,
                suppression_reason=reason,
                state=state,
            )

        if decision.should_prompt:
            self._prompt_count += 1
            await self.storage.record_policy_event(
                "eligible", decision.reason, metadata=context.context_flags
            )
        return decision

    def counters(self) -> Dict[str, int]:
        return {"prompted": self._prompt_count, "suppressed": self._suppressed_count}
