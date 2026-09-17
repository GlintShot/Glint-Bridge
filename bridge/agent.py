"""ADB-only sense/act primitives for agentic IDEs.

The IDE agent IS the planner (it already has a model), so these do no LLM
calls and need no GLINT_AI_API_KEY.

Prefer one-shot `pass` for store packs (fewer tokens than N tool roundtrips):
  python -m bridge.agent --serial S pass com.app --count 5

Usage (JSON on stdout):
  python -m bridge.agent [--serial S] screenshot [--no-true-color]
  python -m bridge.agent [--serial S] hierarchy [--package PKG]
  python -m bridge.agent [--serial S] tap X Y
  python -m bridge.agent [--serial S] scroll [forward|backward]
  python -m bridge.agent [--serial S] back
  python -m bridge.agent [--serial S] launch PKG
  python -m bridge.agent [--serial S] pass PKG [--count 5] [--settle 0.8]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def _adb(serial: str | None, *args: str) -> subprocess.CompletedProcess:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, check=False)


def cmd_screenshot(
    serial: str | None,
    filename: str | None,
    *,
    true_color: bool = True,
    crop_status: bool = True,
    crop_nav: bool = True,
) -> dict:
    from .capture import capture_screenshot
    from .display_filters import true_color_display
    from .session import update_session_with_capture

    with true_color_display(serial, enabled=true_color) as filt:
        path = capture_screenshot(serial=serial, filename=filename)
    if not path:
        return {"ok": False, "error": "screenshot failed - check device + USB debugging"}

    cropped = False
    if crop_status or crop_nav:
        try:
            from .chrome_crop import crop_system_chrome

            crop_system_chrome(path, path, status=crop_status, nav=crop_nav)
            cropped = True
        except RuntimeError:
            # Pillow missing - leave full frame; polish script can still crop.
            cropped = False

    session = update_session_with_capture(path)
    return {
        "ok": True,
        "path": path,
        "file": Path(path).name,
        "session": session,
        "trueColor": filt.get("trueColor"),
        "filters": filt.get("changed") or [],
        "chromeCropped": cropped,
    }


def _dump_hierarchy_xml(serial: str | None) -> str:
    """Prefer file dump - more reliable than exec-out on some Samsung builds."""
    remote = "/sdcard/glint_uidump.xml"
    r = _adb(serial, "shell", "uiautomator", "dump", remote)
    if r.returncode == 0:
        r2 = _adb(serial, "shell", "cat", remote)
        raw = (r2.stdout or b"").decode("utf-8", "replace")
        if "<?xml" in raw or "<node" in raw:
            return raw
    r = _adb(serial, "exec-out", "uiautomator", "dump", "/dev/tty")
    return (r.stdout or b"").decode("utf-8", "replace")


def cmd_hierarchy(serial: str | None, package: str = "") -> dict:
    from .ai_planner import summarize_android_hierarchy

    raw = _dump_hierarchy_xml(serial)
    start = raw.find("<?xml")
    xml = raw[start:] if start >= 0 else raw
    if not xml.strip().startswith("<?xml") and "<node" not in xml:
        return {"ok": False, "error": "hierarchy dump failed"}
    summary = summarize_android_hierarchy(xml, package=package)
    # Compact for tokens: short target list + text sample only
    targets = []
    for t in summary.targets[:24]:
        cx = cy = None
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", t.bounds or "")
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        targets.append(
            {
                "id": t.id,
                "label": t.label,
                "tap": [cx, cy] if cx is not None else None,
                "scroll": t.scrollable,
            }
        )
    return {
        "ok": True,
        "n": len(targets),
        "text": summary.text_sample[:12],
        "targets": targets,
    }


def cmd_tap(serial: str | None, x: int, y: int) -> dict:
    r = _adb(serial, "shell", "input", "tap", str(x), str(y))
    return {"ok": r.returncode == 0}


def _window_size(serial: str | None) -> tuple[int, int]:
    r = _adb(serial, "shell", "wm", "size")
    out = ((r.stdout or b"").decode() or "") + ((r.stderr or b"").decode() or "")
    m = re.search(r"(\d+)\s*x\s*(\d+)", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1080, 2400


def cmd_scroll(serial: str | None, direction: str = "forward") -> dict:
    """Vertical scroll (list) or horizontal pager swipe.

    direction: forward|backward (vertical), left|right (horizontal / ViewPager).
    """
    w, h = _window_size(serial)
    if direction in ("left", "next"):
        # Next page in a horizontal pager
        args = [
            "shell", "input", "swipe",
            str(int(w * 0.82)), str(h // 2),
            str(int(w * 0.18)), str(h // 2),
            "280",
        ]
        axis = "horizontal"
    elif direction in ("right", "prev"):
        args = [
            "shell", "input", "swipe",
            str(int(w * 0.18)), str(h // 2),
            str(int(w * 0.82)), str(h // 2),
            "280",
        ]
        axis = "horizontal"
    else:
        x = w // 2
        if direction == "backward":
            args = ["shell", "input", "swipe", str(x), str(int(h * 0.25)), str(x), str(int(h * 0.75)), "400"]
        else:
            args = ["shell", "input", "swipe", str(x), str(int(h * 0.75)), str(x), str(int(h * 0.25)), "400"]
        axis = "vertical"
    r = _adb(serial, *args)
    return {"ok": r.returncode == 0, "direction": direction, "axis": axis}


def cmd_back(serial: str | None) -> dict:
    r = _adb(serial, "shell", "input", "keyevent", "4")
    return {"ok": r.returncode == 0}


def cmd_launch(serial: str | None, package: str) -> dict:
    r = _adb(serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
    out = ((r.stdout or b"").decode() or "")[-300:]
    return {"ok": r.returncode == 0, "package": package, "output": out}


def cmd_pass(
    serial: str | None,
    package: str,
    *,
    count: int = 5,
    settle: float = 0.9,
    true_color: bool = True,
    clear: bool = True,
    swipe: str = "horizontal",
    crop_status: bool = True,
    crop_nav: bool = True,
    immersive: bool = True,
) -> dict:
    """One-shot store pack: launch → N screenshots with swipes between.

    Designed for agents: one JSON reply instead of 10+ tool calls.
    swipe: horizontal (pager apps) | vertical (lists)
    """
    from .capture import OUTPUT_DIR
    from .session import write_session
    from .system_chrome import immersive_chrome

    count = max(1, min(int(count), 10))
    if clear and OUTPUT_DIR.exists():
        for p in OUTPUT_DIR.glob("*.png"):
            p.unlink(missing_ok=True)
        sess = OUTPUT_DIR / "session.json"
        if sess.exists():
            sess.unlink(missing_ok=True)

    with immersive_chrome(
        serial,
        enabled=immersive,
        hide_status=crop_status,
        hide_nav=crop_nav,
    ):
        launch = cmd_launch(serial, package)
        if not launch.get("ok"):
            return {"ok": False, "error": "launch failed", "launch": launch}
        time.sleep(max(0.4, settle))

        between = "left" if swipe.startswith("h") else "forward"
        files: list[str] = []
        steps: list[dict] = []
        for i in range(count):
            name = f"shot_{i + 1:02d}.png"
            shot = cmd_screenshot(
                serial,
                name,
                true_color=true_color,
                crop_status=crop_status,
                crop_nav=crop_nav,
            )
            if not shot.get("ok"):
                steps.append({"i": i + 1, "ok": False, "error": shot.get("error")})
                break
            files.append(shot["file"])
            hier = cmd_hierarchy(serial, package)
            text = hier.get("text") if hier.get("ok") else []
            steps.append({
                "i": i + 1,
                "file": shot["file"],
                "text": (text or [])[:6],
                "chromeCropped": shot.get("chromeCropped"),
            })
            if i < count - 1:
                cmd_scroll(serial, between)
                time.sleep(max(0.35, settle * 0.6))

    if not files:
        return {"ok": False, "error": "no screenshots", "launch": launch, "steps": steps}

    session = write_session(files, store="play/phone", output_dir=OUTPUT_DIR)

    theme = None
    try:
        from .pack_inspect import extract_theme_from_paths

        theme = extract_theme_from_paths([OUTPUT_DIR / f for f in files])
        (OUTPUT_DIR / "theme.json").write_text(json.dumps({"theme": theme}, indent=2))
    except Exception:
        theme = None

    return {
        "ok": True,
        "package": package,
        "count": len(files),
        "files": files,
        "dir": str(OUTPUT_DIR),
        "session": session,
        "theme": theme,
        "themeFile": str(OUTPUT_DIR / "theme.json") if theme else None,
        "trueColor": true_color,
        "cropStatus": crop_status,
        "cropNav": crop_nav,
        "swipe": swipe,
        "steps": steps,
        "next": "node Glint-Web/scripts/polish-session.mjs --session <dir> --out store.zip",
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="glint-bridge-agent")
    p.add_argument("--serial", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("screenshot")
    s.add_argument("--filename", default=None)
    s.add_argument("--no-true-color", action="store_true")
    s.add_argument("--keep-status", action="store_true", help="Do not crop status bar")
    s.add_argument("--keep-nav", action="store_true", help="Do not crop nav bar")

    h = sub.add_parser("hierarchy")
    h.add_argument("--package", default="")

    t = sub.add_parser("tap")
    t.add_argument("x", type=int)
    t.add_argument("y", type=int)

    sc = sub.add_parser("scroll")
    sc.add_argument(
        "direction",
        nargs="?",
        default="forward",
        choices=["forward", "backward", "left", "right", "next", "prev"],
    )

    sub.add_parser("back")

    la = sub.add_parser("launch")
    la.add_argument("package")

    pa = sub.add_parser("pass", help="One-shot launch + N screenshots (token-cheap)")
    pa.add_argument("package")
    pa.add_argument("--count", type=int, default=5)
    pa.add_argument("--settle", type=float, default=0.9)
    pa.add_argument("--no-true-color", action="store_true")
    pa.add_argument("--keep-output", action="store_true", help="Do not clear output/ first")
    pa.add_argument(
        "--swipe",
        default="horizontal",
        choices=["horizontal", "vertical"],
        help="Pager apps: horizontal (default). Lists: vertical.",
    )
    pa.add_argument("--keep-status", action="store_true")
    pa.add_argument("--keep-nav", action="store_true")
    pa.add_argument("--no-immersive", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "screenshot":
        res = cmd_screenshot(
            args.serial,
            args.filename,
            true_color=not args.no_true_color,
            crop_status=not args.keep_status,
            crop_nav=not args.keep_nav,
        )
    elif args.cmd == "hierarchy":
        res = cmd_hierarchy(args.serial, args.package)
    elif args.cmd == "tap":
        res = cmd_tap(args.serial, args.x, args.y)
    elif args.cmd == "scroll":
        res = cmd_scroll(args.serial, args.direction)
    elif args.cmd == "back":
        res = cmd_back(args.serial)
    elif args.cmd == "launch":
        res = cmd_launch(args.serial, args.package)
    elif args.cmd == "pass":
        res = cmd_pass(
            args.serial,
            args.package,
            count=args.count,
            settle=args.settle,
            true_color=not args.no_true_color,
            clear=not args.keep_output,
            swipe=args.swipe,
            crop_status=not args.keep_status,
            crop_nav=not args.keep_nav,
            immersive=not args.no_immersive,
        )
    else:
        res = {"ok": False, "error": "unknown command"}
    print(json.dumps(res, separators=(",", ":")))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
