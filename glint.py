"""
Glint - simple CLI for screenshot capture.

Usage:
    python glint.py check          Verify ADB is installed
    python glint.py devices        List connected Android devices
    python glint.py capture        Capture one screenshot
    python glint.py batch 5        Capture 5 screenshots
    python glint.py start          Start server (connect to Glint-Web)
    python glint.py agent …        Agentic sense/act steps (no API key)
    python glint.py crawl com.app  Headless Appium crawl (CI)
    python glint.py crawl com.app --ai   Optional server-side AI (needs your key)
    python glint.py crawl-web https://example.com --ai
    python glint.py inspect --template blink
    python glint.py inspect --pack project.glint
    python glint.py extract-theme output/
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from bridge.main import main

# Sense/act steps for agentic IDEs (Cursor / Claude). No LLM / API key inside Bridge.
AGENT_STEPS = frozenset({"launch", "hierarchy", "tap", "scroll", "back"})

ALIASES = {
    "check": "check",
    "devices": "devices",
    "ls": "devices",
    "capture": "capture",
    "screenshot": "capture",
    "snap": "capture",
    "batch": "batch",
    "multi": "batch",
    "start": "server",
    "server": "server",
    "serve": "server",
    "ws": "server",
    "crawl": "crawl",
    "auto": "crawl",
    "crawl-web": "crawl-web",
    "web": "crawl-web",
    "inspect": "inspect",
    "extract-theme": "extract-theme",
    "theme": "extract-theme",
    "agent": "agent",
    "help": None,
}

USAGE = """
Glint Bridge - Android / web screenshot capture

Agentic IDE (preferred - YOU plan, no API key):
  python glint.py devices
  python glint.py agent pass com.example.app --count 5
  python glint.py agent launch com.example.app
  python glint.py agent screenshot
  python glint.py agent hierarchy [--package com.example.app]
  python glint.py agent tap X Y
  python glint.py agent scroll [forward|backward]
  python glint.py agent back
  # pass = one JSON: launch + N true-color shots (saves agent tokens)

Manual / quick:
  python glint.py check                 Check ADB
  python glint.py capture               One screenshot
  python glint.py batch 5               Five screenshots + session.json
  python glint.py start                 WebSocket for Glint Studio

Headless CI (no IDE agent in the loop):
  python glint.py crawl com.app         Heuristic Appium crawl
  python glint.py crawl com.app --ai    Optional: your vision API key navigates
  python glint.py crawl-web URL [--ai]  Playwright web crawl

Also:
  python glint.py inspect --template blink
  python glint.py extract-theme output/

Shortcuts: snap=capture  ls=devices  multi 5=batch 5
  python glint.py launch com.app        = agent launch
  python glint.py hierarchy             = agent hierarchy

First time? Run: python glint.py check
"""


def resolve_command(args: list[str]) -> list[str] | None:
    """Return argv for bridge.main, or None if handled (agent steps)."""
    if not args:
        print(USAGE)
        sys.exit(0)

    cmd = args[0].lower()

    if cmd in ("help", "--help", "-h"):
        print(USAGE)
        sys.exit(0)

    # Direct step aliases: python glint.py launch com.app
    if cmd in AGENT_STEPS:
        from bridge.agent import main as agent_main

        agent_main(args)
        return None

    if cmd == "agent":
        from bridge.agent import main as agent_main

        if len(args) < 2:
            print(USAGE)
            sys.exit(1)
        agent_main(args[1:])
        return None

    if cmd not in ALIASES:
        # Might be a package name for crawl mode
        if "." in cmd and not cmd.startswith("http"):
            return ["crawl", "--package", cmd] + args[1:]
        if cmd.startswith("http://") or cmd.startswith("https://"):
            return ["crawl-web", "--url", cmd] + args[1:]
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)

    mode = ALIASES[cmd]
    if mode is None:
        print(USAGE)
        sys.exit(0)

    remaining = args[1:]

    if mode == "batch" and remaining and not remaining[0].startswith("-"):
        return ["batch", "--count", remaining[0]] + remaining[1:]

    if mode == "crawl" and remaining and not remaining[0].startswith("-"):
        return ["crawl", "--package", remaining[0]] + remaining[1:]

    if mode == "crawl-web" and remaining and not remaining[0].startswith("-"):
        return ["crawl-web", "--url", remaining[0]] + remaining[1:]

    return [mode] + remaining


if __name__ == "__main__":
    resolved = resolve_command(sys.argv[1:])
    if resolved is None:
        sys.exit(0)
    sys.argv = ["glint-bridge"] + resolved
    main()
