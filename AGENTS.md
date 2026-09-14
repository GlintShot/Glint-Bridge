# Glint-Bridge - Agent Instructions

ADB screenshot capture for Android apps. Real device, real pixels, no cropping.

**You (the agent) are the intelligence.** Developers should not configure API keys for Capture.

**Full workflow:** See `skills/glint/SKILL.md` in the GlintShot org for the complete multi-repo pipeline.

## Primary commands

- `python glint.py check` - verify ADB + AI status
- `python glint.py devices` - list connected USB/WiFi ADB targets
- `python glint.py capture` - single screenshot → output/
- `python glint.py batch N` - N screenshots + session.json
- `python glint.py crawl com.app.package [--ai]` - auto-navigate + capture
- `python glint.py start` - WebSocket for Glint Web live pairing

## Outputs

- Raw PNG screenshots at device native resolution (no crop, no resize)
- `session.json` at output root (used by Glint-Web import)

## Rules

1. **Real device pixels only** - no cropping, no resizing, no fabrication
2. Raw screenshots are NOT store-ready - they get polished in Glint-Web with templates/frames
3. Capture at device native resolution (whatever the phone gives via `adb exec-out screencap -p`)
4. Glint-Web handles: device frames, backgrounds, headlines, export at store sizes
5. Never ask user for API keys - read from env only (GLINT_AI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)
6. Bind WebSocket to localhost only (127.0.0.1:7700), never 0.0.0.0

## Decision Flow

### Developer says: "capture screenshots from my Android app"

Do NOT ask which screens. Auto-crawl:

1. `python glint.py check` - verify ADB installed
2. `python glint.py devices` - confirm device connected
3. If no device → tell developer: "Connect Android device via USB, enable USB debugging"
4. If AI key available (GLINT_AI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY):
   `python glint.py crawl com.app.package --ai`
5. If no AI key:
   `python glint.py crawl com.app.package` (heuristic scroll/tap)
6. Tell developer: output is in `output/`, import into Glint Web for templates

### Developer says: "capture 5 screenshots"

1. `python glint.py devices` - confirm device
2. `python glint.py batch --count 5`
3. Tell developer: output is in `output/`

### Developer says: "capture single screenshot"

1. `python glint.py devices` - confirm device
2. `python glint.py capture`
3. Single PNG in `output/`

### Developer says: "navigate to settings and capture"

1. Use `python glint.py start` (WebSocket for live control)
2. Or: developer navigates manually, then `python glint.py capture` at each screen

### Developer says: "capture for Play Store"

1. Bridge captures raw at device resolution
2. Import into Glint Web → pick Play Store template (1080×1920)
3. Web crops/frames to Play Store size

### Developer says: "capture for App Store"

1. Bridge captures raw at device resolution
2. Import into Glint Web → pick App Store template (1290×2796 for iPhone, 2048×2732 for iPad)
3. Web frames to App Store size

## Crawl Modes

### Heuristic (no AI key)
- Scrolls and taps through the app
- Keeps every 3rd unique screen
- Basic dedup by file size fingerprint
- Good enough for simple apps

### AI (with API key)
- Vision model scores each screen for store marketing value
- Smart navigation: taps feature-rich areas, scrolls to content
- Rejects: login, loading, error, permission dialogs, keyboards
- Keeps 5-8 best unique screens (matches Glint Web template slots)
- Requires: GLINT_AI_API_KEY or OPENAI_API_KEY or ANTHROPIC_API_KEY

## After Capture

1. Raw PNGs + session.json are in `output/`
2. Open Glint Web → drag-drop the output/ folder
3. Pick a template → batch apply → export ZIP
4. ZIP contains store-ready PNGs at exact store dimensions

## Security

- WebSocket binds to localhost only (127.0.0.1:7700)
- Pairing token required before Web can pull captures
- API keys read from env only, never sent to Glint servers
- Never bind 0.0.0.0 in production
