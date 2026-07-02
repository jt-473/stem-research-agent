"""Agentic loop: give Claude the tools and let it drive the research.

This is the "Phase 3" upgrade over the straight-line pipeline. The model
decides when to search, when to make a chart, and when it has enough to
answer. Good for open-ended questions where the right next step isn't
known up front.
"""

from __future__ import annotations

import json

from anthropic import Anthropic

from . import charts, sources
from .config import MODEL

client = Anthropic()

TOOLS = [
    {
        "name": "search_papers",
        "description": "Search scholarly databases (OpenAlex, arXiv) for papers "
        "on a topic. Returns titles, abstracts, authors, and citation counts.",
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

SYSTEM = """You are a STEM research agent for a student. Use the tools to find \
real papers and build charts. Rules you must follow:
- Only cite papers actually returned by search_papers. Never invent sources.
- When you state a finding, attribute it to a specific paper.
- Prefer recent, highly-cited work when relevant.
When you have enough to answer, give a clear synthesis with inline citations."""


def _run_tool(name: str, args: dict) -> str:
    """Execute a tool call and return a string result for the model."""
    if name == "search_papers":
        papers = sources.search(args["query"], limit=args.get("limit", 5))
        return json.dumps([p.to_dict() for p in papers])[:12000]
    if name == "make_chart":
        path = charts.chart_from_data(
            x=args["x"],
            y=args["y"],
            kind=args.get("kind", "bar"),
            title=args.get("title", ""),
            xlabel=args.get("xlabel", ""),
            ylabel=args.get("ylabel", ""),
        )
        return f"Chart saved to {path}"
    return f"Unknown tool: {name}"


def run(question: str, max_turns: int = 8) -> str:
    """Let Claude research the question with tools. Returns final answer text."""
    messages = [{"role": "user", "content": question}]

    for turn in range(max_turns):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            # Model is done: return its text.
            return "".join(b.text for b in resp.content if b.type == "text")

        # Run every tool the model asked for and feed results back.
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"      [tool] {block.name}({json.dumps(block.input)[:80]}...)")
                result = _run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return "Stopped: hit the turn limit before finishing."
