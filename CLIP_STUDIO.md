# Clip Studio — war room

## Weekly ritual (5–7 hrs)

| Block | Time | Action |
|-------|------|--------|
| career-ops scan | 30m | `/career-ops scan` → pick 1 JD from `data/pipeline.md` |
| Produce | 2h | 1 job clip + 1 tech clip |
| Repurpose | 1h | carousel PDF → linkedin-growth-engine |
| Publish | 1h | 2 carousels + 1 text on LinkedIn |
| Short-form | 45m | YT Shorts + new IG channel |
| Distribute | 45m | 10 comments, 2 DMs |
| Engage | 30m | Reply to comments < 24h |

## Themes

**A — Job approach:** `job_to_clip.py` (Phase 2c) from career-ops pipeline → `--anon` or `--name-company`

**B — Tech insight:** `generate_slides.py` (Phase 2b) → `--theme tech_insight`

## Full war room flow

```bash
# 1) Job theme (career-ops pipeline)
python scripts/job_to_clip.py --from-pipeline --pick 1 --anon

# 2) Render clip (add your audio)
python main.py clip --manifest export/manifest.json --audio assets/audio/track.mp3

# 3) Carousel PDF → LinkedIn engine
python scripts/clip_to_carousel.py export/manifest.json --push-lge

# Tech theme shortcut
python main.py clip --topic "Why Glue beats EMR for small teams" \
  --audio assets/audio/track.mp3 --background-file assets/backgrounds/test-bg.mp4
python scripts/clip_to_carousel.py export/manifest.json
```


Optional audio fetch:

```bash
python scripts/fetch_audio.py --url 'https://youtube.com/...' --out assets/audio/trend.mp3
```

## Environment

```bash
# .env (not committed)
OLLAMA_BASE_URL=http://127.0.0.1:11434
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
LGE_BASE_URL=http://127.0.0.1:8787
CAREER_OPS_PATH=/Users/nehatiwari/localcode/career-ops
```

## Platforms

| Platform | Content |
|----------|---------|
| LinkedIn | PDF carousels via linkedin-growth-engine |
| YouTube | Shorts + `export/shortform/yt_*.txt` |
| Instagram | New personal channel, no face, B-roll + text |
| TikTok | Not used |

## Engineering cap

After Phase 3 ships: **max 2 hrs/week** on clip-studio code. Remaining time = produce + distribute.
