"""Terminal digest and trend output using rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_baseline(query, postings):
    console.print(Panel(
        f"[bold]Baseline established[/bold] for [cyan]{query}[/cyan] - "
        f"{len(postings)} postings saved.\nRun this again later to see what changed.",
        title="Hiring Signal", border_style="green"))
    table = Table(title="Current postings")
    for col in ("Company", "Title", "Seniority", "Location", "Signal note"):
        table.add_column(col, overflow="fold")
    for p in postings:
        table.add_row(p.get("company", "-"), p.get("title", "-"), p.get("seniority", "-"),
                      p.get("location", "-"), p.get("signal_note", "-"))
    console.print(table)


def print_digest(query, new, disappeared, unchanged_count):
    console.print(Panel(
        f"[bold]{query}[/bold] - [green]{len(new)} new[/green] · "
        f"[red]{len(disappeared)} disappeared[/red] · {unchanged_count} unchanged since last check",
        title="Hiring Signal Digest", border_style="cyan"))

    if new:
        t = Table(title="New postings")
        for col in ("Company", "Title", "Seniority", "Location", "Signal note"):
            t.add_column(col, overflow="fold")
        for r in new:
            t.add_row(r["company"] or "-", r["title"] or "-", r["seniority"] or "-",
                      r["location"] or "-", r["signal_note"] or "-")
        console.print(t)

    if disappeared:
        t = Table(title="Disappeared postings (filled or pulled)")
        for col in ("Company", "Title", "Location"):
            t.add_column(col, overflow="fold")
        for r in disappeared:
            t.add_row(r["company"] or "-", r["title"] or "-", r["location"] or "-")
        console.print(t)

    if not new and not disappeared:
        console.print("[dim]No change since last check.[/dim]")


def print_trend(query, counts):
    t = Table(title=f"Posting-volume trend - {query}")
    t.add_column("Run time (UTC)")
    t.add_column("Postings", justify="right")
    t.add_column("")
    mx = max((c for _, c in counts), default=1) or 1
    for run_at, count in counts:
        bar = "█" * max(1, int(count / mx * 30)) if count else ""
        t.add_row(run_at, str(count), f"[cyan]{bar}[/cyan]")
    console.print(t)
