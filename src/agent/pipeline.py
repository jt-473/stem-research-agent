"""The straight-line pipeline: question in, research brief out.

This is the reliable, non-agentic path. It runs the same steps every
time (search -> summarize -> synthesize -> report), which makes it easy
to reason about and cheap to run. The agentic loop in ``agent.py`` wraps
these same building blocks when you want the model to drive.
"""

from __future__ import annotations

from . import charts, sources, summarize
from .report import build_report


def run(question: str, limit: int = 5, sources_list: list[str] | None = None) -> dict:
    """Run the full pipeline and return paths + data."""
    print(f"[1/4] Searching for: {question!r}")
    papers = sources.search(question, limit=limit, sources=sources_list)
    if not papers:
        raise SystemExit("No papers found. Try a broader query.")
    print(f"      Found {len(papers)} papers.")

    print("[2/4] Summarizing papers with Claude...")
    summaries = [summarize.summarize_paper(p) for p in papers]

    print("[3/4] Synthesizing an answer...")
    synthesis = summarize.synthesize(question, papers, summaries)

    print("[4/4] Building figures + report...")
    figures = []
    citation_fig = charts.chart_citations(papers)
    if citation_fig:
        figures.append(citation_fig)

    report_path = build_report(question, papers, summaries, synthesis, figures)

    return {
        "papers": papers,
        "summaries": summaries,
        "synthesis": synthesis,
        "figures": figures,
        "report": report_path,
    }
