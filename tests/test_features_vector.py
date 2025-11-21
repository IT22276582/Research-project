from datetime import datetime, timedelta, timezone
import unittest

import numpy as np

from cog_py_est.events import Event
from cog_py_est.features import FEATURE_VECTOR_DIM, fuse_features


class FeatureVectorShapeTest(unittest.TestCase):
    def test_vector_length_and_imputation(self) -> None:
        now = datetime.now(timezone.utc)
        keyboard_event = Event(timestamp=now, source="keyboard", payload={"latency_ms": 120})
        last_vector = np.arange(FEATURE_VECTOR_DIM, dtype=float)

        window = fuse_features(
            events=[keyboard_event],
            hop_index=5,
            window_start=now,
            window_end=now + timedelta(seconds=60),
            last_vector=last_vector,
        )

        self.assertEqual(len(window.vector), FEATURE_VECTOR_DIM)
        # pointer segment should be imputed from the previous vector (positions 5-8)
        np.testing.assert_array_almost_equal(window.vector[5:9], last_vector[5:9])
        self.assertGreaterEqual(window.quality, 0.0)
        self.assertLessEqual(window.quality, 1.0)


if __name__ == "__main__":
    unittest.main()
