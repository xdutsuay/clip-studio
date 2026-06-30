#!/usr/bin/env python3
"""Render manifest slides to PDF; optionally push to linkedin-growth-engine."""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

import httpx
import img2pdf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.llm_hybrid import load_env_file

SLIDE_SIZE = 1080
BG = (26, 26, 46)
FG = (255, 255, 255)
ACCENT = (100, 180, 255)


def render_slide(text: str, index: int, total: int) -> Image.Image:
    img = Image.new("RGB", (SLIDE_SIZE, SLIDE_SIZE), BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 52)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
        small = font

    draw.text((60, 60), f"{index}/{total}", font=small, fill=ACCENT)
    y = 200
    for line in textwrap.wrap(text, width=28):
        draw.text((60, y), line, font=font, fill=FG)
        y += 64
        if y > SLIDE_SIZE - 120:
            break

    draw.text((60, SLIDE_SIZE - 80), "Kaustubh Tripathi · Data & Platform", font=small, fill=ACCENT)
    return img


def manifest_to_pdf(manifest: dict, pdf_path: Path) -> Path:
    slides = manifest.get("slides") or [manifest.get("hook", "")]
    images: list[Image.Image] = []
    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        images.append(render_slide(str(slide), i, total))

    tmp_dir = pdf_path.parent / "_carousel_pages"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    page_paths: list[Path] = []
    for i, im in enumerate(images):
        p = tmp_dir / f"slide_{i:02d}.png"
        im.save(p, "PNG")
        page_paths.append(p)

    pdf_bytes = img2pdf.convert([str(p) for p in page_paths])
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path


def push_lge(manifest: dict, pdf_path: Path) -> dict:
    load_env_file()
    base = os.getenv("LGE_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
    hook = manifest.get("hook", "")
    slides = manifest.get("slides", [])
    body_text = hook + "\n\n" + "\n".join(f"• {s}" for s in slides)

    with httpx.Client(timeout=60.0) as client:
        text_id = client.post(
            f"{base}/api/ingest",
            json={
                "type": "manual",
                "text": body_text,
                "metadata": {"source": "clip-studio", "theme": manifest.get("theme")},
            },
        )
        text_id.raise_for_status()
        source_text = text_id.json()

        with pdf_path.open("rb") as f:
            upload = client.post(
                f"{base}/api/upload",
                files={"file": (pdf_path.name, f, "application/pdf")},
            )
        upload.raise_for_status()
        source_pdf = upload.json()["source_id"]

        gen = client.post(
            f"{base}/api/generate",
            json={"source_ids": [source_text, source_pdf]},
        )
        gen.raise_for_status()
        draft_id = gen.json()

    return {"draft_id": draft_id, "source_ids": [source_text, source_pdf]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Manifest → carousel PDF")
    parser.add_argument("manifest", type=Path, nargs="?", default=Path("export/manifest.json"))
    parser.add_argument("--pdf-out", type=Path, default=Path("export/carousel.pdf"))
    parser.add_argument("--push-lge", action="store_true")
    args = parser.parse_args()

    if not args.manifest.is_file():
        print(f"Missing manifest: {args.manifest}", file=sys.stderr)
        return 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pdf_path = (ROOT / args.pdf_out).resolve()
    manifest_to_pdf(manifest, pdf_path)
    print(f"Wrote {pdf_path}")

    manifest["carousel_pdf"] = str(pdf_path.relative_to(ROOT))
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.push_lge:
        try:
            result = push_lge(manifest, pdf_path)
            print(f"Pushed to linkedin-growth-engine → draft_id={result['draft_id']}")
            print("Open LGE Kanban to review, approve, and post.")
        except httpx.HTTPError as e:
            print(f"LGE push failed (is npm run dev running?): {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
