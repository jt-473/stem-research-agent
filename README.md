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
- **Cites in your style** — Harvard, APA, MLA, Chicago, IEEE, or Vancouver. Full reference-list entries and in-text citations. Run `styles` to see what each one is for.
- **Quotes specific passages** verbatim from a paper with a ready in-text citation, so you can drop a quote straight into an essay.
- **Charts data** with matplotlib, either from numbers you provide or citation counts across a search.
- **Writes a Markdown brief** with the synthesis, figures, quotes, and a full source list in your chosen style.
- **Runs as an agent** (`ask`) where Claude drives the tools itself, or as a fixed pipeline (`research`) that does the same steps every time.

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
# Full research brief in a chosen style, with quotable passages
python main.py research "does caffeine improve reaction time" --style harvard --quotes

# Let the agent decide its own steps (tool-calling loop)
python main.py ask "compare lithium-ion and solid-state battery energy density in IEEE style"

# Just search, no LLM calls (free, fast sanity check)
python main.py search "CRISPR off-target effects" -n 8

# Format references for a search in any style (no LLM calls)
python main.py cite "CRISPR off-target effects" --style apa

# Pull verbatim quotes with in-text citations, ready to paste
python main.py quotes "CRISPR off-target effects" --style mla --focus "detection methods"

# See what each referencing style is for
python main.py styles
```

Briefs and figures land in `outputs/`.

### Referencing styles

Pick with `--style` on `research`, `cite`, and `quotes`. Set a default with the
`CITATION_STYLE` env var.

| Style | Used in | In-text example |
|-------|---------|-----------------|
| `harvard` | UK unis, sciences/social sciences | (Smith et al., 2021, p. 4) |
| `apa` | psychology, education, sciences | (Smith et al., 2021, p. 4) |
| `mla` | English, humanities | (Smith et al. 4) |
| `chicago` | sciences, social sciences | (Smith et al. 2021, 4) |
| `ieee` | engineering, computer science | [1, p. 4] |
| `vancouver` | medicine, life sciences | (1) |

Names, page ranges, and venues come from the source databases and aren't always
perfectly clean, so eyeball citations before you hand work in.

## How it's built

```
src/agent/
  sources.py     paper retrieval (OpenAlex, arXiv) -> normalized Paper objects
  summarize.py   Claude: per-paper summaries + cross-paper synthesis
  citations.py   format references + in-text cites in 6 styles
  passages.py    Claude: pull verbatim quotable passages with citations
  charts.py      matplotlib chart generation
  report.py      assemble everything into a Markdown brief
  pipeline.py    the reliable straight-line flow
  agent.py       agentic tool-calling loop (Claude drives; search/cite/quote/chart tools)
  cli.py         command-line interface
```

Two ways to run the work:
- **`pipeline.py`** runs the same fixed steps every time. Predictable and cheap.
- **`agent.py`** hands Claude the tools and lets it choose what to do. Better for open-ended questions.

## Roadmap

- [x] Multiple referencing styles (Harvard, APA, MLA, Chicago, IEEE, Vancouver)
- [x] Quote specific passages with ready-to-paste citations
- [ ] Full-text PDF parsing so quotes get real page/section locators (currently abstract-only)
- [ ] Pull quantitative data straight out of papers for charting
- [ ] PubMed and CrossRef sources
- [ ] Result caching to cut repeat API cost
- [ ] Web frontend (Next.js)

## Note on citations

The agent only cites papers it actually retrieved, and ties every claim
to a real source from the API. It's a research aid, not a replacement for
reading the papers. Always check the originals before you cite them.
