"""Perceptual hashing for screenshot deduplication.

Used by `agent pass --dedup` to avoid returning N near-identical frames when
an auto-swipe keeps landing on the same screen (menus, carousels that loop,
etc.). Pillow (already a Bridge runtime dependency for chrome cropping) does
the heavy lifting; no new dependencies.

If Pillow is unavailable the helpers degrade: `average_hash` returns `None` and
`is_similar` falls back to byte-equality, so `--dedup` never crashes a capture
session - it just becomes a no-op.
"""
from __future__ import annotations

from pathlib import Path

# 8x8 grid -> 64-bit average hash. Tuned for "same screen vs. different screen".
_HASH_SIZE = 8


def average_hash(path: str | Path, size: int = _HASH_SIZE) -> int | None:
    """Return a 64-bit average hash of the image at `path`, or `None` if the
    image can't be read (or Pillow is missing)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            small = img.convert("L").resize((size, size))
    except Exception:
        return None
    px = list(small.getdata())
    if not px:
        return None
    avg = sum(px) / len(px)
    bits = 0
    for i, value in enumerate(px):
        if value >= avg:
            bits |= 1 << (len(px) - 1 - i)
    return bits


def hamming(a: int, b: int) -> int:
    """Hamming distance between two integer hashes (popcount of XOR)."""
    return bin(a ^ b).count("1")


def is_similar(
    path_a: str | Path,
    path_b: str | Path,
    threshold: int = 8,
) -> bool:
    """`True` when two images are perceptually near-identical.

    Compares average-hash Hamming distance; below `threshold` bits means "same
    screen". Falls back to byte-equality when Pillow isn't available, and
    returns `False` (treat as distinct) when either file is unreadable so the
    crawler never drops a frame it can't hash.
    """
    ha = average_hash(path_a)
    hb = average_hash(path_b)
    if ha is None or hb is None:
        try:
            return Path(path_a).read_bytes() == Path(path_b).read_bytes()
        except OSError:
            return False
    return hamming(ha, hb) < threshold
