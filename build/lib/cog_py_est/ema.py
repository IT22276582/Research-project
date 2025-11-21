"""EMA scheduling and response handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Dict, Optional

from .config import EmaConfig
from .kalman import Estimate

logger = logging.getLogger(__name__)


class SchedulerState(str, Enum):
    DORMANT = "dormant"
    HARD_SUPPRESSED = "hard_suppressed"
    CONTEXT_SUPPRESSED = "context_suppressed"
    SNOOZED = "snoozed"
    COOLDOWN = "cooldown"
    AWAITING_RESPONSE = "awaiting_response"
    ELIGIBLE = "eligible"


@dataclass
class PromptDecision:
    should_prompt: bool
    reason: str
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    state: SchedulerState = SchedulerState.ELIGIBLE
    next_eligible_at: Optional[datetime] = None


@dataclass
class SchedulerStatus:
    state: SchedulerState
    suppression_reason: Optional[str]
    cooldown_until: Optional[datetime]
    snoozed_until: Optional[datetime]
    consent_granted: bool
    privacy_pause: bool
    next_prompt_candidate: Optional[datetime]


class EmaScheduler:
    def __init__(self, config: EmaConfig) -> None:
        self.config = config
        self.last_prompt_at: Optional[datetime] = None
        self.cooldown_until: Optional[datetime] = None
        self.snoozed_until: Optional[datetime] = None
        self.awaiting_response = False
        self.context_blocked_until: Optional[datetime] = None
        self.context_reason: Optional[str] = None
        self.consent_granted = True
        self.privacy_pause = False
        self._next_prompt_candidate: Optional[datetime] = None

    def _expire_awaiting(self, now: datetime) -> None:
        """Clear stale awaiting-response state so the scheduler can't get stuck."""
        if not self.awaiting_response or not self.last_prompt_at:
            return
        elapsed = (now - self.last_prompt_at).total_seconds()
        timeout = max(
            float(self.config.min_seconds_between_prompts) * 2,
            float(self.config.cooldown_on_dismiss_seconds),
        )
        if elapsed > timeout:
            logger.info(
                "EMA awaiting_response expired after %.1fs; clearing and entering cooldown",
                elapsed,
            )
            self.awaiting_response = False
            self.snoozed_until = None
            self.cooldown_until = now + timedelta(seconds=self.config.min_seconds_between_prompts)

    def evaluate(
        self,
        estimate: Estimate,
        now: datetime,
        context_flags: Optional[Dict[str, str]] = None,
    ) -> PromptDecision:
        context_flags = context_flags or {}
        self._update_context(context_flags, now)
        state = SchedulerState.ELIGIBLE
        self._expire_awaiting(now)

        if not self.consent_granted:
            state = SchedulerState.DORMANT
            logger.debug("EMA suppressed: no consent")
            return PromptDecision(False, "no_consent", True, "no_consent", state)

        if self.privacy_pause:
            state = SchedulerState.HARD_SUPPRESSED
            logger.debug("EMA suppressed: privacy pause")
            return PromptDecision(False, "privacy_pause", True, "privacy_pause", state)

        if self.context_blocked_until and now < self.context_blocked_until:
            state = SchedulerState.CONTEXT_SUPPRESSED
            logger.debug("EMA suppressed: context %s", self.context_reason)
            return PromptDecision(
                False,
                "context",
                True,
                self.context_reason or "context_blocked",
                state,
                self.context_blocked_until,
            )

        if self.awaiting_response:
            state = SchedulerState.AWAITING_RESPONSE
            logger.debug("EMA suppressed: awaiting previous response")
            return PromptDecision(False, "awaiting_response", True, "awaiting_response", state)

        if self.snoozed_until and now < self.snoozed_until:
            state = SchedulerState.SNOOZED
            logger.debug("EMA suppressed: snoozed until %s", self.snoozed_until)
            return PromptDecision(False, "snoozed", True, "snoozed", state, self.snoozed_until)

        if self.cooldown_until and now < self.cooldown_until:
            state = SchedulerState.COOLDOWN
            logger.debug("EMA suppressed: cooldown until %s", self.cooldown_until)
            return PromptDecision(
                False,
                "cooldown",
                True,
                "adaptive_cooldown",
                state,
                self.cooldown_until,
            )

        if self.last_prompt_at and (now - self.last_prompt_at).total_seconds() < self.config.min_seconds_between_prompts:
            spacing_target = self.last_prompt_at + timedelta(seconds=self.config.min_seconds_between_prompts)
            state = SchedulerState.COOLDOWN
            logger.debug("EMA suppressed: minimum spacing until %s", spacing_target)
            return PromptDecision(
                False,
                "cadence",
                True,
                "minimum_spacing",
                state,
                spacing_target,
            )

        next_interval = self._adaptive_interval(estimate)
        self._next_prompt_candidate = now + timedelta(seconds=next_interval)

        if estimate.variance >= self.config.trigger_uncertainty_threshold:
            logger.debug("EMA eligible due to variance %.3f", estimate.variance)
            return PromptDecision(True, "uncertainty", state=SchedulerState.ELIGIBLE)

        if abs(estimate.residual) >= self.config.trigger_residual_threshold:
            logger.debug("EMA eligible due to residual %.3f", estimate.residual)
            return PromptDecision(True, "residual", state=SchedulerState.ELIGIBLE)

        logger.debug("EMA stable, no prompt")
        return PromptDecision(False, "stable", state=SchedulerState.ELIGIBLE)

    def record_prompt(self, now: datetime) -> None:
        self.last_prompt_at = now
        self.awaiting_response = True
        self.snoozed_until = None

    def record_response(self, disposition: str, now: datetime) -> None:
        self.awaiting_response = False
        disposition = disposition.lower()
        if disposition in {"dismissed", "snoozed"}:
            self.snoozed_until = now + timedelta(seconds=self.config.cooldown_on_dismiss_seconds)
            self.cooldown_until = None
        elif disposition == "timeout":
            self.cooldown_until = now + timedelta(seconds=self.config.min_seconds_between_prompts // 2)
            self.snoozed_until = None
        else:
            adaptive = self._next_prompt_candidate or (
                now + timedelta(seconds=self.config.min_seconds_between_prompts)
            )
            self.cooldown_until = adaptive
            self.snoozed_until = None

    def set_privacy_pause(self, active: bool) -> None:
        self.privacy_pause = active
        if active:
            self.awaiting_response = False

    def set_consent(self, granted: bool) -> None:
        self.consent_granted = granted
        if not granted:
            self.awaiting_response = False
            self.last_prompt_at = None

    def _update_context(self, context_flags: Dict[str, str], now: datetime) -> None:
        if context_flags:
            self.context_reason = ", ".join(context_flags.values())
            self.context_blocked_until = now + timedelta(seconds=30)
        elif self.context_blocked_until and now >= self.context_blocked_until:
            self.context_blocked_until = None
            self.context_reason = None

    def _adaptive_interval(self, estimate: Estimate) -> float:
        base = float(self.config.min_seconds_between_prompts)
        residual_factor = min(1.5, max(0.5, abs(estimate.residual) * 2))
        variance_factor = 1.0 + min(1.0, estimate.variance * 2)
        return base * (residual_factor + variance_factor) / 2

    def status(self, now: Optional[datetime] = None) -> SchedulerStatus:
        now = now or datetime.now(timezone.utc)
        self._expire_awaiting(now)
        suppression_reason = self.context_reason
        state = SchedulerState.ELIGIBLE
        if not self.consent_granted:
            state = SchedulerState.DORMANT
            suppression_reason = "no_consent"
        elif self.privacy_pause:
            state = SchedulerState.HARD_SUPPRESSED
            suppression_reason = "privacy_pause"
        elif self.context_blocked_until and now < self.context_blocked_until:
            state = SchedulerState.CONTEXT_SUPPRESSED
        elif self.awaiting_response:
            state = SchedulerState.AWAITING_RESPONSE
        elif self.snoozed_until and now < self.snoozed_until:
            state = SchedulerState.SNOOZED
            suppression_reason = "snoozed"
        elif self.cooldown_until and now < self.cooldown_until:
            state = SchedulerState.COOLDOWN
            suppression_reason = "cooldown"

        return SchedulerStatus(
            state=state,
            suppression_reason=suppression_reason,
            cooldown_until=self.cooldown_until,
            snoozed_until=self.snoozed_until,
            consent_granted=self.consent_granted,
            privacy_pause=self.privacy_pause,
            next_prompt_candidate=self._next_prompt_candidate,
        )
