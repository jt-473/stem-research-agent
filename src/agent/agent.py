"""Agentic loop: give Claude the tools and let it drive the research.

This is the "Phase 3" upgrade over the straight-line pipeline. The model
decides when to search, when to cite, when to quote, and when to make a
chart. Papers found during a run are kept in a store keyed by id, so the
citation and quote tools always work off the real retrieved paper rather
than anything the model might re-type. That keeps citations honest.
"""

from __future__ import annotations

import json

from . import charts, citations, config, llm, passages, sources
from .config import DEFAULT_STYLE, MODEL

TOOLS = [
    {
        "name": "search_papers",
        "description": "Search scholarly databases (OpenAlex, arXiv) for papers "
        "on a topic. Returns papers each with an 'id' you pass to other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "format_citation",
        "description": "Format a found paper as a reference-list entry and an "
        "in-text citation in a chosen referencing style. Use the paper 'id' "
        "from search_papers so the citation uses real bibliographic data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "id from search_papers"},
                "style": {
                    "type": "string",
                    "enum": list(citations.STYLES.keys()),
                    "description": "Referencing style",
                },
                "locator": {
                    "type": "string",
                    "description": "Optional page/section for the in-text cite, "
                    "e.g. 'p. 4' or 'abstract'",
                },
            },
            "required": ["paper_id", "style"],
        },
    },
    {
        "name": "quote_passages",
        "description": "Pull verbatim quotable passages from a found paper, each "
        "with a ready in-text citation in the chosen style. Use for essays where "
        "the student needs to quote a specific part.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "id from search_papers"},
                "focus": {"type": "string", "description": "What the quote should be about"},
                "style": {"type": "string", "enum": list(citations.STYLES.keys())},
                "n": {"type": "integer", "default": 3},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "extract_data",
        "description": "Pull the quantitative results out of a found paper "
        "(reads the full PDF when open-access). Returns numbers with label, "
        "value, unit, and the exact sentence each came from. Use before "
        "make_chart when comparing results across papers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "id from search_papers"},
                "focus": {"type": "string", "description": "What kind of numbers to look for"},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "make_chart",
        "description": "Render a chart (bar, line, or scatter) from paired x/y "
        "data and save it as a PNG. Use for visualizing data the user provides "
        "or numbers pulled from papers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "array", "items": {}, "description": "X values"},
                "y": {"type": "array", "items": {"type": "number"}, "description": "Y values"},
                "kind": {"type": "string", "enum": ["bar", "line", "scatter"]},
                "title": {"type": "string"},
                "xlabel": {"type": "string"},
                "ylabel": {"type": "string"},
            },
            "required": ["x", "y"],
        },
    },
]

_STYLE_HELP = "\n".join(f"  {k}: {v}" for k, v in citations.STYLES.items())

SYSTEM = f"""You are a STEM research agent for a student writing lab reports \
and essays. Use the tools to find real papers, cite them, quote them, and chart \
data. Rules you must follow:
- Only cite or quote papers actually returned by search_papers. Never invent a \
source, a quote, a page number, or a statistic.
- When you state a finding, attribute it to a specific paper.
- Use format_citation and quote_passages (via the paper's id) instead of \
writing citations by hand, so the bibliographic details stay accurate.
- If the user names a referencing style, use it. If not, ask or default to \
{DEFAULT_STYLE}.

Referencing styles you can produce:
{_STYLE_HELP}

When you have enough to answer, give a clear synthesis with inline citations \
and, if asked, a reference list in the chosen style."""


class _Session:
    """Holds papers found during one run so tools can look them up by id."""

    def __init__(self) -> None:
        self.papers: dict[str, sources.Paper] = {}
        self._n = 0

    def add(self, paper: sources.Paper) -> str:
        self._n += 1
        pid = f"p{self._n}"
        self.papers[pid] = paper
        return pid

    def run_tool(self, name: str, args: dict) -> str:
        if name == "search_papers":
            found = sources.search(args["query"], limit=args.get("limit", 5))
            out = []
            for p in found:
                pid = self.add(p)
                row = p.to_dict()
                row["id"] = pid
                out.append(row)
            return json.dumps(out)[:12000]

        if name == "format_citation":
            paper = self.papers.get(args["paper_id"])
            if not paper:
                return f"No paper with id {args['paper_id']}. Search first."
            style = args.get("style", DEFAULT_STYLE)
            number = int(args["paper_id"].lstrip("p") or 0)
            return json.dumps(
                {
                    "reference": citations.format_reference(paper, style, number=number),
                    "in_text": citations.in_text(
                        paper, style, locator=args.get("locator"), number=number
                    ),
                }
            )

        if name == "quote_passages":
            paper = self.papers.get(args["paper_id"])
            if not paper:
                return f"No paper with id {args['paper_id']}. Search first."
            number = int(args["paper_id"].lstrip("p") or 0)
            quotes = passages.extract_passages(
                paper,
                focus=args.get("focus", ""),
                style=args.get("style", DEFAULT_STYLE),
                n=args.get("n", 3),
                number=number,
            )
            return json.dumps(quotes)

        if name == "extract_data":
            paper = self.papers.get(args["paper_id"])
            if not paper:
                return f"No paper with id {args['paper_id']}. Search first."
            from .data_extract import extract_numbers

            numbers = extract_numbers(paper, focus=args.get("focus", ""))
            return json.dumps(numbers)[:12000]

        if name == "make_chart":
            try:
                path = charts.chart_from_data(
                    x=args["x"],
                    y=args["y"],
                    kind=args.get("kind", "bar"),
                    title=args.get("title", ""),
                    xlabel=args.get("xlabel", ""),
                    ylabel=args.get("ylabel", ""),
                )
            except ValueError as exc:
                return f"Chart error: {exc}"
            return f"Chart saved to {path}"

        return f"Unknown tool: {name}"


def run(question: str, max_turns: int = 10) -> str:
    """Let Claude research the question with tools. Returns final answer text.

    The agentic loop uses Claude's tool-calling API. On other providers,
    point people at the pipeline commands (research/quotes/data), which are
    provider-agnostic and cover the same ground.
    """
    if config.PROVIDER != "anthropic":
        raise SystemExit(
            f"The 'ask' agent mode currently needs Claude (PROVIDER=anthropic), "
            f"but PROVIDER is set to {config.PROVIDER!r}.\n"
            "Use 'research', 'quotes', or 'data' instead — those work on "
            "Gemini and cover the same features."
        )

    session = _Session()
    messages = [{"role": "user", "content": question}]

    for _ in range(max_turns):
        resp = llm.anthropic_client().messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"      [tool] {block.name}({json.dumps(block.input)[:80]}...)")
                result = session.run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return "Stopped: hit the turn limit before finishing."
