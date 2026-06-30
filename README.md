# Clip Studio

Lightweight CLI war room for trending-audio shorts, LinkedIn carousels, and short-form export.

## Install (clip path only — no Docker, no torch)

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-clip.txt
```

Legacy Reddit story mode (optional, heavy):

```bash
pip install -r requirements-legacy-reddit.txt
python -m playwright install chromium
```

Optional GUI (Phase 4):

```bash
pip install -r requirements-gui.txt
python GUI.py
# → http://localhost:4000/clip
```

## Quick start

```bash
# Drop an MP3 in assets/audio/
python main.py clip --audio assets/audio/your-track.mp3 \
  --hook "Glue vs EMR: what I'd pick in 2026" \
  --background minecraft
```

Outputs:

- `results/clips/*.mp4` — vertical short
- `export/manifest.json` — carousel + LGE bridge
- `export/shortform/` — YT / IG caption files

## Commands

| Command | Purpose |
|---------|---------|
| `python main.py clip` | Render audio + B-roll + hook clip |
| `python main.py reddit` | Legacy Reddit story pipeline |

See [CLIP_STUDIO.md](CLIP_STUDIO.md) for weekly workflow, career-ops job theme, and LinkedIn bridge.

## Principles

- **Lightweight** — default deps fit in `requirements-clip.txt`
- **Fast** — ffmpeg `veryfast`, cached backgrounds
- **No Docker** — docker files live in `legacy/docker/` only

## LinkedIn publish

Use [linkedin-growth-engine](../linkedin-growth-engine) to review and post carousels exported from Clip Studio (Phase 3 script).
