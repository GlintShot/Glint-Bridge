"""Hide Android system bars during capture when the OEM allows it."""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from typing import Iterator


def _adb(serial: str | None, *args: str) -> subprocess.CompletedProcess:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, check=False)


@contextmanager
def immersive_chrome(
    serial: str | None = None,
    *,
    enabled: bool = True,
    hide_status: bool = True,
    hide_nav: bool = True,
) -> Iterator[dict]:
    """Best-effort immersive mode for cleaner shots. Always restores policy_control."""
    report = {"immersive": bool(enabled), "policy": None}
    if not enabled:
        yield report
        return

    prev = _adb(serial, "shell", "settings", "get", "global", "policy_control")
    prev_val = (prev.stdout or b"").decode().strip()
    if prev_val in ("", "null"):
        prev_val = None
    report["policy"] = prev_val

    # immersive.status / immersive.navigation / immersive.full
    if hide_status and hide_nav:
        mode = "immersive.full=*"
    elif hide_status:
        mode = "immersive.status=*"
    elif hide_nav:
        mode = "immersive.navigation=*"
    else:
        yield report
        return

    try:
        _adb(serial, "shell", "settings", "put", "global", "policy_control", mode)
        import time

        time.sleep(0.2)
        yield report
    finally:
        if prev_val is None:
            _adb(serial, "shell", "settings", "delete", "global", "policy_control")
        else:
            _adb(serial, "shell", "settings", "put", "global", "policy_control", prev_val)
