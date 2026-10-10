"""Thin wrapper around SerpApi's Google Jobs engine. Docs: https://serpapi.com/google-jobs-api"""

from __future__ import annotations

from typing import Any

import requests

from config import get_serpapi_key

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiError(RuntimeError):
    pass


def fetch_job_postings(
    query: str,
    location: str | None = None,
    companies: list[str] | None = None,
    max_results: int = 30,
) -> list[dict[str, Any]]:
    api_key = get_serpapi_key()
    if not api_key:
        raise SerpApiError(
            "SerpApi key not found. Paste it into config.py (SERPAPI_KEY_HERE) "
            "or set SERPAPI_API_KEY in .env."
        )

    searches = [f"{query} at {c}" for c in companies] if companies else [query]

    all_results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for search_query in searches:
        params = {"engine": "google_jobs", "q": search_query, "api_key": api_key}
        if location:
            params["location"] = location

        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        if response.status_code != 200:
            raise SerpApiError(f"SerpApi request failed ({response.status_code}): {response.text[:300]}")

        data = response.json()
        if "error" in data and not data.get("jobs_results"):
            # "hasn't returned any results" is not fatal when scanning several companies
            if len(searches) == 1:
                raise SerpApiError(f"SerpApi error: {data['error']}")
            continue

        for job in data.get("jobs_results", []):
            job_id = job.get("job_id") or f"{job.get('title')}::{job.get('company_name')}"
            if job_id in seen:
                continue
            seen.add(job_id)
            all_results.append(job)

        if len(all_results) >= max_results:
            break

    return all_results[:max_results]
