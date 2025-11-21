"""Local diagnostics console that queries SQLite directly."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from ..config import AppConfig


def load_config(path: Path | None) -> AppConfig:
    return AppConfig.load(path)


def fetch_rows(db_path: Path, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def show_summary(db_path: Path) -> None:
    rows = fetch_rows(
        db_path,
        """
        SELECT
            (SELECT COUNT(*) FROM input_events) AS events,
            (SELECT COUNT(*) FROM feature_windows) AS windows,
            (SELECT COUNT(*) FROM ema_prompts) AS prompts,
            (SELECT COUNT(*) FROM ema_responses) AS responses
        """,
    )
    if rows:
        row = rows[0]
        print_section("Record counts")
        for key in row.keys():
            print(f"{key:>12}: {row[key]}")


def show_policy_events(db_path: Path, limit: int = 10) -> None:
    rows = fetch_rows(
        db_path,
        """
        SELECT occurred_at, event_type, reason, metadata_json
        FROM policy_events
        ORDER BY occurred_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    print_section(f"Policy events (latest {limit})")
    if not rows:
        print("No events recorded.")
        return
    for row in rows:
        metadata = row["metadata_json"]
        metadata_str = ""
        if metadata:
            try:
                metadata_str = json.dumps(json.loads(metadata))
            except json.JSONDecodeError:
                metadata_str = metadata
        print(f"- {row['occurred_at']} • {row['event_type']} ({row['reason'] or 'n/a'}) {metadata_str}")


def show_metrics(db_path: Path, limit: int = 10) -> None:
    rows = fetch_rows(
        db_path,
        """
        SELECT snapshot_at, metric_type, metric_value, metadata_json
        FROM telemetry_metrics
        ORDER BY snapshot_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    print_section(f"Telemetry metrics (latest {limit})")
    if not rows:
        print("No metrics recorded.")
        return
    for row in rows:
        print(f"- {row['snapshot_at']} • {row['metric_type']} = {row['metric_value']}")


def show_consent_log(consent_path: Path) -> None:
    print_section("Consent history")
    if not consent_path.exists():
        print("Consent log not found.")
        return
    lines = [line for line in consent_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        print("No consent entries.")
        return
    for line in lines[-20:]:
        try:
            entry: Dict[str, Any] = json.loads(line)
            print(f"- {entry.get('timestamp')} granted={entry.get('granted')} reason={entry.get('reason')}")
        except json.JSONDecodeError:
            print(f"- {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local diagnostics console (no HTTP)")
    parser.add_argument("--config", type=Path, default=None, help="Path to policy TOML")
    args = parser.parse_args()

    config = load_config(args.config)
    db_path = config.storage.path
    show_summary(db_path)
    show_policy_events(db_path)
    show_metrics(db_path)
    show_consent_log(config.permissions.consent_log_path)


if __name__ == "__main__":
    main()
