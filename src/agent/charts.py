"""Generate charts for lab reports and essays.

Two entry points:
- ``chart_from_data`` : you hand it numbers, it renders a clean figure.
- ``chart_citations`` : quick bar chart of citation counts across the
  papers a search returned (a useful "what's influential here" view).
"""

from __future__ import annotations

import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # no display needed, we save straight to file
import matplotlib.pyplot as plt

from .config import OUTPUT_DIR
from .sources import Paper


def _outfile(name: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{name}-{stamp}.png")


def chart_from_data(
    x: list,
    y: list,
    kind: str = "bar",
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
) -> str:
    """Render a chart from paired data. Returns the saved file path.

    ``kind`` is one of: bar, line, scatter.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    if kind == "line":
        ax.plot(x, y, marker="o")
    elif kind == "scatter":
        ax.scatter(x, y)
    else:  # bar is the safe default
        ax.bar([str(v) for v in x], y)

    ax.set_title(title or "Figure")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if kind != "bar":
        ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = _outfile("chart")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_citations(papers: list[Paper]) -> str | None:
    """Bar chart of citation counts for papers that report them."""
    labelled = [
        (p.title[:40] + ("..." if len(p.title) > 40 else ""), p.citations)
        for p in papers
        if p.citations is not None
    ]
    if not labelled:
        return None

    labelled.sort(key=lambda t: t[1], reverse=True)
    titles, counts = zip(*labelled)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(range(len(titles)), counts)
    ax.set_yticks(range(len(titles)))
    ax.set_yticklabels(titles, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Citations")
    ax.set_title("Most-cited papers in this search")
    fig.tight_layout()

    path = _outfile("citations")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
