"""GUI helpers for clip generation subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def list_audio_files() -> list[str]:
    audio_dir = ROOT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    exts = {".mp3", ".wav", ".m4a", ".aac"}
    return sorted(
        p.name
        for p in audio_dir.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )


def list_background_keys() -> list[str]:
    path = ROOT / "utils" / "background_videos.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("__comment", None)
    return sorted(data.keys())


def list_local_background_files() -> list[str]:
    video_dir = ROOT / "assets" / "backgrounds"
    if not video_dir.is_file() and not video_dir.is_dir():
        return []
    files: list[str] = []
    for p in video_dir.rglob("*.mp4"):
        if p.is_file():
            files.append(str(p.relative_to(ROOT)))
    return sorted(files)


def list_clips() -> list[dict]:
    clips_dir = ROOT / "results" / "clips"
    if not clips_dir.is_dir():
        return []
    clips = []
    for p in sorted(clips_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        clips.append(
            {
                "name": p.name,
                "path": str(p.relative_to(ROOT)),
                "mtime": int(p.stat().st_mtime),
            }
        )
    return clips


def run_clip_generation(
    *,
    audio: str,
    hook: str,
    background: str | None,
    background_file: str | None,
    theme: str,
    topic: str | None,
    duration: float | None,
) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "clip",
        "--audio",
        str(ROOT / "assets" / "audio" / audio) if not audio.startswith("/") else audio,
        "--hook",
        hook,
        "--theme",
        theme,
        "--manifest-out",
        str(ROOT / "export" / "manifest.json"),
    ]
    if background_file:
        cmd.extend(["--background-file", str(ROOT / background_file)])
    elif background:
        cmd.extend(["--background", background])
    if topic:
        cmd.extend(["--topic", topic])
    if duration:
        cmd.extend(["--duration", str(duration)])

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def run_carousel_push() -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "clip_to_carousel.py"),
        str(ROOT / "export" / "manifest.json"),
        "--push-lge",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output
