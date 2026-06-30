#!/usr/bin/env python3
"""Build clip manifest from career-ops pipeline or a job URL."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.llm_hybrid import draft, parse_slides_json, polish

PENDING_LINE = re.compile(r"^- \[ \]\s+(.+)$", re.MULTILINE)


@dataclass
class PipelineJob:
    url: str
    company: str | None
    title: str | None
    raw_line: str


def career_ops_root() -> Path:
    return Path(os.getenv("CAREER_OPS_PATH", "/Users/nehatiwari/localcode/career-ops"))


def parse_pipeline(path: Path) -> list[PipelineJob]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Run career-ops scan first or use --job-url / --jd-file."
        )
    text = path.read_text(encoding="utf-8")
    jobs: list[PipelineJob] = []
    for match in PENDING_LINE.finditer(text):
        line = match.group(1).strip()
        parts = [p.strip() for p in line.split("|")]
        url = parts[0]
        company = parts[1] if len(parts) > 1 else None
        title = parts[2] if len(parts) > 2 else None
        if url.startswith("http"):
            jobs.append(PipelineJob(url=url, company=company, title=title, raw_line=line))
    return jobs


def fetch_jd_text(url: str) -> str:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "clip-studio/1.0"})
        resp.raise_for_status()
        html = resp.text
    # Lightweight HTML strip (no extra deps)
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:12000]


def build_prompt(
    *,
    jd_text: str,
    company: str | None,
    title: str | None,
    anon: bool,
) -> str:
    label = "a senior data engineering role"
    if not anon and company and title:
        label = f"{title} at {company}"
    elif title:
        label = title
    elif company:
        label = f"role at {company}"

    return (
        f"Job: {label}\n"
        f"anonymize={anon}\n\n"
        f"JD excerpt:\n{jd_text[:8000]}\n\n"
        "Return JSON with hook, slides (6-8), hashtags for a 'how to approach this job' carousel."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Job → slides.json + manifest stub")
    parser.add_argument("--from-pipeline", action="store_true")
    parser.add_argument("--pick", type=int, default=1, help="1-based index in Pendientes")
    parser.add_argument("--job-url", type=str)
    parser.add_argument("--jd-file", type=Path)
    parser.add_argument("--company", type=str)
    parser.add_argument("--title", type=str)
    parser.add_argument("--anon", action="store_true", help="Anonymize company (default)")
    parser.add_argument("--name-company", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("export"))
    args = parser.parse_args()

    anon = not args.name_company  # default anonymized

    if args.from_pipeline:
        pipeline = career_ops_root() / "data" / "pipeline.md"
        jobs = parse_pipeline(pipeline)
        if not jobs:
            print("No pending jobs in pipeline.md", file=sys.stderr)
            return 1
        if args.pick < 1 or args.pick > len(jobs):
            print(f"--pick must be 1..{len(jobs)}", file=sys.stderr)
            return 1
        job = jobs[args.pick - 1]
        url, company, title = job.url, job.company, job.title
    elif args.job_url:
        url, company, title = args.job_url, args.company, args.title
    elif args.jd_file:
        url, company, title = "file://local", args.company, args.title
    else:
        parser.error("Use --from-pipeline, --job-url, or --jd-file")

    if args.jd_file:
        jd_text = args.jd_file.read_text(encoding="utf-8")
    else:
        print(f"Fetching JD from {url}…", file=sys.stderr)
        jd_text = fetch_jd_text(url)

    theme_path = ROOT / "themes" / "job_approach.txt"
    system = theme_path.read_text(encoding="utf-8")
    prompt = build_prompt(jd_text=jd_text, company=company, title=title, anon=anon)

    print("Drafting slides (Ollama)…", file=sys.stderr)
    raw = draft(prompt, system=system)
    print("Polishing (job theme → Anthropic if set, else Groq)…", file=sys.stderr)
    raw = polish(f"Polish this JSON:\n{raw}", system=system, theme="job_approach")
    data = parse_slides_json(raw)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    slides_path = args.out_dir / "slides.json"
    slides_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    manifest = {
        "hook": data["hook"],
        "slides": data["slides"],
        "theme": "job_approach",
        "hashtags": data.get("hashtags", ["dataengineering", "career", "jobsearch"]),
        "job_url": url if url.startswith("http") else None,
        "company": None if anon else company,
        "title": title,
        "anon": anon,
        "audio_path": None,
        "video_path": None,
        "platforms": {"linkedin": "carousel", "youtube": "shorts", "instagram": "video"},
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote {slides_path} and {manifest_path}")
    print("Next: add audio, then run:")
    print(f"  python main.py clip --manifest {manifest_path} --audio assets/audio/YOUR.mp3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
