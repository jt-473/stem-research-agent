"""A guided, question-by-question mode for people new to the tool.

Running the app with no command drops you here. It asks plain questions
(what are you researching, which citation style) and then finds papers and
formats their references, so nobody has to memorize command-line flags.
"""

from __future__ import annotations

from .citations import STYLES, format_reference, in_text
from .config import DEFAULT_STYLE

BANNER = r"""
  STEM Research Agent
  Find papers and cite them your way. Free, no key needed.
"""


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        raise SystemExit(0)
    return answer or default


def _pick_style() -> str:
    styles = list(STYLES.keys())
    print("\nWhich referencing style does your class use?")
    for i, key in enumerate(styles, start=1):
        marker = " (default)" if key == DEFAULT_STYLE else ""
        blurb = STYLES[key].split(". ")[0]
        print(f"  {i}. {blurb}{marker}")
    choice = _ask("Pick a number", default=str(styles.index(DEFAULT_STYLE) + 1))
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(styles):
            return styles[idx]
    except ValueError:
        pass
    if choice.lower() in styles:
        return choice.lower()
    print(f"Didn't recognize that, using {DEFAULT_STYLE}.")
    return DEFAULT_STYLE


def run_wizard() -> int:
    """Walk a first-time user through one search."""
    print(BANNER)

    question = _ask("What do you want to research")
    while not question:
        print("Type a topic, for example: caffeine reaction time")
        question = _ask("What do you want to research")

    style = _pick_style()

    limit_raw = _ask("\nHow many papers per source", default="5")
    try:
        limit = max(1, min(15, int(limit_raw)))
    except ValueError:
        limit = 5

    from .sources import search

    print("\nSearching...\n")
    papers = search(question, limit=limit)
    if not papers:
        print("No papers matched. Try broader words (keywords work better than "
              "full questions).")
        return 0

    print(f"Found {len(papers)} papers. References ({style}):\n")
    for i, p in enumerate(papers, start=1):
        print(format_reference(p, style, number=i))
        print(f"    in-text: {in_text(p, style, number=i)}\n")
    return 0
