import json
import tempfile
import unittest
from pathlib import Path

from bridge.session import load_session, update_session_with_capture, write_session


class TestSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = Path(self.tmp)

    def test_write_and_load_session(self):
        path = write_session(
            screens=["home.png", "profile.png"],
            store="play",
            output_dir=self.out,
        )
        self.assertTrue(Path(path).exists())

        session = load_session(self.out)
        self.assertEqual(session["screens"], ["home.png", "profile.png"])
        # v1.0 schema normalizes legacy 'play' -> canonical store target 'play/phone'
        self.assertEqual(session["store"], "play/phone")
        self.assertEqual(session["version"], "1.0")
        self.assertIn("exportedAt", session)

    def test_write_session_strips_directory_prefixes(self):
        write_session(
            screens=["android/pixel9/home.png", r"ios\iphone\detail.png"],
            store="play/phone",
            output_dir=self.out,
        )
        session = load_session(self.out)
        self.assertEqual(session["screens"], ["home.png", "detail.png"])
        self.assertEqual(session["store"], "play/phone")

    def test_update_session_appends_unique_screens(self):
        write_session(screens=["a.png"], output_dir=self.out)
        update_session_with_capture("b.png", output_dir=self.out)
        update_session_with_capture("b.png", output_dir=self.out)
        session = load_session(self.out)
        self.assertEqual(session["screens"], ["a.png", "b.png"])

    def test_update_creates_session_when_missing(self):
        update_session_with_capture("first.png", output_dir=self.out)
        session = load_session(self.out)
        self.assertEqual(session["screens"], ["first.png"])

    def test_load_missing_session_returns_none(self):
        self.assertIsNone(load_session(self.out))

    def test_session_json_is_pretty_printed(self):
        write_session(screens=["a.png"], output_dir=self.out)
        raw = (self.out / "session.json").read_text()
        data = json.loads(raw)
        self.assertIn("\n", raw)


if __name__ == "__main__":
    unittest.main()
