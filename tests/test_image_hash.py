"""Tests for bridge.image_hash (perceptual dedup helpers).

No device / ADB required - these exercise the pure hashing logic with real
in-memory PNGs created via Pillow.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from bridge.image_hash import average_hash, hamming, is_similar


class TestImageHash(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _png(self, name: str, left: tuple, right: tuple) -> Path:
        """Half-left / half-right image so the *layout* (not just color) drives the hash."""
        p = self.tmp / name
        img = Image.new("RGB", (64, 64))
        px = img.load()
        for x in range(64):
            col = left if x < 32 else right
            for y in range(64):
                px[x, y] = col
        img.save(p)
        return p

    def test_identical_images_have_zero_distance(self):
        a = self._png("a.png", (30, 60, 90), (200, 220, 240))
        b = self._png("b.png", (30, 60, 90), (200, 220, 240))
        ha, hb = average_hash(a), average_hash(b)
        self.assertIsNotNone(ha)
        self.assertEqual(ha, hb)
        self.assertEqual(hamming(ha, hb), 0)
        self.assertTrue(is_similar(a, b))

    def test_opposite_layouts_are_not_similar(self):
        # Same colors, swapped halves -> same average luminance but different
        # spatial layout, so the average hash should diverge well past threshold.
        a = self._png("a.png", (20, 20, 20), (240, 240, 240))
        b = self._png("b.png", (240, 240, 240), (20, 20, 20))
        ha, hb = average_hash(a), average_hash(b)
        self.assertGreater(hamming(ha, hb), 8)
        self.assertFalse(is_similar(a, b))

    def test_near_identical_is_similar(self):
        a = self._png("a.png", (120, 80, 200), (210, 220, 230))
        b = self._png("b.png", (122, 82, 202), (212, 222, 232))
        self.assertTrue(is_similar(a, b))

    def test_hamming_distance_ints(self):
        self.assertEqual(hamming(0b1010, 0b0011), 2)  # 1001 -> 2 bits
        self.assertEqual(hamming(0, 0), 0)
        self.assertEqual(hamming(0xFFFFFFFF, 0x00000000), 32)

    def test_missing_file_is_not_similar(self):
        a = self._png("a.png", (1, 2, 3), (4, 5, 6))
        self.assertFalse(is_similar(a, self.tmp / "does_not_exist.png"))


if __name__ == "__main__":
    unittest.main()
