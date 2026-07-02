"""The straight-line pipeline: question in, research brief out.

This is the reliable, non-agentic path. It runs the same steps every
time (search -> summarize -> synthesize -> report), which makes it easy
to reason about and cheap to run. The agentic loop in ``agent.py`` wraps
these same building blocks when you want the model to drive.
"""

from __future__ import annotations

from . import charts, passages as passages_mod, sources, summarize
from .config import DEFAULT_STYLE
from .report import build_report


def run(
    question: str,
    limit: int = 5,
    sources_list: list[str] | None = None,
    style: str = DEFAULT_STYLE,
    quotes: bool = False,
) -> dict:
    """Run the full pipeline and return paths + data.

    ``style`` sets the referencing style for the brief. ``quotes`` pulls
    quotable passages (with in-text citations) from each paper.
    """
    print(f"[1/5] Searching for: {question!r}")
    found = sources.search(question, limit=limit, sources=sources_list)
    if not found:
        raise SystemExit("No papers found. Try a broader query.")
    print(f"      Found {len(found)} papers.")

    print("[2/5] Summarizing papers with Claude...")
    summaries = [summarize.summarize_paper(p) for p in found]

    print("[3/5] Synthesizing an answer...")
    synthesis = summarize.synthesize(question, found, summaries)

    passages: list[list[dict]] | None = None
    if quotes:
        print(f"[4/5] Extracting quotable passages ({style} style)...")
        passages = [
            passages_mod.extract_passages(p, focus=question, style=style, number=i)
            for i, p in enumerate(found, start=1)
        ]
    else:
        print("[4/5] Skipping quote extraction (use --quotes to enable).")

    print("[5/5] Building figures + report...")
    figures = []
    citation_fig = charts.chart_citations(found)
    if citation_fig:
        figures.append(citation_fig)

    report_path = build_report(
        question, found, summaries, synthesis, figures, style=style, passages=passages
    )

    return {
        "papers": found,
        "summaries": summaries,
        "synthesis": synthesis,
        "figures": figures,
        "passages": passages,
        "report": report_path,
        "style": style,
    }
