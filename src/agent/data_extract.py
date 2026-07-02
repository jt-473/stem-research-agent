"""Pull quantitative results out of papers and chart them across studies.

The extraction is LLM-based: Claude reads each paper's text and returns
structured numbers (label, value, unit, context). Numbers that share a
unit across two or more papers can then be charted side by side, which
is the "compare results across studies" figure people actually put in
lab reports.

Extracted values are only as good as what the papers state. Every number
carries the sentence it came from so you can check it against the source.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from . import charts, llm
from .fulltext import fetch_fulltext
from .sources import Paper

MAX_TEXT_CHARS = 15_000

EXTRACT_SYSTEM = """You extract quantitative results from academic text. \
Only report numbers that are explicitly stated in the text. Never estimate, \
never convert units, never fill in a number the text doesn't give. Every \
number must come with the exact sentence it appears in."""


def extract_numbers(
    paper: Paper, focus: str = "", use_fulltext: bool = True
) -> list[dict[str, Any]]:
    """Return numeric results from one paper.

    Each item: {"label", "value", "unit", "context"} where context is the
    sentence the number came from.
    """
    full = fetch_fulltext(paper) if use_fulltext else None
    text = full.capped_text(MAX_TEXT_CHARS) if full else paper.abstract
    if not text:
        return []

    focus_line = f"Focus on numbers about: {focus}\n" if focus else ""
    prompt = f"""From the text below, extract the quantitative results. {focus_line}
Text (from "{paper.title}"):
\"\"\"
{text}
\"\"\"

Return ONLY valid JSON: a list of objects with keys:
- "label": short name for what was measured (e.g. "reaction time improvement")
- "value": the number itself (a JSON number, not a string)
- "unit": the unit as stated (e.g. "%", "ms", "mg/kg"); "" if unitless
- "context": the exact sentence the number appears in
Skip citation counts, sample sizes are fine to include. Return [] if there
are no clear quantitative results."""

    raw = _safe_list(llm.complete(prompt, system=EXTRACT_SYSTEM, max_tokens=1200))

    out = []
    for item in raw:
        value = item.get("value")
        if not isinstance(value, (int, float)):
            continue  # refuse anything that isn't a real number
        out.append(
            {
                "label": str(item.get("label", "")).strip(),
                "value": value,
                "unit": str(item.get("unit", "")).strip(),
                "context": str(item.get("context", "")).strip(),
                "paper": paper.title,
                "source": "full text" if full else "abstract",
            }
        )
    return out


def comparison_chart(all_numbers: list[dict[str, Any]]) -> str | None:
    """Chart values that share a unit across papers. Returns path or None.

    Picks the unit with the most data points from at least two different
    papers, so the chart is a real cross-study comparison and not a single
    paper's numbers restated.
    """
    by_unit: dict[str, list[dict]] = defaultdict(list)
    for n in all_numbers:
        if n["unit"]:
            by_unit[n["unit"]].append(n)

    best_unit, best = None, []
    for unit, rows in by_unit.items():
        papers_covered = {r["paper"] for r in rows}
        if len(papers_covered) >= 2 and len(rows) > len(best):
            best_unit, best = unit, rows

    if not best_unit:
        return None

    labels = [
        f"{r['label'][:24]}\n({r['paper'][:24]}...)" if len(r["paper"]) > 24
        else f"{r['label'][:24]}\n({r['paper']})"
        for r in best
    ]
    values = [r["value"] for r in best]
    return charts.chart_from_data(
        x=labels,
        y=values,
        kind="bar",
        title=f"Reported results across studies ({best_unit})",
        ylabel=best_unit,
    )


def _safe_list(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text.strip())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
