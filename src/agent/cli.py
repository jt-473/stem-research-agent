"""Command-line interface for the STEM research agent."""

from __future__ import annotations

import argparse
import sys

from .citations import STYLES
from .config import DEFAULT_STYLE

STYLE_CHOICES = list(STYLES.keys())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stem-research-agent",
        description="Pull papers, summarize them, cite them, and chart data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # research: straight-line pipeline -> Markdown brief
    p_research = sub.add_parser("research", help="Search + summarize + write a brief")
    p_research.add_argument("question", help="Your research question")
    p_research.add_argument("-n", "--limit", type=int, default=5, help="Papers per source")
    p_research.add_argument(
        "--source", action="append", choices=["openalex", "arxiv"],
        help="Restrict to a source (repeatable). Default: both.",
    )
    p_research.add_argument(
        "--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE,
        help=f"Referencing style (default: {DEFAULT_STYLE})",
    )
    p_research.add_argument(
        "--quotes", action="store_true",
        help="Also pull quotable passages with in-text citations",
    )

    # ask: agentic loop, Claude drives the tools
    p_ask = sub.add_parser("ask", help="Let the agent decide how to answer")
    p_ask.add_argument("question", help="Your research question")

    # search: quick source check, no LLM calls
    p_search = sub.add_parser("search", help="Raw paper search, no summaries")
    p_search.add_argument("query")
    p_search.add_argument("-n", "--limit", type=int, default=5)

    # cite: format references for a search in a chosen style
    p_cite = sub.add_parser("cite", help="Format references for a search in a style")
    p_cite.add_argument("query")
    p_cite.add_argument("-n", "--limit", type=int, default=5)
    p_cite.add_argument("--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE)

    # quotes: pull quotable passages with citations
    p_quotes = sub.add_parser("quotes", help="Pull quotable passages with citations")
    p_quotes.add_argument("query")
    p_quotes.add_argument("-n", "--limit", type=int, default=3)
    p_quotes.add_argument("--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE)
    p_quotes.add_argument("--focus", default="", help="Narrow quotes to a topic")

    # styles: explain each referencing style
    sub.add_parser("styles", help="List and explain the referencing styles")

    args = parser.parse_args(argv)

    if args.command == "styles":
        from .citations import list_styles

        print("Supported referencing styles:\n")
        print(list_styles())
        return 0

    if args.command == "search":
        from .sources import search

        for p in search(args.query, limit=args.limit):
            cites = f" · {p.citations} cites" if p.citations is not None else ""
            print(f"- [{p.source}{cites}] {p.title} ({p.year})")
            print(f"  {p.url}")
        return 0

    if args.command == "cite":
        from .citations import format_reference, in_text
        from .sources import search

        papers = search(args.query, limit=args.limit)
        print(f"References ({args.style}):\n")
        for i, p in enumerate(papers, start=1):
            print(format_reference(p, args.style, number=i))
            print(f"    in-text: {in_text(p, args.style, number=i)}\n")
        return 0

    if args.command == "quotes":
        from .passages import extract_passages
        from .sources import search

        papers = search(args.query, limit=args.limit)
        for i, p in enumerate(papers, start=1):
            quotes = extract_passages(
                p, focus=args.focus, style=args.style, n=3, number=i
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
        from .pipeline import run

        result = run(
            args.question, limit=args.limit, sources_list=args.source,
            style=args.style, quotes=args.quotes,
        )
        print(f"\nSynthesis:\n{result['synthesis']}\n")
        print(f"Report written to: {result['report']}")
        for fig in result["figures"]:
            print(f"Figure: {fig}")
        return 0

    if args.command == "ask":
        from .agent import run

        answer = run(args.question)
        print(f"\n{answer}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
