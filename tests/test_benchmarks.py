from datetime import datetime, timedelta, timezone
from time import perf_counter
import unittest

import numpy as np

from cog_py_est.config import EstimatorConfig
from cog_py_est.events import Event
from cog_py_est.features import FEATURE_VECTOR_DIM, fuse_features
from cog_py_est.kalman import KalmanEstimator


def _synthetic_events(start: datetime, count: int = 40) -> list[Event]:
    events: list[Event] = []
    for i in range(count):
        ts = start + timedelta(milliseconds=10 * i)
        if i % 2 == 0:
            events.append(
                Event(timestamp=ts, source="keyboard", payload={"latency_ms": 90 + i, "is_error": i % 5 == 0})
            )
        else:
            events.append(
                Event(
                    timestamp=ts,
                    source="pointer",
                    payload={"dx": 1.0 + i * 0.1, "dy": 0.5, "dt_ms": 10 + (i % 3)},
                )
            )
    return events


class BenchmarkTests(unittest.TestCase):
    def test_feature_fusion_throughput(self) -> None:
        now = datetime.now(timezone.utc)
        iterations = 180
        last_vector = np.zeros(FEATURE_VECTOR_DIM)

        start = perf_counter()
        for hop in range(iterations):
            window_start = now + timedelta(seconds=hop * 0.1)
            window_end = window_start + timedelta(seconds=60)
            fused = fuse_features(
                events=_synthetic_events(window_start),
                hop_index=hop,
                window_start=window_start,
                window_end=window_end,
                last_vector=last_vector,
            )
            last_vector = fused.vector
        elapsed = perf_counter() - start
        self.assertLess(elapsed, 1.0, f"Feature fusion too slow: {elapsed:.3f}s for {iterations} hops")

    def test_kalman_update_speed(self) -> None:
        estimator = KalmanEstimator(EstimatorConfig(), feature_dim=FEATURE_VECTOR_DIM)
        vec = np.ones(FEATURE_VECTOR_DIM)
        iterations = 400

        start = perf_counter()
        for _ in range(iterations):
            estimator.predict_update(vec, timestamp=datetime.now(timezone.utc), quality=1.0)
        elapsed = perf_counter() - start
        self.assertLess(elapsed, 1.0, f"Kalman updates too slow: {elapsed:.3f}s for {iterations} iterations")


if __name__ == "__main__":
    unittest.main()
