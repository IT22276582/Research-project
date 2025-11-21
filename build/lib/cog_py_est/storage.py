"""Async storage layer using SQLite (local-only, no network)."""

from __future__ import annotations

import json
from hashlib import sha256
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import numpy as np

from .events import Event
from .features import FeatureWindow
from .kalman import Estimate


def _dt(dt_val: datetime) -> str:
    return dt_val.isoformat()


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.db: Optional[aiosqlite.Connection] = None
        self.session_id: Optional[int] = None

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.path.as_posix())
        await self.db.execute("PRAGMA journal_mode=WAL;")
        await self._create_tables()
        await self.db.commit()

    async def _create_tables(self) -> None:
        db = self._require_db()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                device_label TEXT,
                consent_version TEXT
            );
            CREATE TABLE IF NOT EXISTS input_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                hop_index INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS feature_windows (
                window_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                hop_index INTEGER NOT NULL,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                feature_vector_json TEXT NOT NULL,
                quality_score REAL,
                ema_prompt_id INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS ema_prompts (
                prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                issued_at TEXT NOT NULL,
                trigger_reason TEXT,
                state TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS ema_responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                responded_at TEXT NOT NULL,
                rating INTEGER,
                disposition TEXT,
                note TEXT,
                FOREIGN KEY (prompt_id) REFERENCES ema_prompts(prompt_id)
            );
            CREATE TABLE IF NOT EXISTS model_state (
                state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                latent_mean REAL,
                latent_variance REAL,
                weights_json TEXT,
                forgetting_factor REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS telemetry_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                snapshot_at TEXT NOT NULL,
                metric_type TEXT,
                metric_value REAL,
                metadata_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS baseline_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                feature_mean_json TEXT NOT NULL,
                residual_mean REAL,
                residual_std REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS policy_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reason TEXT,
                metadata_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS aggregated_exports (
                export_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                reviewer TEXT,
                summary_json TEXT NOT NULL,
                file_path TEXT
            );
            """
        )

    async def start_session(
        self, consent_version: str = "v1", device_label: str = "workstation"
    ) -> int:
        db = self._require_db()
        now = datetime.utcnow()
        cursor = await db.execute(
            "INSERT INTO sessions (started_at, device_label, consent_version) VALUES (?, ?, ?)",
            (_dt(now), device_label, consent_version),
        )
        await db.commit()
        last_id = cursor.lastrowid
        if last_id is None:
            raise RuntimeError("failed to create session row")
        self.session_id = int(last_id)
        return self.session_id

    async def record_event(self, event: Event, hop_index: int) -> None:
        if self.db is None or self.session_id is None:
            return
        await self.db.execute(
            """
            INSERT INTO input_events (session_id, occurred_at, source, payload_json, hop_index)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                _dt(event.timestamp),
                event.source,
                json.dumps(event.payload),
                hop_index,
            ),
        )
        await self.db.commit()

    async def record_window(
        self, window: FeatureWindow, session_id: Optional[int], ema_prompt_id: Optional[int] = None
    ) -> None:
        if self.db is None or session_id is None:
            return
        payload = json.dumps(window.vector.tolist())
        await self.db.execute(
            """
            INSERT INTO feature_windows (session_id, hop_index, window_start, window_end, feature_vector_json, quality_score, ema_prompt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                window.hop_index,
                _dt(window.window_start),
                _dt(window.window_end),
                payload,
                window.quality,
                ema_prompt_id,
            ),
        )
        await self.db.commit()

    async def record_ema_prompt(self, reason: str, state: str = "delivered") -> Optional[int]:
        if self.db is None or self.session_id is None:
            return None
        now = datetime.utcnow()
        cursor = await self.db.execute(
            """
            INSERT INTO ema_prompts (session_id, issued_at, trigger_reason, state)
            VALUES (?, ?, ?, ?)
            """,
            (self.session_id, _dt(now), reason, state),
        )
        await self.db.commit()
        prompt_id = cursor.lastrowid
        return int(prompt_id) if prompt_id is not None else None

    async def update_ema_prompt_state(self, prompt_id: int, state: str) -> None:
        if self.db is None:
            return
        await self.db.execute(
            "UPDATE ema_prompts SET state = ? WHERE prompt_id = ?",
            (state, prompt_id),
        )
        await self.db.commit()

    async def fetch_latest_pending_prompt(self, timeout_seconds: int) -> Optional[Dict[str, Any]]:
        """Return the most recent delivered prompt with no response, respecting timeout."""
        if self.db is None:
            return None
        cursor = await self.db.execute(
            """
            SELECT p.prompt_id, p.issued_at, p.trigger_reason
            FROM ema_prompts p
            WHERE p.state = 'delivered'
              AND NOT EXISTS (SELECT 1 FROM ema_responses r WHERE r.prompt_id = p.prompt_id)
            ORDER BY p.issued_at DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        if not row:
            return None
        prompt_id, issued_at_str, reason = row
        issued_at = datetime.fromisoformat(issued_at_str)
        age = (datetime.utcnow() - issued_at).total_seconds()
        if age > timeout_seconds:
            await self.update_ema_prompt_state(prompt_id, "timeout")
            return None
        return {
            "prompt_id": int(prompt_id),
            "reason": reason,
            "issued_at": issued_at,
        }

    async def record_ema_response(
        self,
        prompt_id: int,
        rating: int,
        disposition: str,
        note: str | None = None,
    ) -> None:
        if self.db is None:
            return
        now = datetime.utcnow()
        await self.db.execute(
            """
            INSERT INTO ema_responses (prompt_id, responded_at, rating, disposition, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (prompt_id, _dt(now), rating, disposition, note),
        )
        await self.db.commit()

    async def save_model_state(self, estimate: Estimate, weights: np.ndarray, forgetting: float) -> None:
        if self.db is None or self.session_id is None:
            return
        await self.db.execute(
            """
            INSERT INTO model_state (session_id, captured_at, latent_mean, latent_variance, weights_json, forgetting_factor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                _dt(estimate.timestamp),
                estimate.load,
                estimate.variance,
                json.dumps(weights.tolist()),
                forgetting,
            ),
        )
        await self.db.commit()

    async def load_latest_model_state(self) -> Optional[Tuple[Estimate, np.ndarray, float]]:
        if self.db is None:
            return None
        cursor = await self.db.execute(
            """
            SELECT captured_at, latent_mean, latent_variance, weights_json, forgetting_factor
            FROM model_state
            ORDER BY captured_at DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        if not row:
            return None
        captured_at = datetime.fromisoformat(row[0])
        estimate = Estimate(
            timestamp=captured_at,
            load=row[1],
            variance=row[2],
            residual=0.0,
        )
        weights = np.array(json.loads(row[3]))
        forgetting = float(row[4]) if row[4] is not None else 1.0
        return estimate, weights, forgetting

    async def record_metric(
        self, metric_type: str, metric_value: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if self.db is None or self.session_id is None:
            return
        now = datetime.utcnow()
        await self.db.execute(
            """
            INSERT INTO telemetry_metrics (session_id, snapshot_at, metric_type, metric_value, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                _dt(now),
                metric_type,
                metric_value,
                json.dumps(metadata or {}),
            ),
        )
        await self.db.commit()

    async def close(self) -> None:
        if self.db is not None:
            if self.session_id is not None:
                await self.end_session()
            await self.db.close()

    async def end_session(self) -> None:
        """Mark the active session as ended."""
        if self.db is None or self.session_id is None:
            return
        await self.db.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ? AND ended_at IS NULL",
            (_dt(datetime.utcnow()), self.session_id),
        )
        await self.db.commit()

    async def prune_retention(self, retention_hours: int) -> None:
        if self.db is None:
            return
        cutoff = datetime.utcnow() - timedelta(hours=retention_hours)
        cutoff_iso = _dt(cutoff)
        prune_targets = [
            ("input_events", "occurred_at"),
            ("feature_windows", "window_end"),
            ("ema_prompts", "issued_at"),
            ("ema_responses", "responded_at"),
            ("model_state", "captured_at"),
            ("telemetry_metrics", "snapshot_at"),
            ("baseline_profiles", "captured_at"),
            ("policy_events", "occurred_at"),
        ]
        for table, column in prune_targets:
            await self.db.execute(
                f"DELETE FROM {table} WHERE {column} < ?",  # nosec - column names static
                (cutoff_iso,),
            )
        await self.db.commit()

    async def record_policy_event(
        self,
        event_type: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.db is None or self.session_id is None:
            return
        await self.db.execute(
            """
            INSERT INTO policy_events (session_id, occurred_at, event_type, reason, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                _dt(datetime.utcnow()),
                event_type,
                reason,
                json.dumps(metadata or {}),
            ),
        )
        await self.db.commit()
        return self.db

    async def fetch_policy_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        cursor = await self.db.execute(
            """
            SELECT occurred_at, event_type, reason, metadata_json
            FROM policy_events
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        events: List[Dict[str, Any]] = []
        for occurred_at, event_type, reason, metadata_json in rows:
            metadata: Dict[str, Any] = {}
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
            events.append(
                {
                    "occurred_at": occurred_at,
                    "event_type": event_type,
                    "reason": reason,
                    "metadata": metadata,
                }
            )
        return events

    async def record_baseline_profile(
        self, feature_mean: np.ndarray, residuals: List[float]
    ) -> None:
        if self.db is None or self.session_id is None:
            return
        residual_array = np.array(residuals, dtype=float) if residuals else np.zeros(1)
        await self.db.execute(
            """
            INSERT INTO baseline_profiles (session_id, captured_at, feature_mean_json, residual_mean, residual_std)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                _dt(datetime.utcnow()),
                json.dumps(feature_mean.tolist()),
                float(np.mean(residual_array)),
                float(np.std(residual_array)),
            ),
        )
        await self.db.commit()

    async def fetch_telemetry_metrics(self, limit: int = 200) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        cursor = await self.db.execute(
            """
            SELECT snapshot_at, metric_type, metric_value, metadata_json
            FROM telemetry_metrics
            ORDER BY snapshot_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        metrics: List[Dict[str, Any]] = []
        for snapshot_at, metric_type, metric_value, metadata_json in rows:
            metadata: Dict[str, Any] = {}
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
            metrics.append(
                {
                    "snapshot_at": snapshot_at,
                    "metric_type": metric_type,
                    "metric_value": metric_value,
                    "metadata": metadata,
                }
            )
        return metrics

    async def aggregated_summary(self) -> Dict[str, Any]:
        db = self._require_db()
        summary: Dict[str, Any] = {}

        async def scalar(query: str) -> int:
            cursor = await db.execute(query)
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

        summary["input_events"] = await scalar("SELECT COUNT(*) FROM input_events")
        summary["feature_windows"] = await scalar("SELECT COUNT(*) FROM feature_windows")
        summary["ema_prompts"] = await scalar("SELECT COUNT(*) FROM ema_prompts")
        summary["ema_responses"] = await scalar("SELECT COUNT(*) FROM ema_responses")

        cursor = await db.execute(
            "SELECT AVG(metric_value), MAX(metric_value) FROM telemetry_metrics WHERE metric_type = 'residual_rms'"
        )
        row = await cursor.fetchone()
        summary["residual_rms_avg"] = row[0] if row and row[0] is not None else 0.0
        summary["residual_rms_peak"] = row[1] if row and row[1] is not None else 0.0

        cursor = await db.execute(
            "SELECT AVG(metric_value) FROM telemetry_metrics WHERE metric_type = 'variance'"
        )
        row = await cursor.fetchone()
        summary["variance_avg"] = row[0] if row and row[0] is not None else 0.0

        cursor = await db.execute(
            "SELECT AVG(rating) FROM ema_responses WHERE disposition = 'completed'"
        )
        row = await cursor.fetchone()
        summary["ema_rating_avg"] = row[0] if row and row[0] is not None else None

        cursor = await db.execute(
            "SELECT MIN(started_at), MAX(ended_at) FROM sessions"
        )
        row = await cursor.fetchone()
        summary["session"] = {
            "started_at": row[0] if row and row[0] else None,
            "ended_at": row[1] if row and row[1] else None,
        }

        cursor = await db.execute(
            """
            SELECT MIN(window_start), MAX(window_end), MIN(hop_index), MAX(hop_index)
            FROM feature_windows
            """
        )
        row = await cursor.fetchone()
        summary["window_span"] = {
            "start": row[0] if row and row[0] else None,
            "end": row[1] if row and row[1] else None,
            "first_hop": row[2] if row and row[2] is not None else None,
            "last_hop": row[3] if row and row[3] is not None else None,
        }

        cursor = await db.execute(
            """
            SELECT reason, COUNT(*) as count
            FROM policy_events
            GROUP BY reason
            """
        )
        policy_reasons = {reason or "unknown": count for reason, count in await cursor.fetchall()}
        policy_total = sum(policy_reasons.values())
        summary["policy_events"] = policy_total
        summary["policy_reasons"] = policy_reasons

        cursor = await db.execute(
            """
            SELECT prompt_id, trigger_reason, state
            FROM ema_prompts
            ORDER BY prompt_id DESC
            LIMIT 20
            """
        )
        prompts = [
            {"prompt_id": pid, "reason": reason, "state": state}
            for pid, reason, state in await cursor.fetchall()
        ]
        summary["ema_prompts_recent"] = prompts

        summary["checksum"] = sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()

        return summary

    async def create_aggregated_export(
        self, summary: Dict[str, Any], status: str = "pending", reviewer: Optional[str] = None, file_path: Optional[str] = None
    ) -> int:
        db = self._require_db()
        cursor = await db.execute(
            """
            INSERT INTO aggregated_exports (created_at, status, reviewer, summary_json, file_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _dt(datetime.utcnow()),
                status,
                reviewer,
                json.dumps(summary),
                file_path,
            ),
        )
        await db.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("failed to create export record")
        return int(cursor.lastrowid)

    async def list_exports(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        if status:
            cursor = await self.db.execute(
                """
                SELECT export_id, created_at, status, reviewer, summary_json, file_path
                FROM aggregated_exports
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,),
            )
        else:
            cursor = await self.db.execute(
                """
                SELECT export_id, created_at, status, reviewer, summary_json, file_path
                FROM aggregated_exports
                ORDER BY created_at DESC
                """
            )
        rows = await cursor.fetchall()
        exports = []
        for export_id, created_at, status_val, reviewer, summary_json, file_path in rows:
            try:
                summary = json.loads(summary_json)
            except json.JSONDecodeError:
                summary = {}
            exports.append(
                {
                    "export_id": export_id,
                    "created_at": created_at,
                    "status": status_val,
                    "reviewer": reviewer,
                    "summary": summary,
                    "file_path": file_path,
                }
            )
        return exports

    async def update_export_status(
        self, export_id: int, status: str, reviewer: Optional[str] = None, file_path: Optional[str] = None
    ) -> None:
        if self.db is None:
            return
        await self.db.execute(
            """
            UPDATE aggregated_exports
            SET status = ?, reviewer = COALESCE(?, reviewer), file_path = COALESCE(?, file_path)
            WHERE export_id = ?
            """,
            (status, reviewer, file_path, export_id),
        )
        await self.db.commit()

    def _require_db(self) -> aiosqlite.Connection:
        if self.db is None:
            raise RuntimeError("database not initialized")
        return self.db
