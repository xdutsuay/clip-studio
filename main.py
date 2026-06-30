#!/usr/bin/env python
"""Clip Studio — lightweight trending-audio clips + carousel export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__VERSION__ = "4.0.0"


def _check_python() -> None:
    if sys.version_info < (3, 10):
        print("Clip Studio requires Python 3.10 or newer.")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clip-studio",
        description="Clip Studio — audio clips, carousels, LinkedIn war room",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__VERSION__}")

    sub = parser.add_subparsers(dest="command", required=True)

    clip = sub.add_parser("clip", help="Render a trending-audio short clip")
    clip.add_argument("--audio", type=Path, help="Path to MP3/WAV (or use assets/audio/)")
    clip.add_argument("--hook", type=str, help="On-screen hook text")
    clip.add_argument("--background-file", type=Path, help="Local MP4 instead of catalog download")
    clip.add_argument("--background", type=str, help="Key from utils/background_videos.json")
    clip.add_argument(
        "--theme",
        choices=("tech_insight", "job_approach"),
        default="tech_insight",
    )
    clip.add_argument("--topic", type=str, help="Auto-generate slides via LLM (needs Ollama)")
    clip.add_argument("--slides-file", type=Path, help="JSON file with slides array")
    clip.add_argument(
        "--manifest",
        type=Path,
        help="Use fields from an existing manifest (with --audio/--hook overrides)",
    )
    clip.add_argument(
        "--manifest-out",
        type=Path,
        default=Path("export/manifest.json"),
    )

    sub.add_parser("reddit", help="Legacy Reddit story video pipeline (heavy deps)")

    return parser


def run_clip(args: argparse.Namespace) -> int:
    from video_creation.audio_clip import make_clip

    audio = args.audio
    hook = args.hook
    slides = None

    if args.topic:
        import subprocess

        out = Path("export/slides.json")
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "scripts" / "generate_slides.py"),
            "--topic",
            args.topic,
            "--theme",
            args.theme,
            "--out",
            str(out),
        ]
        subprocess.run(cmd, check=True)
        data = json.loads(out.read_text(encoding="utf-8"))
        hook = hook or data.get("hook")
        slides = data.get("slides")

    if args.manifest and args.manifest.is_file():
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        audio = audio or Path(data["audio_path"])
        hook = hook or data["hook"]
        slides = data.get("slides")
        if not args.theme:
            args.theme = data.get("theme", "tech_insight")

    if args.slides_file and args.slides_file.is_file():
        slides = json.loads(args.slides_file.read_text(encoding="utf-8"))
        if isinstance(slides, dict):
            slides = slides.get("slides", [])

    if not audio or not hook:
        print("error: --audio and --hook are required (or provide --manifest)", file=sys.stderr)
        return 1

    make_clip(
        audio_path=audio,
        hook=hook,
        background=args.background,
        background_file=args.background_file,
        theme=args.theme,
        duration_cap=args.duration,
        slides=slides,
        manifest_out=args.manifest_out,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    _check_python()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "clip":
        return run_clip(args)

    if args.command == "reddit":
        from reddit_runner import run_cli

        run_cli()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
