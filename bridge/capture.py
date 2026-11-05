import io
import subprocess
import time
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _run_adb(args: list[str], capture: bool = True) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["adb"] + args,
            capture_output=capture,
            text=not capture,
            check=False,
        )
    except FileNotFoundError:
        return None


def capture_png_bytes(serial: str | None = None) -> bytes | None:
    """Raw PNG from `adb exec-out screencap -p`, or None on failure."""
    cmd = ["exec-out", "screencap", "-p"]
    if serial:
        cmd = ["-s", serial, *cmd]
    result = _run_adb(cmd)
    if result is None or result.returncode != 0:
        return None
    raw = result.stdout if isinstance(result.stdout, bytes) else b""
    return raw or None


def png_to_jpeg(
    png_bytes: bytes,
    max_width: int = 540,
    quality: int = 70,
) -> bytes:
    """Downscale PNG → JPEG for live mirror (smaller WS payloads)."""
    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as im:
        rgb = im.convert("RGB")
        if max_width > 0 and rgb.width > max_width:
            h = max(1, round(rgb.height * (max_width / rgb.width)))
            rgb = rgb.resize((max_width, h), Image.Resampling.BILINEAR)
        out = io.BytesIO()
        rgb.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()


def capture_frame_jpeg(
    serial: str | None = None,
    max_width: int = 540,
    quality: int = 70,
) -> bytes | None:
    """One live-mirror frame as JPEG bytes, or None if device/ADB fails."""
    png = capture_png_bytes(serial)
    if not png:
        return None
    try:
        return png_to_jpeg(png, max_width=max_width, quality=quality)
    except Exception:
        return None


def capture_screenshot(
    serial: str | None = None,
    filename: str | None = None,
) -> str | None:
    """Capture a single screenshot via ADB. Returns the file path or None."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        existing = list(OUTPUT_DIR.glob("screenshot_*.png"))
        num = len(existing) + 1
        filename = f"screenshot_{num:04d}.png"

    dest = OUTPUT_DIR / filename
    raw = capture_png_bytes(serial)
    if not raw:
        return None
    dest.write_bytes(raw)
    return str(dest)


def batch_capture(serial: str | None = None, count: int = 5, delay: float = 1.0) -> list[str]:
    """Capture N screenshots with delay between each. Returns list of file paths."""
    paths = []
    for i in range(count):
        path = capture_screenshot(serial, f"batch_{i+1:04d}.png")
        if path:
            paths.append(path)
        if i < count - 1:
            time.sleep(delay)
    return paths
