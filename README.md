# STEM Research Agent

An AI agent that helps with lab reports and essays. Give it a research
question and it pulls real papers from scholarly databases, summarizes
them, writes a cited synthesis, and generates charts you can drop into
your work. Runs on either Google Gemini (free tier) or Claude.

Built to speed up the annoying part of research: finding sources, reading
abstracts, and turning data into figures.

## What it does

- **Pulls papers** from four free databases, no key needed: OpenAlex (all fields), arXiv (physics / CS / math), PubMed (medicine / life sciences), and CrossRef (broad published work, with citation counts). Results are merged and de-duplicated.
- **Filters for real relevance**: a paper is kept only if your search words actually appear in its title, counting word-forms (kick / kicks / kicking) and synonyms (football / soccer). No more loosely-related results. Add `--loose` to turn it off.
- **Summarizes** each paper into main finding, method, and key numbers.
- **Synthesizes** an answer to your question with inline citations, and never invents a source.
- **Cites in your style** — Harvard, APA, MLA, Chicago, IEEE, or Vancouver. Full reference-list entries and in-text citations. Run `styles` to see what each one is for.
- **Quotes specific passages** verbatim from a paper with a ready in-text citation. For open-access papers it reads the full PDF and gives a real page number, so you can drop a quote straight into an essay.
- **Charts data** with matplotlib, either from numbers you provide or citation counts across a search.
- **Writes a Markdown brief** with the synthesis, figures, quotes, and a full source list in your chosen style.
- **Free or paid AI** — runs on Google Gemini (free tier) or Claude, set by one line in `.env`.
- **Runs as an agent** (`ask`) where the model drives the tools itself, or as a fixed pipeline (`research`) that does the same steps every time.

## First time? Start here

Three steps and you're running:

```bash
# 1. Install everything
pip install -r requirements.txt

# 2. Add an API key (needed for the AI parts). Two options:
cp .env.example .env          # then open .env and paste a key

#    Free:  set PROVIDER=gemini and paste a Google Gemini key
#           (get one free at https://aistudio.google.com/apikey)
#    Paid:  set PROVIDER=anthropic and paste a Claude key
#           (https://console.anthropic.com/)

# 3. Check it all worked
python main.py doctor
```

`doctor` tells you exactly what's set up and what isn't, in plain English,
including which provider and model you're on.

### Free or paid? (choosing a provider)

The AI features (summaries, quotes, data extraction) run through one provider,
set by `PROVIDER` in `.env`:

- **`gemini`** — Google Gemini, has a genuinely free tier. Great for students.
- **`anthropic`** — Claude, paid but a few cents per run. Also unlocks the
  `ask` agent mode.

Switch anytime by changing that one line. Everything else works the same. The
`search`, `cite`, and `styles` commands need no key or provider at all.

Then pick whichever way of using it you like:

```bash
python main.py web        # a local web page: type your question, click Research
python main.py            # guided question-by-question mode in the terminal
```

The web page is the easiest way in. It has a search box, a citation style
picker, and shows the answer, quotes, citations, and charts on one page.
Nothing to install beyond step 1, and it never leaves your computer.

Prefer typing commands directly? Those are below.

## Commands

```bash
# Full research brief in a chosen style, with quotable passages
python main.py research "does caffeine improve reaction time" --style harvard --quotes

# Let the agent decide its own steps (tool-calling loop; needs PROVIDER=anthropic)
python main.py ask "compare lithium-ion and solid-state battery energy density in IEEE style"

# Just search, no LLM calls (free, fast sanity check)
python main.py search "CRISPR off-target effects" -n 8

# Restrict to specific databases (repeatable; default is openalex+arxiv+pubmed)
python main.py research "gene therapy safety" --source pubmed --source crossref

# Format references for a search in any style (no LLM calls)
python main.py cite "CRISPR off-target effects" --style apa

# Pull verbatim quotes with in-text citations, ready to paste
# (reads the full PDF for real page numbers when the paper is open-access)
python main.py quotes "CRISPR off-target effects" --style mla --focus "detection methods"

# Extract the numbers from papers and chart them across studies
python main.py data "caffeine reaction time improvement" --focus "reaction time"

# See what each referencing style is for
python main.py styles

# Check your setup
python main.py doctor
```

Briefs and figures land in `outputs/`. Search results are cached in
`.cache/` for a day, so repeat runs are instant and don't re-hit the APIs.

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
  sources.py       retrieval (OpenAlex, arXiv, PubMed, CrossRef) -> Paper objects
  relevance.py     keep only papers whose title matches the query (+ synonyms)
  llm.py           one text-generation interface over Claude and Gemini
  cache.py         day-long cache of search results (.cache/)
  fulltext.py      download an open-access PDF, read it, locate a quote's page
  summarize.py     Claude: per-paper summaries + cross-paper synthesis
  citations.py     format references + in-text cites in 6 styles
  passages.py      Claude: pull verbatim quotable passages with page citations
  data_extract.py  Claude: pull quantitative results, chart them across studies
  charts.py        matplotlib chart generation
  report.py        assemble everything into a Markdown brief
  pipeline.py      the reliable straight-line flow
  agent.py         agentic loop (Claude drives; search/cite/quote/data/chart tools)
  wizard.py        guided beginner mode (runs when you pass no command)
  web.py + web/    local web interface (stdlib only, no Node needed)
  cli.py           command-line interface
```

Two ways to run the work:
- **`pipeline.py`** runs the same fixed steps every time. Predictable and cheap.
- **`agent.py`** hands Claude the tools and lets it choose what to do. Better for open-ended questions.

## Roadmap

- [x] Multiple referencing styles (Harvard, APA, MLA, Chicago, IEEE, Vancouver)
- [x] Quote specific passages with ready-to-paste citations
- [x] Full-text PDF parsing so quotes get real page numbers (open-access papers)
- [x] Guided beginner mode + `doctor` setup check
- [x] Pull quantitative data straight out of papers for charting (`data` command)
- [x] Result caching to cut repeat API cost
- [x] Local web interface (`web` command)
- [x] PubMed and CrossRef sources

## Note on citations

The agent only cites papers it actually retrieved, and ties every claim
to a real source from the API. It's a research aid, not a replacement for
reading the papers. Always check the originals before you cite them.
