"""Live-mirror JPEG helper (no ADB required)."""

import io
import unittest

from PIL import Image

from bridge.capture import png_to_jpeg


def _png(w=200, h=400) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(20, 40, 60)).save(buf, format="PNG")
    return buf.getvalue()


class TestPngToJpeg(unittest.TestCase):
    def test_downscales_and_returns_jpeg(self):
        out = png_to_jpeg(_png(1080, 2400), max_width=540, quality=70)
        self.assertTrue(out.startswith(b"\xff\xd8"))  # JPEG SOI
        with Image.open(io.BytesIO(out)) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.width, 540)
            self.assertEqual(im.height, 1200)

    def test_keeps_small_images(self):
        out = png_to_jpeg(_png(320, 640), max_width=540, quality=80)
        with Image.open(io.BytesIO(out)) as im:
            self.assertEqual(im.width, 320)
            self.assertEqual(im.height, 640)


if __name__ == "__main__":
    unittest.main()
