"""Paper and article retrieval from free scholarly APIs.

Currently supports OpenAlex (broad coverage, all fields) and arXiv
(physics / CS / math preprints). Both are free and need no API key.

Every source returns a normalized list of ``Paper`` dicts so the rest
of the agent doesn't care where a result came from.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

import requests

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_URL = "http://export.arxiv.org/api/query"

# OpenAlex asks that you identify yourself in the User-Agent so they can
# route you to their faster "polite pool". Swap in your own email.
CONTACT_EMAIL = "jovantomy@icloud.com"
HEADERS = {"User-Agent": f"stem-research-agent (mailto:{CONTACT_EMAIL})"}


@dataclass
class Paper:
    """A single paper, normalized across every source."""

    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    url: str = ""
    doi: str = ""
    citations: int | None = None
    source: str = ""
    # Bibliographic fields needed by citation styles (best-effort per source).
    venue: str = ""  # journal / conference / "arXiv preprint"
    volume: str = ""
    issue: str = ""
    pages: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def citation_line(self) -> str:
        """A plain reference string you can drop into a report."""
        who = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            who += ", et al."
        year = f"({self.year})" if self.year else ""
        bits = [b for b in (who, year, self.title, self.doi or self.url) if b]
        return ". ".join(bits)


def _rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex ships abstracts as an inverted index. Put it back together."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, spots in inverted_index.items():
        for spot in spots:
            positions.append((spot, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def search_openalex(query: str, limit: int = 5) -> list[Paper]:
    """Search OpenAlex. Returns up to ``limit`` papers, most relevant first."""
    params = {
        "search": query,
        "per_page": limit,
        "sort": "relevance_score:desc",
    }
    resp = requests.get(OPENALEX_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results", [])

    papers: list[Paper] = []
    for item in results:
        authors = [
            a["author"]["display_name"]
            for a in item.get("authorships", [])
            if a.get("author")
        ]
        biblio = item.get("biblio") or {}
        first, last = biblio.get("first_page"), biblio.get("last_page")
        pages = f"{first}-{last}" if first and last else (first or "")
        location = item.get("primary_location") or {}
        venue = (location.get("source") or {}).get("display_name", "")

        papers.append(
            Paper(
                title=item.get("title") or "(untitled)",
                abstract=_rebuild_abstract(item.get("abstract_inverted_index")),
                authors=authors,
                year=item.get("publication_year"),
                url=item.get("id", ""),
                doi=(item.get("doi") or "").replace("https://doi.org/", ""),
                citations=item.get("cited_by_count"),
                source="OpenAlex",
                venue=venue or "",
                volume=biblio.get("volume") or "",
                issue=biblio.get("issue") or "",
                pages=pages or "",
            )
        )
    return papers


def search_arxiv(query: str, limit: int = 5) -> list[Paper]:
    """Search arXiv preprints. Returns up to ``limit`` papers."""
    # feedparser is optional; import lazily so OpenAlex-only use still works.
    import feedparser

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
    }
    resp = requests.get(ARXIV_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)

    papers: list[Paper] = []
    for entry in feed.entries:
        year = None
        if getattr(entry, "published_parsed", None):
            year = entry.published_parsed.tm_year
        # arXiv id like "2401.01234" pulled from the entry URL for the venue line.
        arxiv_id = entry.get("id", "").rsplit("/abs/", 1)[-1]
        venue = f"arXiv preprint arXiv:{arxiv_id}" if arxiv_id else "arXiv preprint"
        papers.append(
            Paper(
                title=entry.get("title", "(untitled)").replace("\n", " ").strip(),
                abstract=entry.get("summary", "").replace("\n", " ").strip(),
                authors=[a.name for a in entry.get("authors", [])],
                year=year,
                url=entry.get("link", ""),
                doi=entry.get("arxiv_doi", ""),
                citations=None,  # arXiv doesn't report citation counts
                source="arXiv",
                venue=venue,
            )
        )
    return papers


def search(query: str, limit: int = 5, sources: list[str] | None = None) -> list[Paper]:
    """Search every requested source and merge the results.

    ``sources`` defaults to both OpenAlex and arXiv. Failures in one
    source are swallowed so a single API hiccup doesn't kill the run.
    """
    sources = sources or ["openalex", "arxiv"]
    runners = {"openalex": search_openalex, "arxiv": search_arxiv}

    merged: list[Paper] = []
    for name in sources:
        runner = runners.get(name)
        if not runner:
            continue
        try:
            merged.extend(runner(query, limit=limit))
        except Exception as exc:  # keep going if one source is down
            print(f"[warn] {name} search failed: {exc}")
        time.sleep(0.34)  # be gentle with the free APIs
    return merged
