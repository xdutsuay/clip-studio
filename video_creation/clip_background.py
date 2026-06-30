"""Lean background download and chop for clip mode (ffmpeg only, no MoviePy)."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path
from typing import Any

import yt_dlp

from utils.clip_paths import ASSETS_BACKGROUNDS_VIDEO, BACKGROUND_VIDEOS_JSON
from utils.console import print_substep


def load_video_backgrounds() -> dict[str, list[Any]]:
    with open(BACKGROUND_VIDEOS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("__comment", None)
    return data


def resolve_background_key(name: str | None) -> str:
    options = load_video_backgrounds()
    if name and name in options:
        return name
    if name:
        raise ValueError(
            f"Unknown background {name!r}. Options: {', '.join(sorted(options))}"
        )
    return random.choice(list(options.keys()))


def background_file_path(key: str, local_file: Path | None = None) -> Path:
    if local_file is not None:
        path = local_file.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Background file not found: {path}")
        return path
    uri, filename, credit, _ = load_video_backgrounds()[key]
    path = ASSETS_BACKGROUNDS_VIDEO / f"{credit}-{filename}"
    if not path.is_file():
        download_background_video(uri, credit, filename)
    if not path.is_file():
        raise FileNotFoundError(f"Background video not found after download: {path}")
    return path


def download_background_video(uri: str, credit: str, filename: str) -> None:
    ASSETS_BACKGROUNDS_VIDEO.mkdir(parents=True, exist_ok=True)
    dest = ASSETS_BACKGROUNDS_VIDEO / f"{credit}-{filename}"
    if dest.is_file():
        return
    print_substep(f"Downloading background {filename} (≤720p, one-time)…")
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]/best[height<=720]",
        "outtmpl": str(dest),
        "retries": 5,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([uri])
    print_substep("Background downloaded.", style="bold green")


def probe_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def chop_background_ffmpeg(source: Path, duration: float, dest: Path) -> None:
    """Extract a subclip of `duration` seconds from a longer background video."""
    total = probe_duration_seconds(source)
    if total <= duration + 1:
        start = 0.0
    else:
        # Skip first 3 minutes of typical gameplay intros when possible.
        min_start = min(180.0, max(0.0, total - duration - 1))
        max_start = max(min_start, total - duration - 1)
        start = random.uniform(min_start, max_start)

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(duration),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(dest),
        ],
        check=True,
    )
