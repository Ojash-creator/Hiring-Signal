"""
Hiring Signal CLI.

    python main.py track --query "LLM infra engineer" --location "India"
    python main.py track --query "LLM infra engineer" --companies "Google,Razorpay,Zerodha"
    python main.py trend --query "LLM infra engineer"
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

import digest  # noqa: E402
import storage  # noqa: E402
from extractor import extraction_mode, normalize_postings  # noqa: E402
from serpapi_client import SerpApiError, fetch_job_postings  # noqa: E402


def cmd_track(args):
    companies = [c.strip() for c in args.companies.split(",")] if args.companies else None
    print(f"Fetching postings for '{args.query}'" + (f" in {args.location}" if args.location else "") + "...")
    try:
        raw = fetch_job_postings(args.query, args.location, companies, args.max_results)
    except SerpApiError as e:
        print(f"Error fetching postings: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Got {len(raw)} raw postings. Normalizing ({extraction_mode()} mode)...")
    normalized = normalize_postings(raw)
    run_id = storage.save_run(args.query, args.location, normalized)
    prev = storage.get_previous_run(args.query, run_id)

    if prev is None:
        digest.print_baseline(args.query, normalized)
    else:
        d = storage.diff_runs(prev["id"], run_id)
        digest.print_digest(args.query, d.new, d.disappeared, d.unchanged_count)


def cmd_trend(args):
    counts = storage.get_posting_count_by_run(args.query)
    if not counts:
        print(f"No history yet for '{args.query}'. Run `track` first.")
        return
    digest.print_trend(args.query, counts)


def cmd_demo(args):
    from demo import run_demo

    run_demo()


def cmd_chart(args):
    from chart import export_trend_png

    try:
        path = export_trend_png(args.query, args.out)
    except ValueError as e:
        print(e)
        return
    print(f"Saved chart to {path}")


def main():
    parser = argparse.ArgumentParser(description="Hiring Signal - hiring trends via SerpApi + Claude")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("track", help="Fetch current postings and diff against last run")
    t.add_argument("--query", required=True)
    t.add_argument("--location", default=None)
    t.add_argument("--companies", default=None, help="Comma-separated watchlist (optional)")
    t.add_argument("--max-results", type=int, default=30, dest="max_results")
    t.set_defaults(func=cmd_track)

    tr = sub.add_parser("trend", help="Posting-volume trend over time")
    tr.add_argument("--query", required=True)
    tr.set_defaults(func=cmd_trend)

    demo_parser = sub.add_parser("demo", help="Seed SIMULATED history to preview the diff/trend views")
    demo_parser.set_defaults(func=cmd_demo)

    chart_parser = sub.add_parser("chart", help="Export the trend as a PNG")
    chart_parser.add_argument("--query", required=True)
    chart_parser.add_argument("--out", default="trend.png")
    chart_parser.set_defaults(func=cmd_chart)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
