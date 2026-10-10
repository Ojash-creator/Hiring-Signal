"""
Hiring Signal - local web app.

    python app.py     ->  open http://localhost:5000
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request  # noqa: E402

import storage  # noqa: E402
from config import get_serpapi_key  # noqa: E402
from extractor import extraction_mode, normalize_with_info  # noqa: E402
from serpapi_client import SerpApiError, fetch_job_postings  # noqa: E402

app = Flask(__name__)


def _rows(rows):
    return [dict(r) for r in rows]


def build_report(query: str) -> dict:
    """Everything the UI needs for one tracked query."""
    runs = storage.get_runs(query)
    if not runs:
        return {"query": query, "runs": [], "steps": [], "latest": [], "demo": query.startswith("DEMO:")}

    counts = storage.get_posting_count_by_run(query)
    steps = []
    for prev, cur in zip(runs, runs[1:]):
        d = storage.diff_runs(prev["id"], cur["id"])
        steps.append({
            "run_at": cur["run_at"],
            "new": _rows(d.new),
            "disappeared": _rows(d.disappeared),
            "unchanged": d.unchanged_count,
        })

    return {
        "query": query,
        "demo": query.startswith("DEMO:"),
        "runs": [{"run_at": t, "count": c} for t, c in counts],
        "steps": steps,
        "latest": _rows(storage.get_postings_for_run(runs[-1]["id"])),
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        has_serpapi=bool(get_serpapi_key()),
        mode=extraction_mode(),
    )


@app.get("/api/queries")
def api_queries():
    return jsonify(storage.get_tracked_queries())


@app.get("/api/report")
def api_report():
    query = (request.args.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    return jsonify(build_report(query))


@app.post("/api/track")
def api_track():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    location = (body.get("location") or "").strip() or None
    companies = [c.strip() for c in (body.get("companies") or "").split(",") if c.strip()] or None
    try:
        max_results = max(1, min(int(body.get("max_results") or 30), 50))
    except (TypeError, ValueError):
        max_results = 30

    if not query:
        return jsonify({"error": "Please enter a role or skill to track."}), 400
    if query.startswith("DEMO:"):
        return jsonify({"error": "Queries starting with 'DEMO:' are reserved for simulated data."}), 400

    try:
        raw = fetch_job_postings(query, location, companies, max_results)
    except SerpApiError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # network errors etc.
        return jsonify({"error": f"Could not reach SerpApi: {e}"}), 502

    if not raw:
        return jsonify({"error": "SerpApi returned no job postings for that search. Try a broader query."}), 404

    normalized, info = normalize_with_info(raw)
    storage.save_run(query, location, normalized)

    report = build_report(query)
    report["mode"] = info["mode"]
    report["ai_failed"] = info["ai_failed"]
    return jsonify(report)


@app.post("/api/demo")
def api_demo():
    """Seed clearly-labelled SIMULATED history so the diff/trend views can be previewed."""
    from demo import run_demo

    return jsonify(build_report(run_demo()))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  Hiring Signal running at  http://localhost:{port}\n  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False)
