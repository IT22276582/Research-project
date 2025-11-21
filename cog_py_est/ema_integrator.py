"""EMA fusion helper that replays labelled windows into the estimator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import numpy as np


@dataclass
class PendingAssimilation:
    prompt_id: int
    features: np.ndarray
    timestamp: datetime
    label: Optional[float] = None


class EMAIntegrator:
    """Tracks prompt windows and emits labelled observations once responses arrive."""

    def __init__(self) -> None:
        self._pending: Dict[int, PendingAssimilation] = {}

    def register_prompt(self, prompt_id: int, features: np.ndarray, timestamp: datetime) -> None:
        self._pending[prompt_id] = PendingAssimilation(prompt_id, features, timestamp, None)

    def submit_response(self, prompt_id: int, label: float) -> None:
        pending = self._pending.get(prompt_id)
        if pending:
            pending.label = label

    def ready_observations(self) -> Iterable[PendingAssimilation]:
        ready: List[PendingAssimilation] = []
        for prompt_id, pending in list(self._pending.items()):
            if pending.label is None:
                continue
            ready.append(pending)
            del self._pending[prompt_id]
        return ready
