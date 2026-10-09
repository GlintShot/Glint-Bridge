import json
import sys
from pathlib import Path

import pytest

from bridge.pack_inspect import (
    build_theme_from_counts,
    is_neutral_rgb,
    load_template_family,
    map_colors_to_palette,
    read_glint,
    template_summary,
)


def test_is_neutral_rgb():
    assert is_neutral_rgb(255, 255, 255)
    assert is_neutral_rgb(10, 10, 10)
    assert not is_neutral_rgb(200, 50, 50)


def test_pick_theme_colors():
    counts = {
        "96,32,160": 40,
        "128,48,208": 25,
        "248,248,248": 200,
    }
    theme = build_theme_from_counts(counts, counts, ["primary", "background"])
    # primary is brand-punched to match Glint-Web's buildHarmonyFromPrimary
    # (punchSaturation('#6020A0', 0.1)) -> #601DA3, not the raw extracted hex
    assert theme["primary"] == "#601DA3"
    assert theme["background"] == "#F8F8F8"


def test_build_theme_from_counts():
    accent = {"96,32,160": 80}
    neutral = {"248,248,248": 200, "96,32,160": 80}
    theme = build_theme_from_counts(accent, neutral, ["primary", "background"])
    assert "primary" in theme
    assert theme["background"] == "#F8F8F8"


def test_template_summary_blink():
    root = Path(__file__).resolve().parent.parent.parent / "Glint-Web" / "public" / "templates"
    if not root.is_dir():
        pytest.skip("Glint-Web templates not available")
    template = load_template_family("blink", root)
    summary = template_summary(template)
    assert summary["familyId"] == "blink"
    assert "primary" in summary["palette"]
    assert summary["headlines"]


def test_map_colors_to_palette():
    palette = [{"id": "primary", "color": "#611AB4"}, {"id": "secondary", "color": "#8030DD"}]
    mapped = map_colors_to_palette(palette, {"primary": "#FF0000", "secondary": "#00FF00"})
    assert mapped == {"primary": "#FF0000", "secondary": "#00FF00"}


def test_read_glint_roundtrip(tmp_path):
    # Minimal fake glint zip without magic header
    import io
    import zipfile

    project = {"format": "glint", "frames": []}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("project.json", json.dumps(project))
    path = tmp_path / "test.glint"
    path.write_bytes(buf.getvalue())
    assert read_glint(path)["format"] == "glint"
