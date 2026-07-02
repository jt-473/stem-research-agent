"""Pull specific, quotable passages out of a paper with a ready citation.

For each passage the student gets:
- the verbatim quote (so they can drop it straight into an essay)
- why it's useful / what it supports
- an in-text citation in their chosen style, with a locator

If the paper's full text is available (open-access PDF), quotes come from
the body and the locator is a real page number. Otherwise we fall back to
the abstract and label the locator "abstract".
"""

from __future__ import annotations

import json
from typing import Any

from . import citations, llm
from .fulltext import FullText, fetch_fulltext
from .sources import Paper

# How much full text to send to the model per paper (rough token budget).
MAX_FULLTEXT_CHARS = 18_000

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
    use_fulltext: bool = True,
) -> list[dict[str, Any]]:
    """Return up to ``n`` quotable passages with citations.

    ``focus`` narrows quotes to a specific argument or claim. When
    ``use_fulltext`` is on we try the open-access PDF for real page
    locators, falling back to the abstract if there's no usable PDF.
    """
    full: FullText | None = fetch_fulltext(paper) if use_fulltext else None

    if full:
        source_text = full.capped_text(MAX_FULLTEXT_CHARS)
        locus_label = "the full text"
    else:
        source_text = paper.abstract
        locus_label = "the abstract"

    if not source_text:
        return []

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

    raw = _safe_list(llm.complete(prompt, system=PASSAGE_SYSTEM, max_tokens=900))

    out: list[dict[str, Any]] = []
    for item in raw:
        quote = (item.get("quote") or "").strip().strip('"')
        if not quote:
            continue
        # Guard against the model drifting from the source text.
        if not _appears_in(quote, source_text):
            continue
        # Real page number from the PDF if we can find it; else abstract.
        locator = (full.locate(quote) if full else None) or (
            "abstract" if not full else "full text"
        )
        out.append(
            {
                "quote": quote,
                "supports": item.get("supports", ""),
                "locator": locator,
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
