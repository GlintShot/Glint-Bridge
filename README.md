# Glint Bridge

ADB screenshot capture for **Android**, optional **web** crawl, and intelligent filtering with **your** API key. Part of [Glint](https://github.com/GlintShot).

> For Flutter store sizes without a device, use [Glint-Capture](../Glint-Capture).

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

## Commands

```bash
python glint.py check      # ADB + AI status
python glint.py devices    # list USB / Wi‑Fi
python glint.py capture    # one PNG → output/
python glint.py batch 5    # five PNGs + session.json
python glint.py start      # WebSocket for Glint Web
```

### Inspect templates & theme

Read Glint-Web template JSON or exported `.glint` packs; sample dominant colors from PNG screenshots (`pip install Pillow` for extract):

```bash
python glint.py inspect --template blink
python glint.py inspect --pack my-project.glint
python glint.py extract-theme output/
python glint.py theme output/ --template blink   # map colors to template slots
```

### Crawl (Android)

Needs Appium. Uncomment `Appium-Python-Client` in `requirements.txt`, start Appium on `:4723`, then:

```bash
# Heuristic (scroll / tap) - no AI
python glint.py crawl com.example.app

# Intelligent - your key; AI navigates + keeps store-worthy real screens only
export GLINT_AI_API_KEY=sk-...          # or OPENAI_API_KEY / ANTHROPIC_API_KEY
python glint.py crawl com.example.app --ai
```

### Crawl (web)

```bash
pip install playwright && playwright install chromium
python glint.py crawl-web https://example.com --ai
```

### AI settings (local-first)

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

CLI: `--ai` / `--no-ai` / `--ai-key` / `--ai-provider` / `--ai-model`

**Policy:** AI chooses where to go and which frames to keep. Screenshots are always **real** pixels (App Store 2.3.10). No fabricated UI.

Then import `output/` (PNGs + `session.json`) into **Glint Web**.

## Security (WebSocket)

- Binds to **`127.0.0.1:7700` only** (loopback)
- Prints a **pairing token** on start; Glint Web must pair before capture
- Capture responses include **`data_url`** (base64 PNG) so the browser can display shots
- Crawl `use_ai` may be requested by the client; **API keys are read only from Bridge env**

Never bind `0.0.0.0` in production use.

## Glint Web

1. `python glint.py start` - copy the token
2. In Web editor, paste token if prompted → Pair
3. **Capture from Device** in Assets  
   Or: crawl → drag `output/` into Web

## License

MIT

---

<div align="center">

<a href="https://github.com/darkmintis">
  <img src="https://img.shields.io/badge/follow-%40Darkmintis-1DA1F2?style=social&logo=github" alt="Follow @Darkmintis"/>
</a>

</div>
