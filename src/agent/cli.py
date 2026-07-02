"""Command-line interface for the STEM research agent."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stem-research-agent",
        description="Pull papers, summarize them, and chart data for reports.",
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

    # ask: agentic loop, Claude drives the tools
    p_ask = sub.add_parser("ask", help="Let the agent decide how to answer")
    p_ask.add_argument("question", help="Your research question")

    # search: quick source check, no LLM calls
    p_search = sub.add_parser("search", help="Raw paper search, no summaries")
    p_search.add_argument("query")
    p_search.add_argument("-n", "--limit", type=int, default=5)

    args = parser.parse_args(argv)

    if args.command == "search":
        from .sources import search

        for p in search(args.query, limit=args.limit):
            cites = f" · {p.citations} cites" if p.citations is not None else ""
            print(f"- [{p.source}{cites}] {p.title} ({p.year})")
            print(f"  {p.url}")
        return 0

    if args.command == "research":
        from .pipeline import run

        result = run(args.question, limit=args.limit, sources_list=args.source)
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
