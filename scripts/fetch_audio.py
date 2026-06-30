#!/usr/bin/env python3
"""Download audio from a YouTube URL into assets/audio/ (optional helper)."""

from __future__ import annotations

import argparse
from pathlib import Path

import yt_dlp


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch audio via yt-dlp")
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_template = str(args.out.with_suffix("")) + ".%(ext)s"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([args.url])

    print(f"Saved audio under {args.out.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
