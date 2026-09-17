import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .capture import capture_screenshot, batch_capture
from .adb_usb import list_usb_devices
from .crawler import crawl_app
from .session import write_session
from .ai_config import resolve_ai_settings

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

ADB_INSTALL_GUIDE = """
Glint Bridge requires ADB (Android Debug Bridge).

Install it:
  Windows:  winget install Google.PlatformTools
  macOS:    brew install android-platform-tools
  Linux:    sudo apt install android-tools-adb

Or download directly: https://developer.android.com/tools/releases/platform-tools

After install, verify: adb version
"""


def check_adb() -> bool:
    if shutil.which("adb") is None:
        print(ADB_INSTALL_GUIDE)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(prog="glint-bridge")
    parser.add_argument(
        "mode",
        nargs="?",
        default="server",
        choices=["server", "capture", "batch", "devices", "crawl", "crawl-web", "check", "inspect", "extract-theme"],
    )
    parser.add_argument("--template", type=str, default=None, help="Template family id for inspect mode")
    parser.add_argument("--pack", type=str, default=None, help=".glint path for inspect mode")
    parser.add_argument("paths", nargs="*", help="PNG paths or folders for extract-theme")
    parser.add_argument("--count", type=int, default=5, help="Batch capture count")
    parser.add_argument("--package", type=str, default=None, help="App package for crawl mode")
    parser.add_argument("--url", type=str, default=None, help="Start URL for crawl-web")
    parser.add_argument("--max-screens", type=int, default=20, help="Max explore steps for crawl")
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Enable intelligent crawl (requires API key in env or --ai-key)",
    )
    parser.add_argument("--no-ai", action="store_true", help="Force heuristic crawl even if a key is set")
    parser.add_argument("--ai-key", type=str, default=None, help="API key (prefer GLINT_AI_API_KEY env)")
    parser.add_argument(
        "--ai-provider",
        type=str,
        default=None,
        choices=["openai", "anthropic", "compatible"],
        help="AI provider",
    )
    parser.add_argument("--ai-model", type=str, default=None, help="Model id")

    args = parser.parse_args()

    if args.mode == "check":
        if check_adb():
            print("ADB found:", end=" ")
            import subprocess

            result = subprocess.run(["adb", "version"], capture_output=True, text=True)
            print(result.stdout.strip().splitlines()[0] if result.stdout else "unknown version")
            devices = list_usb_devices()
            print(f"Connected devices: {len(devices)}")
            for d in devices:
                print(f"  {d['serial']}  {d['model']}")
        ai_key = (
            args.ai_key
            or os.getenv("GLINT_AI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        if ai_key:
            try:
                ai = resolve_ai_settings(use_ai=True, api_key=ai_key, provider=args.ai_provider, model=args.ai_model)
                print(f"AI: ready - {ai.provider} / {ai.model}")
            except RuntimeError as e:
                print(f"AI: not ready ({e})")
        else:
            print("AI: off - fine for agentic IDE (you plan). Optional --ai crawl needs GLINT_AI_API_KEY.")
        sys.exit(0 if shutil.which("adb") else 1)

    if args.mode != "crawl-web" and not check_adb():
        sys.exit(1)

    use_ai = False if args.no_ai else (True if args.ai else None)

    if args.mode == "devices":
        devices = list_usb_devices()
        if not devices:
            print("No Android devices connected.")
            print("Connect a device via USB and enable USB debugging.")
            sys.exit(1)
        print(f"Found {len(devices)} device(s):")
        for d in devices:
            print(f"  {d['serial']}  {d['model']}")

    elif args.mode == "capture":
        path = capture_screenshot()
        if path:
            write_session(
                screens=[Path(path).name],
                output_dir=OUTPUT_DIR,
            )
            print(f"Saved: {path}")
            print(f"Session: {OUTPUT_DIR / 'session.json'}")
        else:
            print("Capture failed. Check that your device is connected and USB debugging is enabled.")
            sys.exit(1)

    elif args.mode == "batch":
        paths = batch_capture(count=args.count)
        if paths:
            write_session(
                screens=[Path(p).name for p in paths],
                output_dir=OUTPUT_DIR,
            )
        print(f"Captured {len(paths)} screenshot(s):")
        for p in paths:
            print(f"  {p}")
        print(f"Session: {OUTPUT_DIR / 'session.json'}")

    elif args.mode == "crawl":
        if not args.package:
            print("Error: --package is required for crawl mode")
            sys.exit(1)
        try:
            paths = crawl_app(
                args.package,
                max_screens=args.max_screens,
                use_ai=use_ai,
                ai_api_key=args.ai_key or os.getenv("GLINT_AI_API_KEY"),
                ai_provider=args.ai_provider,
                ai_model=args.ai_model,
            )
            write_session(
                screens=[Path(p).name for p in paths],
                output_dir=OUTPUT_DIR,
            )
            print(f"Crawled {len(paths)} kept screenshot(s):")
            for p in paths:
                print(f"  {p}")
            print(f"Session: {OUTPUT_DIR / 'session.json'}")
            print("Next: import output/ into Glint Web")
        except RuntimeError as e:
            print(f"Crawl failed: {e}")
            sys.exit(1)

    elif args.mode == "crawl-web":
        if not args.url:
            print("Error: --url is required for crawl-web")
            sys.exit(1)
        try:
            from .web_crawler import crawl_web

            paths = crawl_web(
                args.url,
                max_screens=args.max_screens,
                use_ai=use_ai,
                ai_api_key=args.ai_key or os.getenv("GLINT_AI_API_KEY"),
                ai_provider=args.ai_provider,
                ai_model=args.ai_model,
            )
            write_session(
                screens=[Path(p).name for p in paths],
                output_dir=OUTPUT_DIR,
            )
            print(f"Web crawl kept {len(paths)} screenshot(s):")
            for p in paths:
                print(f"  {p}")
            print(f"Session: {OUTPUT_DIR / 'session.json'}")
        except RuntimeError as e:
            print(f"Web crawl failed: {e}")
            sys.exit(1)

    elif args.mode == "inspect":
        from .pack_inspect import load_template_family, pack_summary, read_glint, template_summary

        if args.template:
            try:
                data = template_summary(load_template_family(args.template))
            except FileNotFoundError as e:
                print(f"Error: {e}")
                sys.exit(1)
            print(json.dumps(data, indent=2))
        elif args.pack:
            pack_path = Path(args.pack)
            if not pack_path.is_file():
                print(f"Error: pack not found: {pack_path}")
                sys.exit(1)
            print(json.dumps(pack_summary(read_glint(pack_path)), indent=2))
        else:
            print("Error: use --template FAMILY or --pack PATH.glint")
            sys.exit(1)

    elif args.mode == "extract-theme":
        from .pack_inspect import extract_theme_from_paths, map_colors_to_palette, resolve_image_paths

        paths = resolve_image_paths(args.paths)
        if not paths:
            print("Error: pass PNG paths or a folder (e.g. output/)")
            sys.exit(1)
        try:
            slot_ids = None
            if args.template:
                from .pack_inspect import load_template_family

                tpl = load_template_family(args.template)
                slot_ids = [s.get("id") or f"c{i}" for i, s in enumerate(tpl.get("palette") or [])]
            theme = extract_theme_from_paths(paths, slot_ids=slot_ids)
        except RuntimeError as e:
            print(f"Error: {e}")
            sys.exit(1)
        out = {"theme": theme, "sources": [str(p) for p in paths]}
        if args.template:
            try:
                from .pack_inspect import load_template_family

                template = load_template_family(args.template)
                out["mapped"] = map_colors_to_palette(template.get("palette") or [], theme)
            except FileNotFoundError as e:
                print(f"Warning: {e}", file=sys.stderr)
        print(json.dumps(out, indent=2))

    else:
        from .websocket_server import run as run_ws

        run_ws()


if __name__ == "__main__":
    main()
