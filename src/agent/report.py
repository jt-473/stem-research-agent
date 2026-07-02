"""Assemble search + summaries + synthesis into a Markdown research brief."""

from __future__ import annotations

import os
from datetime import date

from .config import OUTPUT_DIR
from .sources import Paper


def build_report(
    question: str,
    papers: list[Paper],
    summaries: list[dict],
    synthesis: str,
    figures: list[str] | None = None,
) -> str:
    """Write a Markdown brief and return its file path."""
    figures = figures or []
    lines: list[str] = []

    lines.append(f"# Research brief: {question}")
    lines.append("")
    lines.append(f"*Generated {date.today().isoformat()} by stem-research-agent*")
    lines.append("")

    lines.append("## Synthesis")
    lines.append("")
    lines.append(synthesis)
    lines.append("")

    if figures:
        lines.append("## Figures")
        lines.append("")
        for fig in figures:
            rel = os.path.relpath(fig, OUTPUT_DIR)
            lines.append(f"![figure]({rel})")
            lines.append("")

    lines.append("## Sources")
    lines.append("")
    for i, (p, s) in enumerate(zip(papers, summaries), start=1):
        lines.append(f"### [{i}] {p.title}")
        lines.append("")
        lines.append(f"- **Source:** {p.source}"
                     + (f" · {p.citations} citations" if p.citations is not None else ""))
        lines.append(f"- **Reference:** {p.citation_line()}")
        if p.url:
            lines.append(f"- **Link:** {p.url}")
        if s.get("main_finding"):
            lines.append(f"- **Main finding:** {s['main_finding']}")
        if s.get("method"):
            lines.append(f"- **Method:** {s['method']}")
        if s.get("key_numbers"):
            nums = "; ".join(s["key_numbers"])
            lines.append(f"- **Key numbers:** {nums}")
        lines.append("")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = "".join(c if c.isalnum() else "-" for c in question.lower())[:40].strip("-")
    path = os.path.join(OUTPUT_DIR, f"brief-{slug}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path
