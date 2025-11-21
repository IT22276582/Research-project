from datetime import datetime, timedelta, timezone
import unittest

import numpy as np

from cog_py_est.config import EstimatorConfig
from cog_py_est.events import Event
from cog_py_est.features import fuse_features
from cog_py_est.kalman import KalmanEstimator


class FeatureFusionTest(unittest.TestCase):
    def test_fuse_returns_expected_length_and_quality(self) -> None:
        now = datetime.now(timezone.utc)
        events = [
            Event(timestamp=now, source="keyboard", payload={"latency_ms": 140, "is_error": False}),
            Event(
                timestamp=now + timedelta(milliseconds=120),
                source="pointer",
                payload={"dx": 1.0, "dy": 1.0, "dt_ms": 16},
            ),
        ]
        window = fuse_features(events, hop_index=1, window_start=now, window_end=now + timedelta(seconds=60))
        self.assertEqual(len(window.vector), 10)
        self.assertGreaterEqual(window.quality, 0.0)
        self.assertLessEqual(window.quality, 1.0)


class KalmanTest(unittest.TestCase):
    def test_kalman_predict_update_runs(self) -> None:
        estimator = KalmanEstimator(EstimatorConfig(), feature_dim=10)
        vec = np.zeros(10)
        estimate = estimator.predict_update(vec, timestamp=datetime.now(timezone.utc), quality=1.0)
        self.assertIsNotNone(estimate.load)
        self.assertGreaterEqual(estimate.variance, 0.0)


if __name__ == "__main__":
    unittest.main()
