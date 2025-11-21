"""Optional OS hook ingestor that streams sanitized events to the service."""

from __future__ import annotations

import argparse
import asyncio
import time
import ctypes
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from pynput import keyboard, mouse


@dataclass
class PendingEvent:
    source: str
    payload: Dict[str, Any]
    timestamp: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _sender(queue: asyncio.Queue[PendingEvent], endpoint: str) -> None:
    async with httpx.AsyncClient() as client:
        while True:
            event = await queue.get()
            try:
                await client.post(
                    endpoint,
                    json={
                        "source": event.source,
                        "payload": event.payload,
                        "timestamp": event.timestamp.isoformat(),
                    },
                    timeout=5.0,
                )
            except Exception:
                # Best-effort; drop on errors to keep ingestion moving
                pass
            finally:
                queue.task_done()


def run_hooks(endpoint: str) -> None:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[PendingEvent] = asyncio.Queue(maxsize=2048)
    loop.create_task(_sender(queue, endpoint))
    loop.create_task(_context_poller(queue))

    last_key_time = time.perf_counter()
    last_mouse_time = time.perf_counter()

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        nonlocal last_key_time
        if key is None:
            return
        now_perf = time.perf_counter()
        dt = (now_perf - last_key_time) * 1000.0
        last_key_time = now_perf
        payload = {
            "latency_ms": dt,
            "is_error": False,
            "is_backspace": getattr(key, "vk", None) == 8,
        }
        loop.call_soon_threadsafe(
            queue.put_nowait,
            PendingEvent("keyboard", payload, _utc_now()),
        )

    def on_move(x: float, y: float) -> None:
        nonlocal last_mouse_time
        now_perf = time.perf_counter()
        dt = (now_perf - last_mouse_time) * 1000.0
        last_mouse_time = now_perf
        payload = {"dx": x, "dy": y, "dt_ms": dt}
        loop.call_soon_threadsafe(
            queue.put_nowait,
            PendingEvent("pointer", payload, _utc_now()),
        )

    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_move=on_move)
    keyboard_listener.start()
    mouse_listener.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        keyboard_listener.stop()
        mouse_listener.stop()
        loop.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream OS hook events to CLE service.")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8000/events",
        help="Events endpoint (default: http://127.0.0.1:8000/events)",
    )
    args = parser.parse_args()
    run_hooks(args.endpoint)


def _classify_context_label(focus: str) -> str:
    lowered = focus.lower()
    if any(token in lowered for token in ["teams", "zoom", "meet", "slack"]):
        return "collaboration"
    if any(token in lowered for token in ["outlook", "mail", "gmail"]):
        return "communication"
    if any(token in lowered for token in ["word", "docs", "notepad"]):
        return "writing"
    if any(token in lowered for token in ["excel", "sheets"]):
        return "analysis"
    return "other"


async def _context_poller(queue: asyncio.Queue[PendingEvent], interval: float = 1.5) -> None:
    last_payload: Dict[str, float | str | bool] | None = None
    while True:
        payload = _collect_context_payload()
        if payload and payload != last_payload:
            event = PendingEvent("system", payload, _utc_now())
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
            last_payload = payload
        await asyncio.sleep(interval)


def _collect_context_payload() -> Dict[str, float | str | bool]:
    focus = _active_window_title() or "unknown"
    idle_seconds = _idle_seconds()
    locked = idle_seconds > 600 or focus == "unknown"
    payload: Dict[str, float | str | bool] = {
        "focus_app": focus,
        "context_label": _classify_context_label(focus),
        "idle_seconds": float(idle_seconds),
        "locked": locked,
        "dnd": False,
    }
    return payload


def _active_window_title() -> str:
    system = platform.system()
    if system == "Windows":
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
    return ""


def _idle_seconds() -> float:
    system = platform.system()
    if system == "Windows":
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if user32.GetLastInputInfo(ctypes.byref(info)):
            millis = kernel32.GetTickCount() - info.dwTime
            return millis / 1000.0
    return 0.0


if __name__ == "__main__":
    main()
