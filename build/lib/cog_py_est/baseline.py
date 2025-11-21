"""Baseline calibrator orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np

from .features import FeatureWindow
from .kalman import Estimate


@dataclass
class BaselineStatus:
    active: bool
    prompt_ready: bool
    percent_complete: float
    onboarding_message: Optional[str]


class BaselineCalibrator:
    def __init__(self, baseline_minutes: int, target_variance: float) -> None:
        self.target_duration = timedelta(minutes=baseline_minutes)
        self.target_variance = target_variance
        self._start: Optional[datetime] = None
        self._prompt_sent = False
        self._completed = False
        self._vector_sum: Optional[np.ndarray] = None
        self._count = 0
        self._residuals: List[float] = []

    def record_window(self, window: FeatureWindow, estimate: Estimate) -> BaselineStatus:
        if self._completed:
            return BaselineStatus(False, False, 1.0, None)

        if self._start is None:
            self._start = window.window_start

        self._accumulate(window.vector, estimate.residual)
        elapsed = window.window_end - self._start
        percent = min(1.0, max(elapsed / self.target_duration, self._count / 10.0))

        recent_std = self._recent_residual_std()
        prompt_ready = (
            not self._prompt_sent
            and elapsed >= self.target_duration
            and (recent_std is None or recent_std <= self.target_variance * 1.5)
        )

        if self._prompt_sent and estimate.variance <= self.target_variance:
            if recent_std is None or recent_std <= self.target_variance * 1.5:
                self._completed = True
                percent = 1.0

        message = "Calibrating baseline..." if not self._completed else "Baseline complete"
        return BaselineStatus(
            active=not self._completed,
            prompt_ready=prompt_ready,
            percent_complete=float(percent),
            onboarding_message=message,
        )

    def mark_prompt_sent(self) -> None:
        self._prompt_sent = True

    def completed(self) -> bool:
        return self._completed

    def force_complete(self) -> None:
        self._prompt_sent = True
        self._completed = True

    def feature_mean(self) -> Optional[np.ndarray]:
        if not self._count or self._vector_sum is None:
            return None
        return self._vector_sum / self._count

    def residuals(self) -> List[float]:
        return list(self._residuals)

    def _accumulate(self, vector: np.ndarray, residual: float) -> None:
        if self._vector_sum is None:
            self._vector_sum = vector.astype(float)
        else:
            self._vector_sum = self._vector_sum + vector
        self._count += 1
        self._residuals.append(residual)

    def _recent_residual_std(self, sample: int = 5) -> Optional[float]:
        if not self._residuals:
            return None
        recent = self._residuals[-sample:]
        return float(np.std(recent))
