# STEM Research Agent

A free tool for lab reports and essays. Give it a topic and it finds real
papers across four scholarly databases and formats the citations in whatever
style your class uses. No API key, no account, no cost.

Built to speed up the annoying part of research: finding sources and getting
the citations right.

## What it does

- **Finds papers** across four free databases: OpenAlex (all fields), arXiv (physics / CS / math), PubMed (medicine / life sciences), and CrossRef (broad, with citation counts). Results are merged and de-duplicated.
- **Filters for real relevance**: a paper is kept only if your search words actually appear in its title, counting word-forms (kick / kicks / kicking) and synonyms (football / soccer). Add `--loose` to widen the net.
- **Cites in your style** — Harvard, APA, MLA, Chicago, IEEE, or Vancouver. Full reference-list entries and ready-to-paste in-text citations.
- **Runs anywhere** — a guided terminal mode, direct commands, or a local web page. Nothing leaves your computer.

## First time? Start here

```bash
# 1. Install (three small packages, no build tools)
pip install -r requirements.txt

# 2. Check it works
python main.py doctor
```

That's the whole setup. There's no key to get.

Then pick how you like to use it:

```bash
python main.py web     # a local web page: type a topic, click Find papers
python main.py         # guided question-by-question mode in the terminal
```

## Commands

```bash
# Search papers
python main.py search "caffeine reaction time" -n 8

# Search + format references in a style
python main.py cite "caffeine reaction time" --style apa

# See what each referencing style is for
python main.py styles

# Check your setup
python main.py doctor
```

Tip: keyword searches ("caffeine reaction time") work better than full
questions, because the filter matches your words against paper titles. If you
get "No papers matched," shorten to keywords or add `--loose`.

### Referencing styles

Pick with `--style` on `cite`. Set a default with the `CITATION_STYLE` env var.

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
  sources.py     retrieval (OpenAlex, arXiv, PubMed, CrossRef) -> Paper objects
  cache.py       day-long cache of search results (.cache/)
  relevance.py   keep only papers whose title matches the query (+ synonyms)
  citations.py   format references + in-text cites in 6 styles
  wizard.py      guided beginner mode (runs when you pass no command)
  web.py + web/  local web interface (stdlib only, no Node needed)
  cli.py         command-line interface
```

Search results are cached in `.cache/` for a day, so repeat runs are instant.

## A note on citations

The tool only ever cites papers it actually found, with real bibliographic
data from the databases. It's a research aid, not a replacement for reading the
papers. Always check the originals before you cite them.
