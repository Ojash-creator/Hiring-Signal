"""SQLite persistence + diff logic. posting_key = hash(company+title+location)."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "hiring_signal.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    location TEXT,
    run_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    company TEXT, title TEXT, seniority TEXT, location TEXT,
    remote INTEGER, posted TEXT, signal_note TEXT, source_url TEXT,
    posting_key TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_postings_run ON postings(run_id);
CREATE INDEX IF NOT EXISTS idx_postings_key ON postings(posting_key);
"""


def posting_key(p: dict[str, Any]) -> str:
    raw = "::".join((p.get(k) or "").lower().strip() for k in ("company", "title", "location"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(
    query: str,
    location: str | None,
    postings: list[dict[str, Any]],
    run_at: str | None = None,
) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO runs (query, location, run_at) VALUES (?, ?, ?)",
            (query, location, run_at or datetime.now(timezone.utc).isoformat()),
        )
        run_id = cur.lastrowid
        for p in postings:
            conn.execute(
                """INSERT INTO postings (run_id, company, title, seniority, location, remote,
                   posted, signal_note, source_url, posting_key) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (run_id, p.get("company"), p.get("title"), p.get("seniority"), p.get("location"),
                 1 if p.get("remote") else 0, p.get("posted"), p.get("signal_note"),
                 p.get("source_url"), posting_key(p)),
            )
    conn.close()
    return run_id


def get_previous_run(query: str, before_run_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM runs WHERE query = ? AND id < ? ORDER BY id DESC LIMIT 1",
        (query, before_run_id),
    ).fetchone()
    conn.close()
    return row


def get_postings_for_run(run_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM postings WHERE run_id = ?", (run_id,)).fetchall()
    conn.close()
    return rows


def get_posting_count_by_run(query: str) -> list[tuple[str, int]]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT runs.run_at, COUNT(postings.id) AS cnt FROM runs
           LEFT JOIN postings ON postings.run_id = runs.id
           WHERE runs.query = ? GROUP BY runs.id ORDER BY runs.id ASC""",
        (query,),
    ).fetchall()
    conn.close()
    return [(r["run_at"], r["cnt"]) for r in rows]


@dataclass
class Diff:
    new: list
    disappeared: list
    unchanged_count: int


def diff_runs(previous_run_id: int, current_run_id: int) -> Diff:
    prev = {r["posting_key"]: r for r in get_postings_for_run(previous_run_id)}
    curr = {r["posting_key"]: r for r in get_postings_for_run(current_run_id)}
    return Diff(
        new=[curr[k] for k in curr.keys() - prev.keys()],
        disappeared=[prev[k] for k in prev.keys() - curr.keys()],
        unchanged_count=len(curr.keys() & prev.keys()),
    )


def get_runs(query: str):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM runs WHERE query = ? ORDER BY id ASC", (query,)).fetchall()
    conn.close()
    return rows


def get_tracked_queries() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT query, MAX(id) AS last_id FROM runs GROUP BY query ORDER BY last_id DESC").fetchall()
    conn.close()
    return [r["query"] for r in rows]
