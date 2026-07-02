"""Pull specific, quotable passages out of a paper with a ready citation.

For each passage the student gets:
- the verbatim quote (so they can drop it straight into an essay)
- why it's useful / what it supports
- an in-text citation in their chosen style, with a locator

Right now quotes come from the abstract, so the locator is "abstract".
When full-text parsing lands (roadmap), the same function can take the
body text and give real page / section locators.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from . import citations
from .config import MODEL
from .sources import Paper

client = Anthropic()

PASSAGE_SYSTEM = """You extract quotable passages from academic text for a \
student's essay. You quote VERBATIM — every quote must appear word-for-word in \
the source text you are given. Never paraphrase inside quotation marks and never \
invent a sentence that isn't there. If the text has nothing useful, return an \
empty list."""


def extract_passages(
    paper: Paper,
    focus: str = "",
    style: str = "harvard",
    n: int = 3,
    number: int | None = None,
    body: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to ``n`` quotable passages with citations.

    ``focus`` narrows quotes to a specific argument or claim. ``body`` is
    optional full text; when absent we quote from the abstract and mark the
    locator accordingly.
    """
    source_text = body or paper.abstract
    if not source_text:
        return []

    locus_label = "the full text" if body else "the abstract"
    focus_line = f"Focus on passages about: {focus}\n" if focus else ""

    prompt = f"""From the text below, pull up to {n} short passages a student \
could quote in an essay. {focus_line}
Text (from {locus_label} of "{paper.title}"):
\"\"\"
{source_text}
\"\"\"

Return ONLY valid JSON: a list of objects with keys:
- "quote": the exact words from the text, verbatim
- "supports": one short phrase on what claim this quote backs up
Return [] if nothing is worth quoting."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=PASSAGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = _safe_list(resp.content[0].text)

    locator = "abstract" if not body else None
    out: list[dict[str, Any]] = []
    for item in raw:
        quote = (item.get("quote") or "").strip().strip('"')
        if not quote:
            continue
        # Guard against the model drifting from the source text.
        if not body and not _appears_in(quote, source_text):
            continue
        out.append(
            {
                "quote": quote,
                "supports": item.get("supports", ""),
                "in_text": citations.in_text(paper, style, locator=locator, number=number),
                "reference": citations.format_reference(paper, style, number=number),
            }
        )
    return out


def _appears_in(quote: str, text: str) -> bool:
    """Loose check that a quote really came from the source (ignore whitespace)."""
    norm = lambda s: " ".join(s.lower().split())
    return norm(quote) in norm(text)


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
