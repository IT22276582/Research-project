import tempfile
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from cog_py_est.app import create_app


def _write_test_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "test_config.toml"
    config_path.write_text(
        f"""
[window]
window_seconds = 1.0
hop_seconds = 1.0
inactivity_gap_seconds = 0.1

[storage]
path = "{(tmp_path / "state.db").as_posix()}"
enable_retention_prune = false
retention_hours = 1

[permissions]
consent_log_path = "{(tmp_path / "consent_log.jsonl").as_posix()}"
state_path = "{(tmp_path / "permissions_state.json").as_posix()}"
idle_block_seconds = 0

[export]
enabled = false
output_dir = "{(tmp_path / "exports").as_posix()}"
require_review = false
""",
        encoding="utf-8",
    )
    return config_path


class AppApiIntegrationTest(unittest.TestCase):
    def test_ingest_event_and_permissions_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_test_config(Path(tmp_dir))
            app = create_app(config_path)

            with TestClient(app) as client:
                health = client.get("/health")
                self.assertEqual(health.status_code, 200)
                self.assertEqual(health.json()["status"], "ok")

                payload = {"source": "keyboard", "payload": {"latency_ms": 88}}
                resp = client.post("/events", json=payload)
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.json()["accepted"])

                permissions = client.get("/permissions").json()
                self.assertIn("consent_granted", permissions)
                self.assertIn("privacy_pause", permissions)


if __name__ == "__main__":
    unittest.main()
