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
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CROSSREF_URL = "https://api.crossref.org/works"

# Which sources a plain search() hits. All four by default for the widest
# coverage of papers.
DEFAULT_SOURCES = ["openalex", "arxiv", "pubmed", "crossref"]

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
    pdf_url: str = ""  # open-access PDF, when one is available

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
        # Prefer an open-access PDF if OpenAlex knows one.
        best_oa = item.get("best_oa_location") or {}
        pdf_url = (
            best_oa.get("pdf_url")
            or (item.get("open_access") or {}).get("oa_url")
            or location.get("pdf_url")
            or ""
        )

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
                pdf_url=pdf_url,
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
        # arXiv abstract links map directly to the PDF.
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""
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
                pdf_url=pdf_url,
            )
        )
    return papers


def search_pubmed(query: str, limit: int = 5) -> list[Paper]:
    """Search PubMed (medicine / life sciences) via NCBI E-utilities.

    Two steps: esearch finds article ids, efetch pulls the records as XML.
    Free, no key needed, but NCBI asks for max ~3 requests/second.
    """
    import xml.etree.ElementTree as ET

    resp = requests.get(
        PUBMED_ESEARCH_URL,
        params={
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "sort": "relevance",
            "retmode": "json",
        },
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    time.sleep(0.34)  # NCBI rate courtesy between the two calls
    resp = requests.get(
        PUBMED_EFETCH_URL,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    papers: list[Paper] = []
    for art in root.iterfind(".//PubmedArticle"):
        pmid = art.findtext(".//PMID", "")
        # itertext() so inline markup inside titles (<i>, <sup>) doesn't
        # truncate the text.
        title_node = art.find(".//ArticleTitle")
        title = "".join(title_node.itertext()) if title_node is not None else ""
        title = title or "(untitled)"
        # Abstracts can be split into labelled sections; join them all.
        abstract = " ".join(
            " ".join(node.itertext()).strip()
            for node in art.iterfind(".//Abstract/AbstractText")
        ).strip()
        authors = []
        for a in art.iterfind(".//AuthorList/Author"):
            fore, last = a.findtext("ForeName", ""), a.findtext("LastName", "")
            name = f"{fore} {last}".strip()
            if name:
                authors.append(name)
        year_text = art.findtext(".//JournalIssue/PubDate/Year") or (
            (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
        )
        year = int(year_text) if year_text.isdigit() else None
        doi = ""
        for eid in art.iterfind(".//ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                doi = eid.text.strip()
        papers.append(
            Paper(
                title=title.strip(),
                abstract=abstract,
                authors=authors,
                year=year,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                doi=doi,
                citations=None,  # PubMed doesn't report citation counts
                source="PubMed",
                venue=art.findtext(".//Journal/Title", "") or "",
                volume=art.findtext(".//JournalIssue/Volume", "") or "",
                issue=art.findtext(".//JournalIssue/Issue", "") or "",
                pages=art.findtext(".//Pagination/MedlinePgn", "") or "",
            )
        )
    return papers


def _strip_jats(text: str) -> str:
    """CrossRef abstracts arrive as JATS XML; strip the tags."""
    import re

    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def search_crossref(query: str, limit: int = 5) -> list[Paper]:
    """Search CrossRef: broad coverage of published work, with citation counts.

    Records often lack abstracts (publishers don't always deposit them),
    which is why this source is opt-in rather than a default.
    """
    resp = requests.get(
        CROSSREF_URL,
        params={"query": query, "rows": limit},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])

    papers: list[Paper] = []
    for item in items:
        titles = item.get("title") or []
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
            if a.get("family") or a.get("given")
        ]
        date_parts = (item.get("issued") or {}).get("date-parts") or [[None]]
        year = date_parts[0][0] if date_parts[0] else None
        containers = item.get("container-title") or []
        # Grab a PDF link when the publisher exposes one.
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf" and link.get("URL"):
                pdf_url = link["URL"]
                break
        papers.append(
            Paper(
                title=(titles[0] if titles else "(untitled)").strip(),
                abstract=_strip_jats(item.get("abstract", "")),
                authors=authors,
                year=year if isinstance(year, int) else None,
                url=item.get("URL", ""),
                doi=item.get("DOI", ""),
                citations=item.get("is-referenced-by-count"),
                source="CrossRef",
                venue=containers[0] if containers else "",
                volume=item.get("volume", "") or "",
                issue=item.get("issue", "") or "",
                pages=item.get("page", "") or "",
                pdf_url=pdf_url,
            )
        )
    return papers


def _dedupe(papers: list[Paper]) -> list[Paper]:
    """Drop duplicate papers across sources (same DOI, or same title)."""
    seen: set[str] = set()
    out: list[Paper] = []
    for p in papers:
        key = p.doi.lower() if p.doi else " ".join(p.title.lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


SORT_OPTIONS = ("relevance", "newest", "oldest", "cited")


def _sort_papers(papers: list[Paper], sort: str) -> list[Paper]:
    """Reorder results. Unknown-year / uncited papers sink to the bottom."""
    if sort == "newest":
        return sorted(papers, key=lambda p: (p.year is None, -(p.year or 0)))
    if sort == "oldest":
        return sorted(papers, key=lambda p: (p.year is None, p.year or 0))
    if sort == "cited":
        return sorted(
            papers, key=lambda p: (p.citations is None, -(p.citations or 0))
        )
    return papers  # "relevance": keep the databases' own ordering


def search(
    query: str,
    limit: int = 5,
    sources: list[str] | None = None,
    strict: bool = True,
    sort: str = "relevance",
    year_from: int | None = None,
) -> list[Paper]:
    """Search every requested source and merge the results.

    ``sources`` defaults to ``DEFAULT_SOURCES`` (all four). Failures in one
    source are swallowed so a single API hiccup doesn't kill the run.
    Results are cached for a day so reruns are instant and free.

    - ``strict`` (default on): drop papers whose title doesn't contain every
      meaningful query word (or a synonym / word-form).
    - ``sort``: one of relevance / newest / oldest / cited.
    - ``year_from``: keep only papers published in or after this year.
    """
    from . import cache

    sources = sources or DEFAULT_SOURCES
    sort = sort if sort in SORT_OPTIONS else "relevance"
    cache_key = (
        f"{query}|{limit}|{','.join(sorted(sources))}|strict={strict}"
        f"|sort={sort}|from={year_from}"
    )
    cached = cache.get("search", cache_key)
    if cached is not None:
        return [Paper(**row) for row in cached]

    runners = {
        "openalex": search_openalex,
        "arxiv": search_arxiv,
        "pubmed": search_pubmed,
        "crossref": search_crossref,
    }

    merged: list[Paper] = []
    failures = 0
    for name in sources:
        runner = runners.get(name)
        if not runner:
            continue
        try:
            merged.extend(runner(query, limit=limit))
        except Exception as exc:  # keep going if one source is down
            failures += 1
            print(f"[warn] {name} search failed: {exc}")
        time.sleep(0.34)  # be gentle with the free APIs

    merged = _dedupe(merged)

    if strict:
        from . import relevance

        before = len(merged)
        merged = relevance.filter_by_title(merged, query)
        dropped = before - len(merged)
        if dropped:
            print(
                f"[filter] kept {len(merged)} of {before} results whose title "
                f"matches '{query}' (use --loose to include the rest)"
            )

    if year_from is not None:
        merged = [p for p in merged if p.year is not None and p.year >= year_from]

    merged = _sort_papers(merged, sort)

    # Only cache complete runs; a partial result from an outage shouldn't
    # stick around for a day.
    if merged and failures == 0:
        cache.put("search", cache_key, [p.to_dict() for p in merged])
    return merged
