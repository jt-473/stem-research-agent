"""A guided, question-by-question mode for people new to the tool.

Running the app with no command drops you here. It asks plain questions
(what are you researching, which style, do you want quotes) and then runs
the research pipeline, so nobody has to memorize command-line flags.
"""

from __future__ import annotations

from .citations import STYLES
from .config import DEFAULT_STYLE, API_KEY_HELP, has_api_key

BANNER = r"""
  STEM Research Agent
  Find papers, cite them your way, and pull quotes for your report.
"""


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        raise SystemExit(0)
    return answer or default


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    answer = _ask(f"{prompt} ({d})").lower()
    if not answer:
        return default
    return answer.startswith("y")


def _pick_style() -> str:
    styles = list(STYLES.keys())
    print("\nWhich referencing style does your class use?")
    for i, key in enumerate(styles, start=1):
        marker = " (default)" if key == DEFAULT_STYLE else ""
        # Show just the first sentence of each description to keep it short.
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
    """Walk a first-time user through one research run."""
    print(BANNER)

    question = _ask("What do you want to research")
    while not question:
        print("Type a question or topic, for example: does caffeine improve reaction time")
        question = _ask("What do you want to research")

    style = _pick_style()

    print()
    want_quotes = _ask_yes_no(
        "Pull quotable passages you can paste into your essay?", default=True
    )
    limit_raw = _ask("\nHow many papers per source", default="5")
    try:
        limit = max(1, min(15, int(limit_raw)))
    except ValueError:
        limit = 5

    # If quotes are on, we need the AI features (and a key). Warn kindly.
    if want_quotes and not has_api_key():
        print("\n" + API_KEY_HELP)
        if not _ask_yes_no("\nContinue with just a paper search (no AI summary/quotes)?", default=True):
            return 0
        return _search_only(question, style, limit)

    if not has_api_key():
        print("\n(No API key set, so I'll just list and cite papers, no AI summary.)")
        return _search_only(question, style, limit)

    print("\nWorking on it. This can take a minute...\n")
    from .pipeline import run

    try:
        result = run(question, limit=limit, style=style, quotes=want_quotes)
    except Exception as exc:  # keep the beginner out of a stack trace
        print(f"Something went wrong: {exc}")
        print("Try a broader topic, or run 'python main.py search \"your topic\"' to test the connection.")
        return 1

    print("\n" + "=" * 60)
    print("Synthesis:\n")
    print(result["synthesis"])
    print("\n" + "=" * 60)
    print(f"\nFull report saved to: {result['report']}")
    for fig in result["figures"]:
        print(f"Figure saved to: {fig}")
    print(f"\nStyle used: {style.upper()}. Open the report file to see the "
          "sources, citations, and quotes.")
    return 0


def _search_only(question: str, style: str, limit: int) -> int:
    """Fallback path with no LLM calls: search + formatted references."""
    from .citations import format_reference, in_text
    from .sources import search

    print("\nSearching...\n")
    papers = search(question, limit=limit)
    if not papers:
        print("No papers found. Try a broader topic.")
        return 0
    print(f"Found {len(papers)} papers. References ({style}):\n")
    for i, p in enumerate(papers, start=1):
        print(format_reference(p, style, number=i))
        print(f"    in-text: {in_text(p, style, number=i)}\n")
    return 0
