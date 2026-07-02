"""Command-line interface for the STEM research agent.

Free and offline-friendly: it finds real papers and formats citations, with
no API key and no cost. Run with no command for a guided mode.
"""

from __future__ import annotations

import argparse
import sys

from .citations import STYLES
from .config import DEFAULT_STYLE

STYLE_CHOICES = list(STYLES.keys())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stem-research-agent",
        description="Find papers and format citations. Free, no key needed. "
        "Run with no command for a guided mode.",
    )
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search papers across databases")
    p_search.add_argument("query")
    p_search.add_argument("-n", "--limit", type=int, default=5)
    p_search.add_argument(
        "--loose", action="store_true",
        help="Don't require the query words to appear in each paper's title",
    )

    p_cite = sub.add_parser("cite", help="Search + format references in a style")
    p_cite.add_argument("query")
    p_cite.add_argument("-n", "--limit", type=int, default=5)
    p_cite.add_argument("--style", choices=STYLE_CHOICES, default=DEFAULT_STYLE)
    p_cite.add_argument("--loose", action="store_true", help="Skip the title-match filter")

    p_web = sub.add_parser("web", help="Open the local web interface")
    p_web.add_argument("--port", type=int, default=8765)
    p_web.add_argument("--no-browser", action="store_true", help="Don't auto-open a browser")

    sub.add_parser("styles", help="List and explain the referencing styles")
    sub.add_parser("doctor", help="Check your setup")
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
            print(f"- [{p.source}{cites}] {p.title} ({p.year})")
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

    return 1


def _doctor() -> int:
    """Print a setup health check a beginner can act on."""
    print("Checking your setup...\n")
    ok = True

    print(f"[ok] Python {sys.version.split()[0]}")

    for mod, label in [
        ("requests", "paper search"),
        ("feedparser", "arXiv search"),
    ]:
        try:
            __import__(mod)
            print(f"[ok] {mod} installed ({label})")
        except ImportError:
            ok = False
            print(f"[!!] {mod} missing ({label}) - run: pip install -r requirements.txt")

    # Optional: nltk/WordNet widens synonym matching in the relevance filter.
    try:
        __import__("nltk")
        print("[ok] nltk installed (broader synonym matching, optional)")
    except ImportError:
        print("[--] nltk not installed (optional) - basic synonyms still work; "
              "'pip install nltk' widens them")

    # Quick reachability check of the paper databases.
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
