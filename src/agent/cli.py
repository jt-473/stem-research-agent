"""Command-line interface for the STEM research agent.

Run it with no command to get a guided, beginner-friendly mode. The named
commands (research, ask, cite, quotes, search, styles, doctor) are there
once you know what you want.
"""

from __future__ import annotations

import argparse
import sys

from .citations import STYLES
from .config import API_KEY_HELP, DEFAULT_STYLE, has_api_key

STYLE_CHOICES = list(STYLES.keys())


def _needs_key() -> bool:
    """Print setup help and signal to stop if there's no API key."""
    if has_api_key():
        return False
    print(API_KEY_HELP)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stem-research-agent",
        description="Pull papers, summarize them, cite them, and chart data. "
        "Run with no command for a guided mode.",
    )
    # command is optional: no command -> guided wizard.
    sub = parser.add_subparsers(dest="command")

    p_research = sub.add_parser("research", help="Search + summarize + write a brief")
    p_research.add_argument("question", help="Your research question")
    p_research.add_argument("-n", "--limit", type=int, default=5, help="Papers per source")
    p_research.add_argument(
        "--source", action="append",
        choices=["openalex", "arxiv", "pubmed", "crossref"],
        help="Restrict to a source (repeatable). Default: openalex, arxiv, "
        "pubmed. CrossRef is opt-in (huge coverage, but often no abstracts).",
    )
    p_research.add_argument(
        "--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE,
        help=f"Referencing style (default: {DEFAULT_STYLE})",
    )
    p_research.add_argument(
        "--quotes", action="store_true",
        help="Also pull quotable passages with in-text citations",
    )
    p_research.add_argument(
        "--loose", action="store_true",
        help="Don't require the query words to appear in each paper's title",
    )

    p_ask = sub.add_parser("ask", help="Let the agent decide how to answer")
    p_ask.add_argument("question", help="Your research question")

    p_search = sub.add_parser("search", help="Raw paper search, no LLM calls")
    p_search.add_argument("query")
    p_search.add_argument("-n", "--limit", type=int, default=5)
    p_search.add_argument(
        "--loose", action="store_true",
        help="Don't require the query words to appear in each paper's title",
    )

    p_cite = sub.add_parser("cite", help="Format references for a search (no LLM calls)")
    p_cite.add_argument("query")
    p_cite.add_argument("-n", "--limit", type=int, default=5)
    p_cite.add_argument("--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE)
    p_cite.add_argument("--loose", action="store_true", help="Skip the title-match filter")

    p_quotes = sub.add_parser("quotes", help="Pull quotable passages with citations")
    p_quotes.add_argument("query")
    p_quotes.add_argument("-n", "--limit", type=int, default=3)
    p_quotes.add_argument("--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE)
    p_quotes.add_argument("--focus", default="", help="Narrow quotes to a topic")
    p_quotes.add_argument(
        "--no-fulltext", action="store_true",
        help="Quote from abstracts only; don't download PDFs for page numbers",
    )
    p_quotes.add_argument("--loose", action="store_true", help="Skip the title-match filter")

    p_data = sub.add_parser("data", help="Extract numbers from papers + compare chart")
    p_data.add_argument("query")
    p_data.add_argument("-n", "--limit", type=int, default=4)
    p_data.add_argument("--focus", default="", help="What kind of numbers to look for")
    p_data.add_argument(
        "--no-fulltext", action="store_true",
        help="Extract from abstracts only; don't download PDFs",
    )

    p_web = sub.add_parser("web", help="Open the local web interface")
    p_web.add_argument("--port", type=int, default=8765)
    p_web.add_argument("--no-browser", action="store_true", help="Don't auto-open a browser")

    sub.add_parser("styles", help="List and explain the referencing styles")
    sub.add_parser("doctor", help="Check your setup (deps, API key)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # No command: friendly guided mode.
    if args.command is None:
        from .wizard import run_wizard

        return run_wizard()

    if args.command == "doctor":
        return _doctor()

    if args.command == "styles":
        from .citations import list_styles

        print("Supported referencing styles:\n")
        print(list_styles())
        print(f"\nDefault: {DEFAULT_STYLE}. Change it with --style or the "
              "CITATION_STYLE environment variable.")
        return 0

    if args.command == "search":
        from .sources import search

        papers = search(args.query, limit=args.limit, strict=not args.loose)
        if not papers:
            print("No papers matched. Try broader words, or add --loose.")
            return 1
        for p in papers:
            cites = f" · {p.citations} cites" if p.citations is not None else ""
            pdf = " · PDF" if p.pdf_url else ""
            print(f"- [{p.source}{cites}{pdf}] {p.title} ({p.year})")
            print(f"  {p.url}")
        return 0

    if args.command == "cite":
        from .citations import format_reference, in_text
        from .sources import search

        papers = search(args.query, limit=args.limit, strict=not args.loose)
        if not papers:
            print("No papers matched. Try broader words, or add --loose.")
            return 1
        print(f"References ({args.style}):\n")
        for i, p in enumerate(papers, start=1):
            print(format_reference(p, args.style, number=i))
            print(f"    in-text: {in_text(p, args.style, number=i)}\n")
        return 0

    if args.command == "web":
        from .web import serve

        return serve(port=args.port, open_browser=not args.no_browser)

    if args.command == "data":
        if _needs_key():
            return 1
        from .data_extract import comparison_chart, extract_numbers
        from .sources import search

        papers = search(args.query, limit=args.limit)
        if not papers:
            print("No papers found. Try a broader query.")
            return 1
        all_numbers = []
        for p in papers:
            print(f"Reading: {p.title[:70]}")
            rows = extract_numbers(p, focus=args.focus, use_fulltext=not args.no_fulltext)
            all_numbers.extend(rows)
        if not all_numbers:
            print("\nNo clear quantitative results found in these papers.")
            return 0
        print(f"\nExtracted {len(all_numbers)} numbers:\n")
        for r in all_numbers:
            unit = f" {r['unit']}" if r["unit"] else ""
            print(f"  {r['value']}{unit:<8} {r['label']}  [{r['paper'][:40]}]")
            print(f"           from: \"{r['context'][:90]}\"")
        chart = comparison_chart(all_numbers)
        if chart:
            print(f"\nComparison chart saved to: {chart}")
        else:
            print("\nNo unit was shared across two or more papers, so no "
                  "comparison chart this time.")
        return 0

    if args.command == "quotes":
        if _needs_key():
            return 1
        from .passages import extract_passages
        from .sources import search

        papers = search(args.query, limit=args.limit, strict=not args.loose)
        if not papers:
            print("No papers matched. Try broader words, or add --loose.")
            return 1
        for i, p in enumerate(papers, start=1):
            quotes = extract_passages(
                p, focus=args.focus, style=args.style, n=3, number=i,
                use_fulltext=not args.no_fulltext,
            )
            if not quotes:
                continue
            print(f"[{i}] {p.title}")
            for q in quotes:
                print(f'  "{q["quote"]}" {q["in_text"]}')
                if q.get("supports"):
                    print(f"       (supports: {q['supports']})")
            print()
        return 0

    if args.command == "research":
        if _needs_key():
            return 1
        from .pipeline import run

        result = run(
            args.question, limit=args.limit, sources_list=args.source,
            style=args.style, quotes=args.quotes, strict=not args.loose,
        )
        print(f"\nSynthesis:\n{result['synthesis']}\n")
        print(f"Report written to: {result['report']}")
        for fig in result["figures"]:
            print(f"Figure: {fig}")
        return 0

    if args.command == "ask":
        if _needs_key():
            return 1
        from .agent import run

        answer = run(args.question)
        print(f"\n{answer}")
        return 0

    return 1


def _doctor() -> int:
    """Print a setup health check a beginner can act on."""
    print("Checking your setup...\n")
    ok = True

    print(f"[ok] Python {sys.version.split()[0]}")

    for mod, label in [
        ("requests", "paper search"),
        ("feedparser", "arXiv search"),
        ("anthropic", "AI summaries/quotes"),
        ("matplotlib", "charts"),
        ("pypdf", "full-text PDF quotes"),
    ]:
        try:
            __import__(mod)
            print(f"[ok] {mod} installed ({label})")
        except ImportError:
            ok = False
            print(f"[!!] {mod} missing ({label}) - run: pip install -r requirements.txt")

    # Optional: nltk/WordNet widens synonym matching in the relevance filter.
    # Word-forms and common synonyms work without it.
    try:
        __import__("nltk")
        print("[ok] nltk installed (broader synonym matching, optional)")
    except ImportError:
        print("[--] nltk not installed (optional) - basic synonyms still work; "
              "'pip install nltk' widens them")

    if has_api_key():
        print("[ok] Anthropic API key found (AI features enabled)")
    else:
        ok = False
        print("[!!] No Anthropic API key (AI features off)")
        print("     " + API_KEY_HELP.replace("\n", "\n     "))

    # Quick reachability check of the paper databases (each is optional; a
    # source being down is a warning, not a failure of your setup).
    print()
    from .sources import search

    try:
        hits = search("test", limit=1)
        if hits:
            print(f"[ok] Paper databases reachable ({hits[0].source} responded)")
        else:
            print("[..] Paper databases returned nothing for a test query "
                  "(they may be briefly down; try again later)")
    except Exception as exc:
        print(f"[..] Couldn't reach the paper databases right now: {exc}")

    print("\nAll set!" if ok else "\nFix the [!!] items above, then run this again.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
