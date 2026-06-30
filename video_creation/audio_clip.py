"""Trending-audio clip renderer — ffmpeg + PIL, no Reddit/Playwright/TTS stack."""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils.clip_paths import EXPORT_DIR, RESULTS_CLIPS, ROOT, TEMP_DIR
from utils.console import print_step, print_substep
from utils.ffmpeg_codec import video_encode_args
from video_creation.clip_background import (
    background_file_path,
    chop_background_ffmpeg,
    probe_duration_seconds,
    resolve_background_key,
)

W, H = 1080, 1920


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return (slug or "clip")[:max_len]


def render_hook_overlay(hook: str, path: Path) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 72)
    except OSError:
        font = ImageFont.load_default()

    margin = 80
    max_width = W - 2 * margin
    lines = _wrap_text(draw, hook, font, max_width)
    line_height = 86
    block_height = line_height * len(lines)
    y = (H - block_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines[:4]


def write_shortform_exports(export_dir: Path, hook: str, hashtags: list[str]) -> None:
    shortform = export_dir / "shortform"
    shortform.mkdir(parents=True, exist_ok=True)
    tags = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
    (shortform / "yt_title.txt").write_text(hook[:95], encoding="utf-8")
    (shortform / "yt_description.txt").write_text(
        f"{hook}\n\n{tags}\n\nhttps://kaustubhtripathi.com",
        encoding="utf-8",
    )
    (shortform / "ig_caption.txt").write_text(
        f"{hook}\n\n{tags}",
        encoding="utf-8",
    )


def make_clip(
    *,
    audio_path: Path,
    hook: str,
    background: str | None = None,
    background_file: Path | None = None,
    theme: str = "tech_insight",
    duration_cap: float | None = None,
    slides: list[str] | None = None,
    manifest_out: Path | None = None,
) -> Path:
    if not shutil_which("ffmpeg"):
        raise RuntimeError("ffmpeg not found. Install with: brew install ffmpeg")

    audio_path = audio_path.resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    started = time.perf_counter()
    audio_duration = probe_duration_seconds(audio_path)
    duration = min(audio_duration, duration_cap or 60.0)

    bg_key = "local" if background_file is not None else resolve_background_key(background)
    bg_source = background_file_path(bg_key, local_file=background_file)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    temp = TEMP_DIR / run_id
    temp.mkdir(parents=True, exist_ok=True)

    chopped_bg = temp / "background.mp4"
    overlay_png = temp / "hook.png"
    scaled_bg = temp / "background_9x16.mp4"
    output = RESULTS_CLIPS / f"{run_id}_{slugify(hook)}.mp4"
    RESULTS_CLIPS.mkdir(parents=True, exist_ok=True)

    print_step(f"Clip: {duration:.1f}s · background={bg_key}")
    chop_background_ffmpeg(bg_source, duration, chopped_bg)
    render_hook_overlay(hook, overlay_png)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(chopped_bg),
            "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(scaled_bg),
        ],
        check=True,
    )

    encode = video_encode_args()
    vcodec = encode.pop("c:v")
    preset = encode.pop("preset", None)
    crf = encode.pop("crf", None)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(scaled_bg),
        "-i",
        str(overlay_png),
        "-i",
        str(audio_path),
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map",
        "[v]",
        "-map",
        "2:a",
        "-t",
        str(duration),
        "-c:v",
        vcodec,
    ]
    if preset:
        cmd.extend(["-preset", str(preset)])
    if crf:
        cmd.extend(["-crf", str(crf)])
    if encode.get("b:v"):
        cmd.extend(["-b:v", str(encode["b:v"])])
    cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest", str(output)])
    subprocess.run(cmd, check=True)

    render_ms = int((time.perf_counter() - started) * 1000)
    slide_list = slides or [hook]
    hashtags = _default_hashtags(theme)

    manifest = {
        "hook": hook,
        "slides": slide_list,
        "theme": theme,
        "hashtags": hashtags,
        "background": bg_key,
        "video_path": str(output.relative_to(ROOT)),
        "audio_path": str(audio_path),
        "duration_sec": duration,
        "render_ms": render_ms,
        "platforms": {"linkedin": "carousel", "youtube": "shorts", "instagram": "video"},
    }

    export_dir = EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    out_manifest = manifest_out or (export_dir / "manifest.json")
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_shortform_exports(export_dir, hook, hashtags)

    print_substep(f"Rendered in {render_ms}ms → {output}", style="bold green")
    print_substep(f"Manifest → {out_manifest}")
    return output


def _default_hashtags(theme: str) -> list[str]:
    base = ["dataengineering", "platformengineering", "softwareengineering"]
    if theme == "job_approach":
        return base + ["career", "jobsearch", "techjobs"]
    return base + ["buildinpublic", "data"]


def shutil_which(cmd: str) -> str | None:
    import shutil

    return shutil.which(cmd)
