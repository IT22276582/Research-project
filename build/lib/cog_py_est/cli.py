"""Command-line entry point for the estimator service."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .app import create_app
from .config import AppConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cognitive load estimator (Python)")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to TOML config (defaults to bundled example values)",
    )
    parser.add_argument("--host", type=str, default=None, help="Override bind host")
    parser.add_argument("--port", type=int, default=None, help="Override bind port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AppConfig.load(args.config)
    host = args.host or config.service.host
    port = args.port or config.service.port
    app = create_app(args.config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
