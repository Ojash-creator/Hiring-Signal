"""Export a posting-volume trend chart as a PNG (handy for the demo video)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import storage


def export_trend_png(query: str, out_path: str = "trend.png") -> str:
    counts = storage.get_posting_count_by_run(query)
    if not counts:
        raise ValueError(f"No history for '{query}'. Run `track` first.")
    labels = [c[0][:10] for c in counts]
    values = [c[1] for c in counts]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(labels, values, marker="o")
    ax.set_title(f"Posting volume over time: {query}")
    ax.set_ylabel("Postings found")
    ax.set_xlabel("Run date")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
