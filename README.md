# Glint Bridge

ADB capture for **Android** apps - real device pixels for Play Store / App Store pipelines. Part of [GlintShot](https://github.com/GlintShot).

> Flutter without a device? Use [Glint-Capture](https://github.com/GlintShot/Glint-Capture).

## Two ways to crawl

| Mode | Who decides where to go? | API key? |
|------|--------------------------|----------|
| **Agentic IDE (preferred)** | Cursor / Claude / Copilot - they already have a model | **No** |
| **Headless crawl** | Bridge heuristic, or optional `--ai` with *your* key | Only if you use `--ai` |

In an agentic IDE, **you (the agent) are the planner**. Bridge only exposes sense/act primitives: launch, hierarchy, screenshot, tap, scroll, back. No `GLINT_AI_*` keys needed.

## Install

```bash
pip install -r requirements.txt
```

Requires [ADB](https://developer.android.com/tools/releases/platform-tools):

```bash
# Linux
sudo apt install android-tools-adb
# macOS
brew install android-platform-tools
# Windows
winget install Google.PlatformTools
```

## Agentic crawl (no API key)

**One-shot pack (preferred - fewer agent tokens):**

```bash
python glint.py agent pass com.example.app --count 5
# → output/shot_01.png … + session.json (true-color: eye comfort briefly off per shot)
```

**Step-by-step** when you need to decide taps yourself:

```bash
python glint.py check
python glint.py devices

python glint.py agent launch com.example.app
python glint.py agent screenshot          # true-color by default; --no-true-color to skip
python glint.py agent hierarchy --package com.example.app
python glint.py agent tap 540 1200
python glint.py agent scroll forward
python glint.py agent back
```

MCP: `glint_bridge_pass` or step tools `glint_bridge_*`.

Shortcuts: `python glint.py launch com.app` · `python glint.py hierarchy`

## Manual / quick capture

```bash
python glint.py capture    # one PNG → output/
python glint.py batch 5    # five PNGs + session.json
python glint.py start      # WebSocket for Glint Studio live pairing
```

## Headless crawl (CI / no IDE agent)

Needs Appium. Uncomment `Appium-Python-Client` in `requirements.txt`, start Appium on `:4723`:

```bash
# Heuristic scroll/tap - no key
python glint.py crawl com.example.app

# Optional: Bridge calls YOUR vision API to navigate + score (not Glint servers)
export GLINT_AI_API_KEY=sk-...   # or OPENAI_API_KEY / ANTHROPIC_API_KEY
python glint.py crawl com.example.app --ai
```

Web (Playwright):

```bash
pip install playwright && playwright install chromium
python glint.py crawl-web https://example.com          # heuristic
python glint.py crawl-web https://example.com --ai     # optional key
```

### Optional `--ai` settings (headless only)

Only when Bridge itself must plan without an IDE agent:

| Env | Purpose |
|-----|---------|
| `GLINT_AI_API_KEY` | Preferred key (never sent to Glint servers) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Also accepted |
| `GLINT_AI_ENABLED=1` | Same as always passing `--ai` |
| `GLINT_AI_PROVIDER` | `openai` \| `anthropic` \| `compatible` |
| `GLINT_AI_MODEL` | e.g. `gpt-4o-mini`, `claude-3-5-haiku-latest` |
| `GLINT_AI_BASE_URL` | OpenAI-compatible base (OpenRouter, Groq, local) |
| `GLINT_AI_KEEP_THRESHOLD` | Min score to keep (default `0.65`) |
| `GLINT_AI_MAX_KEEP` | Max kept frames (default `8`) |

**Policy:** Screenshots are always **real** pixels (App Store 2.3.10). No fabricated UI.

## Inspect templates & theme

```bash
python glint.py inspect --template blink
python glint.py inspect --pack my-project.glint
python glint.py extract-theme output/
python glint.py theme output/ --template blink
```

## Security (WebSocket)

- Binds to **`127.0.0.1:7700` only** (loopback)
- Prints a **pairing token** on start; Glint Studio must pair before capture
- Crawl `use_ai` may be requested by the client; **API keys are read only from Bridge env**

Never bind `0.0.0.0` in production use.

## Glint Studio

1. Agentic or crawl → `output/` (PNGs + `session.json` + `theme.json`)
2. Open Studio → import / drop `output/`
3. Or: `python glint.py start` → pair token → Capture from Device
4. **Headless polish** (agents): from Glint-Web run `node scripts/polish-session.mjs --session ../Glint-Bridge/output --out pack.zip --headlines "…"`

Chrome: `pass` / `screenshot` crop status + nav by default; `--keep-status` / `--keep-nav` to disable. Immersive mode is on for `pass` unless `--no-immersive`.

## License

MIT

---

<div align="center">

<a href="https://github.com/darkmintis">
  <img src="https://img.shields.io/badge/follow-%40Darkmintis-1DA1F2?style=social&logo=github" alt="Follow @Darkmintis"/>
</a>

</div>
