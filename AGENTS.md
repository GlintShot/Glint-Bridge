# Glint-Bridge - Agent Instructions

ADB screenshot capture for Android. Real device pixels. System chrome can be cropped for store focus.

**You (the IDE agent) are the intelligence.** Do **not** ask the developer for OpenAI/Anthropic keys. Drive the device with sense/act steps.

**Full workflow:** See `skills/glint/SKILL.md` in the GlintShot org.

## Preferred path - agentic crawl (no API key)

```text
devices → pass(package, count=5) → theme.json + shots → polish-session → ZIP
# or step-by-step:
devices → launch → loop{ screenshot, hierarchy, tap|scroll|back } → polish
```

| Command | Purpose |
|---------|---------|
| `python glint.py check` | ADB present? |
| `python glint.py devices` | USB / Wi‑Fi targets |
| `python glint.py agent pass com.app --count 5` | Launch + N shots + theme (preferred) |
| `python glint.py agent launch com.app` | Open app |
| `python glint.py agent screenshot` | PNG → `output/` (crops status/nav by default) |
| `python glint.py agent hierarchy [--package com.app]` | Clickable targets + text |
| `python glint.py agent tap X Y` | Tap pixel (use hierarchy bounds center) |
| `python glint.py agent scroll [forward\|backward]` | Swipe |
| `python glint.py agent back` | System back |
| `python glint.py extract-theme output/` | Sample brand colors → theme.json |

Chrome flags: `--keep-status` / `--keep-nav` / `--no-immersive` on `pass` / `screenshot`.

MCP: `glint_bridge_pass` or step tools `glint_bridge_*`.

## Rules

1. **Real device UI only** - no fabricated screens; chrome crop for store focus is OK
2. Prefer `pass` (fewer tokens) then headless polish
3. Never ask the user for API keys for agentic crawl
4. Skip login, loading, errors, permission dialogs, keyboards when choosing keepers
5. Keep about **5-8** unique marketing screens
6. WebSocket binds to `127.0.0.1:7700` only - never `0.0.0.0`

## Decision flow

### "Capture screenshots from my Android app"

1. `python glint.py check` / `devices`
2. `python glint.py agent pass com.app --count 5`
3. Polish (below) or import `output/` into Studio

### Headless CI only (no IDE agent)

- `python glint.py crawl com.app` (Appium heuristic)
- `python glint.py crawl com.app --ai` only if a key is **already** in env - never solicit one

## After capture

1. `output/` has PNGs + `session.json` (+ `theme.json` from `pass`)
2. Headless polish (same path every agent should use):

```bash
cd ../Glint-Web
node scripts/polish-session.mjs \
  --session ../Glint-Bridge/output \
  --out app-play.zip \
  --template mint-tags-play \
  --headlines "Caption one,Caption two,Caption three,Caption four,Caption five"
```

3. Or Glint Studio → import folder → template → export ZIP

## Security

- Localhost WebSocket + pairing token
- Optional `--ai` keys stay on the machine; never sent to Glint servers
