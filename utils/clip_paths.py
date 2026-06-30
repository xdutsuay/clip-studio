"""Shared paths for clip-studio."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_AUDIO = ROOT / "assets" / "audio"
ASSETS_BACKGROUNDS_VIDEO = ROOT / "assets" / "backgrounds" / "video"
BACKGROUND_VIDEOS_JSON = ROOT / "utils" / "background_videos.json"
EXPORT_DIR = ROOT / "export"
RESULTS_CLIPS = ROOT / "results" / "clips"
TEMP_DIR = ROOT / "assets" / "temp"
