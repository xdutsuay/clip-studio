"""Hybrid LLM routing — Ollama draft, Groq/Anthropic polish (httpx only)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _ollama_chat(prompt: str, system: str) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(f"{base}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def _openai_compat_chat(
    prompt: str,
    system: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def draft(prompt: str, system: str = "") -> str:
    load_env_file()
    return _ollama_chat(prompt, system or "You are a concise technical writer.")


def polish(text: str, system: str = "", *, theme: str = "tech_insight") -> str:
    load_env_file()
    provider = os.getenv("LLM_POLISH_PROVIDER", "groq")
    if theme == "job_approach" and os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"

    sys_msg = system or (
        "You polish LinkedIn carousel copy for Kaustubh Tripathi, a senior data/platform engineer. "
        "Keep slides short (max 18 words each). Return valid JSON only."
    )

    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return _openai_compat_chat(
            text,
            sys_msg,
            base_url="https://api.anthropic.com/v1",
            api_key=key,
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        )

    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set (or set ANTHROPIC_API_KEY for job posts)")
    return _openai_compat_chat(
        text,
        sys_msg,
        base_url="https://api.groq.com/openai/v1",
        api_key=key,
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    )


def parse_slides_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    data = json.loads(raw)
    if "slides" not in data:
        raise ValueError("LLM response missing 'slides'")
    return data
