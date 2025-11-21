"""Platform-specific context monitor (focus app, idle, DND)."""

from __future__ import annotations

import asyncio
import ctypes
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ContextCallback = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class ContextSnapshot:
    focus_app: str
    process_name: str
    idle_seconds: float
    locked: bool
    dnd: bool
    context_label: str
    running_apps: List[str]


class ContextMonitor:
    def __init__(self, callback: ContextCallback, interval_seconds: float = 2.0) -> None:
        self.callback = callback
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while self._running:
            payload = self._collect_payload()
            if payload:
                await self.callback(payload)
            await asyncio.sleep(self.interval)

    def _collect_payload(self) -> Optional[Dict[str, Any]]:
        snapshot = self._snapshot_for_platform()
        if snapshot is None:
            return None
        return {
            "focus_app": snapshot.focus_app,
            "focus_process": snapshot.process_name,
            "context_label": snapshot.context_label,
            "idle_seconds": snapshot.idle_seconds,
            "locked": snapshot.locked,
            "dnd": snapshot.dnd,
            "running_apps": snapshot.running_apps,
            "captured_at": _utc_iso(),
        }

    def _snapshot_for_platform(self) -> Optional[ContextSnapshot]:
        system = platform.system()
        if system == "Windows":
            return self._snapshot_windows()
        if system == "Darwin":
            return self._snapshot_macos()
        return self._snapshot_linux()

    def _snapshot_windows(self) -> Optional[ContextSnapshot]:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        hwnd = user32.GetForegroundWindow()
        title = ""
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "unknown"

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        idle_seconds = 0.0
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetLastInputInfo(ctypes.byref(info)):
            millis = kernel32.GetTickCount() - info.dwTime
            idle_seconds = millis / 1000.0

        process_name = _process_name_from_window(hwnd)
        friendly_name = _friendly_app_name(process_name, title)
        running_apps = _running_apps_windows(friendly_name)
        locked = idle_seconds > 900 or not hwnd
        context_label = _classify_label(title)
        return ContextSnapshot(
            focus_app=friendly_name or (title or "unknown"),
            process_name=process_name or "unknown",
            idle_seconds=idle_seconds,
            locked=locked,
            dnd=_windows_dnd_enabled(),
            context_label=context_label,
            running_apps=running_apps,
        )

    def _snapshot_macos(self) -> Optional[ContextSnapshot]:
        idle_seconds = _mac_idle_seconds()
        locked = idle_seconds > 900
        return ContextSnapshot(
            focus_app="Unknown app",
            process_name="unknown",
            idle_seconds=idle_seconds,
            locked=locked,
            dnd=_mac_dnd_enabled(),
            context_label="other",
            running_apps=[],
        )

    def _snapshot_linux(self) -> Optional[ContextSnapshot]:
        idle_seconds = _linux_idle_seconds()
        locked = idle_seconds > 900
        return ContextSnapshot(
            focus_app="Unknown app",
            process_name="unknown",
            idle_seconds=idle_seconds,
            locked=locked,
            dnd=_linux_dnd_enabled(),
            context_label="other",
            running_apps=[],
        )


def _classify_label(name: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ["teams", "zoom", "meet", "slack"]):
        return "collaboration"
    if any(token in lowered for token in ["outlook", "mail", "gmail"]):
        return "communication"
    if any(token in lowered for token in ["word", "docs", "notepad"]):
        return "writing"
    if any(token in lowered for token in ["excel", "sheets"]):
        return "analysis"
    return "other"


_TITLE_HINTS = [
    "Microsoft Edge",
    "Google Chrome",
    "Mozilla Firefox",
    "Visual Studio Code",
    "PowerPoint",
    "Excel",
    "Word",
    "Outlook",
    "Teams",
    "Slack",
]

_FRIENDLY_OVERRIDES = {
    "msedge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "code": "Visual Studio Code",
    "powerpnt": "PowerPoint",
    "excel": "Excel",
    "word": "Word",
    "outlook": "Outlook",
    "teams": "Microsoft Teams",
    "slack": "Slack",
    "notepad": "Notepad",
    "spotify": "Spotify",
}


def _friendly_app_name(process_name: str, window_title: str) -> str:
    base = (process_name or "").lower().removesuffix(".exe")
    if base in _FRIENDLY_OVERRIDES:
        return _FRIENDLY_OVERRIDES[base]
    cleaned = base.replace("_", " ").strip()
    if cleaned:
        parts = []
        for token in cleaned.split():
            if len(token) <= 3:
                parts.append(token.upper())
            else:
                parts.append(token.capitalize())
        candidate = " ".join(parts)
        if candidate:
            return candidate
    title_candidate = _friendly_from_title(window_title)
    if title_candidate:
        return title_candidate
    if process_name:
        return Path(process_name).stem.capitalize()
    return window_title or "Unknown app"


def _friendly_from_title(title: str) -> str:
    lowered = title.lower()
    for token in _TITLE_HINTS:
        if token.lower() in lowered:
            return token
    segments = [segment.strip() for segment in title.split("-") if segment.strip()]
    if segments:
        candidate = segments[-1]
        return candidate[:64]
    return ""


def _process_name_from_window(hwnd: int) -> str:
    if not hwnd:
        return ""
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return _process_path_from_pid(pid.value)


def _process_path_from_pid(pid: int) -> str:
    if not pid:
        return ""
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(512)
        size = ctypes.wintypes.DWORD(len(buffer))
        query = getattr(kernel32, "QueryFullProcessImageNameW", None)
        if query:
            query.restype = ctypes.wintypes.BOOL
            query.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.LPWSTR,
                ctypes.POINTER(ctypes.wintypes.DWORD),
            ]
            if query(handle, 0, buffer, ctypes.byref(size)):
                return Path(buffer.value).name
        psapi = ctypes.windll.psapi  # type: ignore[attr-defined]
        psapi.GetModuleFileNameExW.restype = ctypes.wintypes.DWORD
        psapi.GetModuleFileNameExW.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.HMODULE,
            ctypes.wintypes.LPWSTR,
            ctypes.wintypes.DWORD,
        ]
        if psapi.GetModuleFileNameExW(handle, None, buffer, len(buffer)):
            return Path(buffer.value).name
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _running_apps_windows(focus_name: str) -> List[str]:
    if platform.system() != "Windows":
        return []
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    apps: List[str] = []
    seen: set[str] = set()

    def _append(name: str) -> None:
        normalized = (name or "").strip()
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        apps.append(normalized)

    _append(focus_name)

    @EnumWindowsProc
    def _enum_proc(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value or ""
        if not title.strip():
            return True
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = _process_path_from_pid(pid.value)
        friendly = _friendly_app_name(process_name, title)
        _append(friendly)
        return True

    try:
        EnumWindows(_enum_proc, 0)
    except Exception:
        pass
    return apps[:50]


def _windows_dnd_enabled() -> bool:
    """Best-effort detection of Windows Focus Assist."""
    try:
        import winreg  # type: ignore

        path = r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings\\NOC_GLOBAL_SETTING_TOASTS_ENABLED"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "")
            return value == 0
    except Exception:
        return False


def _mac_idle_seconds() -> float:
    """Try to read idle time from IORegistry; tolerate missing tools."""
    try:
        output = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], text=True)
        for line in output.splitlines():
            if "HIDIdleTime" in line:
                parts = line.strip().split(" = ")
                if len(parts) == 2:
                    nanoseconds = int(parts[1])
                    return nanoseconds / 1e9
    except Exception:
        return 0.0
    return 0.0


def _mac_dnd_enabled() -> bool:
    """Check macOS Focus/Do Not Disturb flag."""
    try:
        output = subprocess.check_output(
            [
                "defaults",
                "-currentHost",
                "read",
                "com.apple.notificationcenterui",
                "doNotDisturb",
            ],
            text=True,
        ).strip()
        return output in {"1", "true", "YES"}
    except Exception:
        return False


def _linux_idle_seconds() -> float:
    """Use xprintidle when available; otherwise 0."""
    try:
        output = subprocess.check_output(["xprintidle"], text=True).strip()
        millis = float(output)
        return millis / 1000.0
    except Exception:
        return 0.0


def _linux_dnd_enabled() -> bool:
    """Gnome Do Not Disturb detection; defaults to False if unavailable."""
    try:
        output = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.notifications", "show-banners"],
            text=True,
        ).strip()
        return output.lower() == "false"
    except Exception:
        return False
