"""Crop Android status / navigation chrome from screenshots.

Store frames look cleaner without the live status bar + 3-button nav.
Detects bar heights from pixels when possible; falls back to height fractions.
Requires Pillow.
"""

from __future__ import annotations

from pathlib import Path


def _row_is_black(pixels: list[tuple[int, int, int]], *, thresh: int = 28, ratio: float = 0.86) -> bool:
    if not pixels:
        return False
    dark = sum(1 for r, g, b in pixels if r <= thresh and g <= thresh and b <= thresh)
    return dark / len(pixels) >= ratio


def _row_mean(pixels: list[tuple[int, int, int]]) -> tuple[float, float, float]:
    n = max(1, len(pixels))
    return (
        sum(p[0] for p in pixels) / n,
        sum(p[1] for p in pixels) / n,
        sum(p[2] for p in pixels) / n,
    )


def _sample_row(im, y: int, step: int = 8) -> list[tuple[int, int, int]]:
    w, _ = im.size
    return [im.getpixel((x, y))[:3] for x in range(0, w, step)]


def detect_nav_height(im, *, max_frac: float = 0.12) -> int:
    """Black 3-button / gesture hint bar from the bottom."""
    _, h = im.size
    limit = max(8, int(h * max_frac))
    nav = 0
    for dy in range(limit):
        y = h - 1 - dy
        if _row_is_black(_sample_row(im, y)):
            nav = dy + 1
        elif nav > 4:
            break
        else:
            nav = 0
    return nav


def detect_status_height(im, *, max_frac: float = 0.08, min_frac: float = 0.028) -> int:
    """Status strip: thin top band before the app's dominant content color."""
    _, h = im.size
    lo = max(8, int(h * min_frac))
    hi = max(lo + 4, int(h * max_frac))
    # Sample a reference band below the likely status area.
    ref_y = min(h - 1, int(h * 0.12))
    ref = _row_mean(_sample_row(im, ref_y))
    cut = lo
    for y in range(lo, hi):
        mean = _row_mean(_sample_row(im, y))
        # Large jump toward saturated/content color → status ended above.
        delta = abs(mean[0] - ref[0]) + abs(mean[1] - ref[1]) + abs(mean[2] - ref[2])
        if delta < 35:
            cut = y
            break
        cut = y
    return cut


def crop_system_chrome(
    src: str | Path,
    dest: str | Path | None = None,
    *,
    status: bool = True,
    nav: bool = True,
    status_frac: float = 0.042,
    nav_frac: float = 0.068,
) -> str:
    """Crop top status and/or bottom nav bars. Returns output path."""
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow required for chrome crop (pip install Pillow)") from e

    src_p = Path(src)
    dest_p = Path(dest) if dest else src_p
    with Image.open(src_p) as im:
        im = im.convert("RGBA")
        w, h = im.size
        top = 0
        bottom = h
        if status:
            detected = detect_status_height(im)
            frac = int(h * status_frac)
            top = max(detected, frac)
        if nav:
            detected = detect_nav_height(im)
            frac = int(h * nav_frac)
            bottom = h - max(detected, frac)
        if bottom <= top + 8:
            raise RuntimeError(f"chrome crop too aggressive for {src_p} ({w}x{h})")
        cropped = im.crop((0, top, w, bottom))
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(dest_p, "PNG")
    return str(dest_p)


def crop_dir(
    directory: str | Path,
    *,
    status: bool = True,
    nav: bool = True,
    pattern: str = "shot_*.png",
) -> list[str]:
    out: list[str] = []
    d = Path(directory)
    for p in sorted(d.glob(pattern)):
        out.append(crop_system_chrome(p, p, status=status, nav=nav))
    return out
