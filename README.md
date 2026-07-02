# STEM Research Agent

An AI agent that helps with lab reports and essays. Give it a research
question and it pulls real papers from scholarly databases, summarizes
them with Claude, writes a cited synthesis, and generates charts you can
drop into your work.

Built to speed up the annoying part of research: finding sources, reading
abstracts, and turning data into figures.

## What it does

- **Pulls papers** from OpenAlex (all fields) and arXiv (physics / CS / math). Both free, no key needed.
- **Summarizes** each paper into main finding, method, and key numbers.
- **Synthesizes** an answer to your question with inline citations, and never invents a source.
- **Charts data** with matplotlib, either from numbers you provide or citation counts across a search.
- **Writes a Markdown brief** with the synthesis, figures, and a full source list.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
# then edit .env and paste your key
```

Get an API key at [console.anthropic.com](https://console.anthropic.com/).

## Usage

```bash
# Full research brief (search + summarize + synthesize + charts)
python main.py research "does caffeine improve reaction time"

# Let the agent decide its own steps (tool-calling loop)
python main.py ask "compare lithium-ion and solid-state battery energy density"

# Just search, no LLM calls (free, fast sanity check)
python main.py search "CRISPR off-target effects" -n 8
```

Briefs and figures land in `outputs/`.

## How it's built

```
src/agent/
  sources.py     paper retrieval (OpenAlex, arXiv) -> normalized Paper objects
  summarize.py   Claude: per-paper summaries + cross-paper synthesis
  charts.py      matplotlib chart generation
  report.py      assemble everything into a Markdown brief
  pipeline.py    the reliable straight-line flow
  agent.py       agentic tool-calling loop (Claude drives)
  cli.py         command-line interface
```

Two ways to run the work:
- **`pipeline.py`** runs the same fixed steps every time. Predictable and cheap.
- **`agent.py`** hands Claude the tools and lets it choose what to do. Better for open-ended questions.

## Roadmap

- [ ] Full-text PDF parsing (currently abstract-only)
- [ ] Pull quantitative data straight out of papers for charting
- [ ] PubMed and CrossRef sources
- [ ] Result caching to cut repeat API cost
- [ ] Web frontend (Next.js)

## Note on citations

The agent only cites papers it actually retrieved, and ties every claim
to a real source from the API. It's a research aid, not a replacement for
reading the papers. Always check the originals before you cite them.
