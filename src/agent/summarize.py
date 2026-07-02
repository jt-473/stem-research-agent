"""Turn raw paper abstracts into structured, usable summaries with Claude."""

from __future__ import annotations

import json
from typing import Any

from .config import MODEL, get_client
from .sources import Paper

SUMMARY_SYSTEM = """You are a STEM research assistant helping a student write \
lab reports and essays. You summarize academic papers accurately and never \
invent findings, numbers, or citations that are not present in the text you \
are given. If a detail isn't in the abstract, say so rather than guessing."""


def summarize_paper(paper: Paper) -> dict[str, Any]:
    """Extract a structured summary from a single paper's abstract."""
    if not paper.abstract:
        return {
            "main_finding": "(no abstract available)",
            "method": "",
            "key_numbers": [],
            "relevance": "",
        }

    prompt = f"""Summarize this paper for a student's research notes.

Title: {paper.title}
Abstract: {paper.abstract}

Return ONLY valid JSON with these keys:
- "main_finding": one sentence, the core result
- "method": one sentence on how they did it
- "key_numbers": a list of important quantitative results as strings \
(empty list if none are stated)
- "relevance": one sentence on when a student would cite this"""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=600,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    return _safe_json(text)


def synthesize(question: str, papers: list[Paper], summaries: list[dict]) -> str:
    """Write a short literature-synthesis paragraph across several papers.

    Every claim is tied to a numbered source so nothing is uncited.
    """
    lines = []
    for i, (p, s) in enumerate(zip(papers, summaries), start=1):
        lines.append(
            f"[{i}] {p.title} ({p.year}) — {s.get('main_finding', '')}"
        )
    sources_block = "\n".join(lines)

    prompt = f"""Research question: {question}

Here are summarized sources, each with a number:
{sources_block}

Write a 4-6 sentence synthesis that answers the research question using \
only these sources. Cite claims inline with their number like [1], [2]. \
Do not introduce facts that aren't in the sources above."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=800,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def _safe_json(text: str) -> dict[str, Any]:
    """Parse JSON out of a model response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"main_finding": text, "method": "", "key_numbers": [], "relevance": ""}
