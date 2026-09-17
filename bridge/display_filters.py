"""Temporary display-filter bypass for store-true screenshots.

Samsung Eye comfort (`blue_light_filter`) is composited into `screencap`.
There is no ADB flag for “capture without filter.” We briefly disable known
filters, capture, then restore - screen may flash for ~100–300ms.
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Iterator


# (namespace, key) - Samsung + AOSP night light
_FILTER_KEYS: tuple[tuple[str, str], ...] = (
    ("system", "blue_light_filter"),
    ("secure", "night_display_activated"),
    ("secure", "reduce_bright_colors_activated"),
)


def _adb(serial: str | None, *args: str) -> subprocess.CompletedProcess:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, check=False)


def _get(serial: str | None, ns: str, key: str) -> str | None:
    r = _adb(serial, "shell", "settings", "get", ns, key)
    out = (r.stdout or b"").decode().strip()
    if r.returncode != 0 or out in ("", "null"):
        return None
    return out


def _put(serial: str | None, ns: str, key: str, value: str) -> None:
    _adb(serial, "shell", "settings", "put", ns, key, value)


@contextmanager
def true_color_display(serial: str | None = None, enabled: bool = True) -> Iterator[dict]:
    """Yield after filters off; restore previous values on exit.

    Returns a small report dict via the context value for agent logs.
    """
    report: dict = {"trueColor": bool(enabled), "changed": [], "restored": []}
    if not enabled:
        yield report
        return

    saved: list[tuple[str, str, str]] = []
    try:
        for ns, key in _FILTER_KEYS:
            prev = _get(serial, ns, key)
            if prev is None:
                continue
            if prev in ("0", "false", "False"):
                continue
            saved.append((ns, key, prev))
            _put(serial, ns, key, "0")
            report["changed"].append(f"{ns}.{key}={prev}->0")
        # Brief settle so compositor drops the tint
        import time

        if saved:
            time.sleep(0.15)
        yield report
    finally:
        for ns, key, prev in saved:
            _put(serial, ns, key, prev)
            report["restored"].append(f"{ns}.{key}={prev}")
