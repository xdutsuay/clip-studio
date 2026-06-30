"""Video encoder selection — libx264 on Mac/CPU, optional NVENC when available."""

from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def nvenc_available() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return "h264_nvenc" in result.stdout


def video_encode_args(*, high_quality: bool = False) -> dict[str, Any]:
    """ffmpeg output kwargs for H.264 video."""
    threads = _cpu_count()
    if nvenc_available():
        return {
            "c:v": "h264_nvenc",
            "b:v": "20M",
            "b:a": "192k",
            "threads": threads,
        }
    preset = "medium" if high_quality else "veryfast"
    return {
        "c:v": "libx264",
        "preset": preset,
        "crf": "23",
        "b:a": "192k",
        "threads": threads,
    }


def _cpu_count() -> int:
    try:
        import multiprocessing

        return multiprocessing.cpu_count()
    except NotImplementedError:
        return 4
