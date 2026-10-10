"""
Demo mode: seeds SIMULATED history so you can show the diff + trend views
without waiting days for real job-market changes.

All demo data is fictional and stored under a query prefixed with "DEMO:".
Say so in your video/submission - do not present it as real market data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import digest
import storage

DEMO_QUERY = "DEMO: LLM infra engineer"


def _p(company, title, seniority, location, remote, note):
    return {
        "company": company, "title": title, "seniority": seniority,
        "location": location, "remote": remote, "posted": "simulated",
        "signal_note": note, "source_url": "https://example.com/demo",
    }


WEEKS = [
    [_p("ExampleCo A", "LLM Infra Engineer", "mid", "Bengaluru", False, "Simulated baseline posting."),
     _p("ExampleCo B", "ML Platform Engineer", "senior", "Hyderabad", True, "Simulated baseline posting.")],
    [_p("ExampleCo B", "ML Platform Engineer", "senior", "Hyderabad", True, "Still open."),
     _p("ExampleCo C", "Staff LLM Infra Engineer", "lead/staff", "Chennai", False, "New staff-level role: scaling signal."),
     _p("ExampleCo D", "GPU Cluster Engineer", "mid", "Pune", False, "New team forming.")],
    [_p("ExampleCo B", "ML Platform Engineer", "senior", "Hyderabad", True, "Still open."),
     _p("ExampleCo C", "Staff LLM Infra Engineer", "lead/staff", "Chennai", False, "Still open."),
     _p("ExampleCo D", "GPU Cluster Engineer", "mid", "Pune", False, "Still open."),
     _p("ExampleCo D", "Inference Engineer", "senior", "Pune", True, "Second role at same company: ramp-up."),
     _p("ExampleCo E", "LLM Infra Engineer", "junior", "Remote", True, "New entrant hiring.")],
]


def run_demo() -> str:
    conn = storage.get_connection()
    with conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM runs WHERE query = ?", (DEMO_QUERY,))]
        for i in ids:
            conn.execute("DELETE FROM postings WHERE run_id = ?", (i,))
        conn.execute("DELETE FROM runs WHERE query = ?", (DEMO_QUERY,))
    conn.close()

    now = datetime.now(timezone.utc)
    run_ids = []
    for i, postings in enumerate(WEEKS):
        when = (now - timedelta(weeks=len(WEEKS) - 1 - i)).isoformat()
        run_ids.append(storage.save_run(DEMO_QUERY, "India", postings, run_at=when))

    digest.console.print("[bold yellow]SIMULATED DEMO DATA - not real job postings[/bold yellow]")
    digest.print_baseline(DEMO_QUERY, WEEKS[0])
    for prev_id, cur_id in zip(run_ids, run_ids[1:]):
        d = storage.diff_runs(prev_id, cur_id)
        digest.print_digest(DEMO_QUERY, d.new, d.disappeared, d.unchanged_count)
    digest.print_trend(DEMO_QUERY, storage.get_posting_count_by_run(DEMO_QUERY))
    return DEMO_QUERY
