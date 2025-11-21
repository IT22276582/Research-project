"""Local telemetry summaries shared with the overlay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ema import SchedulerState, SchedulerStatus
from .window_manager import WindowContext


@dataclass
class TelemetrySnapshot:
    hop_index: Optional[int] = None
    residual: Optional[float] = None
    variance: Optional[float] = None
    baseline_active: Optional[bool] = None
    load_state: str = "unknown"
    pending_prompt_reason: Optional[str] = None
    suppression_reason: Optional[str] = None
    scheduler_state: SchedulerState = SchedulerState.DORMANT
    cooldown_seconds: Optional[float] = None
    snooze_seconds: Optional[float] = None
    context_flags: List[str] = field(default_factory=list)
    running_apps: List[str] = field(default_factory=list)
    inactivity_gap_seconds: Optional[float] = None
    consent_granted: bool = True
    privacy_pause: bool = False
    next_prompt_seconds: Optional[float] = None
    onboarding_percent: Optional[float] = None
    onboarding_message: Optional[str] = None
    policy_prompted: Optional[int] = None
    policy_suppressed: Optional[int] = None
    active_prompt_id: Optional[int] = None


class TelemetryEmitter:
    """Maintains a compact snapshot for `/telemetry`."""

    def __init__(self) -> None:
        self._snapshot = TelemetrySnapshot()

    def update(
        self,
        *,
        hop_index: int,
        residual: float,
        variance: float,
        baseline_active: bool,
        load_state: str,
        pending_prompt_reason: Optional[str],
        scheduler_status: SchedulerStatus,
        context: WindowContext,
        onboarding_state: Optional[Dict[str, Any]] = None,
        policy_counters: Optional[Dict[str, int]] = None,
        active_prompt_id: Optional[int] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        cooldown_seconds = (
            (scheduler_status.cooldown_until - now).total_seconds()
            if scheduler_status.cooldown_until and scheduler_status.cooldown_until > now
            else None
        )
        snooze_seconds = (
            (scheduler_status.snoozed_until - now).total_seconds()
            if scheduler_status.snoozed_until and scheduler_status.snoozed_until > now
            else None
        )
        next_prompt_seconds = (
            (scheduler_status.next_prompt_candidate - now).total_seconds()
            if scheduler_status.next_prompt_candidate and scheduler_status.next_prompt_candidate > now
            else None
        )
        self._snapshot = TelemetrySnapshot(
            hop_index=hop_index,
            residual=residual,
            variance=variance,
            baseline_active=baseline_active,
            load_state=load_state,
            pending_prompt_reason=pending_prompt_reason,
            suppression_reason=scheduler_status.suppression_reason,
            scheduler_state=scheduler_status.state,
            cooldown_seconds=cooldown_seconds,
            snooze_seconds=snooze_seconds,
            context_flags=context.as_list(),
            running_apps=context.running_apps,
            inactivity_gap_seconds=context.inactivity_gap_seconds,
            consent_granted=scheduler_status.consent_granted,
            privacy_pause=scheduler_status.privacy_pause,
            next_prompt_seconds=next_prompt_seconds,
            onboarding_percent=(onboarding_state or {}).get("percent") if onboarding_state else None,
            onboarding_message=(onboarding_state or {}).get("message") if onboarding_state else None,
            policy_prompted=(policy_counters or {}).get("prompted") if policy_counters else None,
            policy_suppressed=(policy_counters or {}).get("suppressed") if policy_counters else None,
            active_prompt_id=active_prompt_id,
        )

    def snapshot(self) -> TelemetrySnapshot:
        return self._snapshot
