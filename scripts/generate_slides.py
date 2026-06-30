#!/usr/bin/env python3
"""Generate carousel slides JSON via hybrid LLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.llm_hybrid import draft, parse_slides_json, polish


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate slides.json from a topic")
    parser.add_argument("--topic", required=True, help="Topic or one-line hook seed")
    parser.add_argument(
        "--theme",
        choices=("tech_insight", "job_approach"),
        default="tech_insight",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("export/slides.json"),
    )
    parser.add_argument("--no-polish", action="store_true", help="Ollama draft only")
    args = parser.parse_args()

    theme_path = ROOT / "themes" / f"{args.theme}.txt"
    system = theme_path.read_text(encoding="utf-8")
    prompt = f"Topic: {args.topic}\n\nReturn JSON with hook, slides (6-8), hashtags."

    print("Drafting with Ollama…", file=sys.stderr)
    raw = draft(prompt, system=system)

    if not args.no_polish:
        print("Polishing…", file=sys.stderr)
        raw = polish(
            f"Polish this carousel JSON. Keep structure. Input:\n{raw}",
            system=system,
            theme=args.theme,
        )

    data = parse_slides_json(raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
