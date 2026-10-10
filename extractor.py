"""
Turns raw SerpApi Google Jobs results into a consistent shape.

Two modes:

* rules   (default, needs only a SerpApi key): uses only the fields SerpApi
          returns (posted time, schedule type, remote flag, salary, source site,
          years of experience mentioned in the description). Nothing is invented.
* claude  (optional, if ANTHROPIC_API_KEY is set): Claude cleans the same data and
          writes a one-line signal note. If the call fails, rules mode is used.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from config import get_anthropic_key

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

CLAUDE_SYSTEM_PROMPT = """You normalize raw job-posting data into strict JSON.

You will receive a JSON array of raw job postings from a search API. For each
posting, output an object with exactly these fields:

- company: string
- title: string
- seniority: one of "junior", "mid", "senior", "lead/staff", "unknown"
- location: string (city/region, or "Remote" if remote)
- remote: boolean
- posted: string (relative time like "3 days ago", or "unknown")
- signal_note: one short sentence (<20 words) useful to a hiring-trend observer.
  Base this ONLY on information present in the posting; do not invent context.
- source_url: string (the original job link, copied through unchanged)

If a field cannot be determined, use "unknown" (or false for remote).
Respond with ONLY a JSON array. No prose, no markdown fences.
"""


def extraction_mode() -> str:
    return "claude" if get_anthropic_key() else "rules"


def normalize_postings(raw_postings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convenience wrapper that returns only the postings."""
    return normalize_with_info(raw_postings)[0]


def normalize_with_info(raw_postings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (postings, info). info = {"mode": "rules"|"claude", "ai_failed": bool}."""
    if not raw_postings:
        return [], {"mode": extraction_mode(), "ai_failed": False}

    if not get_anthropic_key():
        return [rules_normalize(j) for j in raw_postings], {"mode": "rules", "ai_failed": False}

    try:
        return _claude_normalize(raw_postings), {"mode": "claude", "ai_failed": False}
    except Exception:
        # Never let an LLM problem break the pipeline.
        return [rules_normalize(j) for j in raw_postings], {"mode": "rules", "ai_failed": True}


# --------------------------------------------------------------------------- claude
def _claude_normalize(raw_postings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed = [
        {
            "title": j.get("title"),
            "company_name": j.get("company_name"),
            "location": j.get("location"),
            "description": (j.get("description") or "")[:400],
            "detected_extensions": j.get("detected_extensions", {}),
            "share_link": _source_url(j),
        }
        for j in raw_postings
    ]
    response = requests.post(
        ANTHROPIC_ENDPOINT,
        headers={
            "x-api-key": get_anthropic_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "max_tokens": 4000,
            "system": CLAUDE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": json.dumps(trimmed)}],
        },
        timeout=60,
    )
    response.raise_for_status()
    blocks = [b["text"] for b in response.json().get("content", []) if b.get("type") == "text"]
    text = "\n".join(blocks).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(text)
    if not isinstance(parsed, list) or len(parsed) != len(raw_postings):
        raise ValueError("Unexpected model output")
    return parsed


# --------------------------------------------------------------------------- rules
def _source_url(job: dict[str, Any]) -> str:
    if job.get("share_link"):
        return job["share_link"]
    for opt in job.get("apply_options") or []:
        if opt.get("link"):
            return opt["link"]
    return job.get("apply_link") or ""


def rules_normalize(job: dict[str, Any]) -> dict[str, Any]:
    title = job.get("title") or "unknown"
    location = job.get("location") or "unknown"
    ext = job.get("detected_extensions") or {}
    description = job.get("description") or ""

    remote = bool(ext.get("work_from_home")) or "remote" in location.lower() or "remote" in title.lower()
    posted = ext.get("posted_at") or "unknown"

    return {
        "company": job.get("company_name") or "unknown",
        "title": title,
        "seniority": guess_seniority(title, description),
        "location": "Remote" if remote and location == "unknown" else location,
        "remote": remote,
        "posted": posted,
        "signal_note": build_note(job, ext, remote, posted),
        "source_url": _source_url(job),
    }


def build_note(job: dict[str, Any], ext: dict[str, Any], remote: bool, posted: str) -> str:
    """Facts-only summary built from fields SerpApi actually returned."""
    parts = []
    if posted != "unknown":
        parts.append(f"posted {posted}")
    if ext.get("schedule_type"):
        parts.append(str(ext["schedule_type"]).lower())
    if remote:
        parts.append("remote-friendly")
    if ext.get("salary"):
        parts.append(f"salary listed ({ext['salary']})")
    if job.get("via"):
        parts.append(str(job["via"]).replace("via ", "via "))
    note = ", ".join(parts)
    return (note[0].upper() + note[1:]) if note else "No extra details in listing."


_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", re.I)


def guess_seniority(title: str, description: str = "") -> str:
    t = (title or "").lower()
    if any(k in t for k in ("staff", "principal", "lead", "head of", "director")):
        return "lead/staff"
    if any(k in t for k in ("senior", "sr.", "sr ")):
        return "senior"
    if any(k in t for k in ("junior", "jr.", "jr ", "entry", "intern", "graduate", "fresher", "trainee")):
        return "junior"
    years = [int(m.group(1)) for m in _YEARS.finditer(description or "")]
    if years:
        y = min(years)
        return "junior" if y <= 2 else "mid" if y <= 5 else "senior"
    return "unknown"
