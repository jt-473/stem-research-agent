"""Format papers into different referencing styles.

Supports the styles a student is most likely to be told to use:
Harvard, APA, MLA, Chicago (author-date), IEEE, and Vancouver.

Two things you get for each style:
- a full reference-list entry (``format_reference``)
- an in-text citation (``in_text``), optionally with a locator like a
  page or section so you can cite a specific part of the paper.

Name and page parsing is best-effort. Databases don't always give clean
author names or page ranges, so always eyeball the output before you
hand a report in.
"""

from __future__ import annotations

from .sources import Paper

# Human-readable descriptions so a user can pick the right one.
STYLES: dict[str, str] = {
    "harvard": "Harvard - author-date, common in UK universities and the "
    "sciences/social sciences. In-text: (Smith, 2020). Reference list is "
    "alphabetical by surname.",
    "apa": "APA (7th) - author-date, used in psychology, education, and the "
    "sciences. In-text: (Smith & Jones, 2020, p. 4).",
    "mla": "MLA (9th) - author-page, used in English and the humanities. "
    "In-text: (Smith 4).",
    "chicago": "Chicago (author-date) - used across the sciences and social "
    "sciences. In-text: (Smith 2020, 4). (There's also a notes-bibliography "
    "variant this tool doesn't produce.)",
    "ieee": "IEEE - numbered, used in engineering and computer science. "
    "In-text: [1], numbered in citation order.",
    "vancouver": "Vancouver - numbered, used in medicine and the life "
    "sciences. In-text: (1), numbered in citation order.",
}

# Styles that cite by number rather than author-date.
NUMBERED = {"ieee", "vancouver"}


def list_styles() -> str:
    """Return a printable description of every supported style."""
    return "\n".join(f"- {key}: {desc}" for key, desc in STYLES.items())


def _normalize(style: str) -> str:
    style = (style or "harvard").strip().lower()
    if style not in STYLES:
        raise ValueError(
            f"Unknown style {style!r}. Choose from: {', '.join(STYLES)}"
        )
    return style


def _split_name(full: str) -> tuple[str, list[str]]:
    """Best-effort split of "First Middle Last" into (surname, [given...])."""
    parts = full.strip().split()
    if not parts:
        return ("", [])
    if len(parts) == 1:
        return (parts[0], [])
    return (parts[-1], parts[:-1])


def _initials(given: list[str], sep: str = ".", space: str = " ") -> str:
    """Turn given names into initials, e.g. ['John','Q'] -> 'J. Q.'"""
    return space.join(f"{g[0].upper()}{sep}" for g in given if g)


# --- author blocks per style -------------------------------------------------

def _authors_harvard_apa(authors: list[str]) -> str:
    """Surname, Initials. — used by Harvard and APA reference lists."""
    if not authors:
        return ""
    formatted = []
    for name in authors[:20]:
        surname, given = _split_name(name)
        inits = _initials(given)
        formatted.append(f"{surname}, {inits}".strip())
    if len(formatted) == 1:
        return formatted[0]
    return ", ".join(formatted[:-1]) + " and " + formatted[-1]


def _authors_mla(authors: list[str]) -> str:
    if not authors:
        return ""
    surname, given = _split_name(authors[0])
    first = f"{surname}, {' '.join(given)}".strip().rstrip(",")
    if len(authors) == 1:
        return first
    if len(authors) == 2:
        return f"{first}, and {authors[1]}"
    return f"{first}, et al"


def _authors_chicago(authors: list[str]) -> str:
    if not authors:
        return ""
    surname, given = _split_name(authors[0])
    first = f"{surname}, {' '.join(given)}".strip().rstrip(",")
    # Authors after the first are written given-name-first.
    rest = [f"{' '.join(_split_name(a)[1])} {_split_name(a)[0]}".strip() for a in authors[1:]]
    if not rest:
        return first
    if len(rest) == 1:
        return f"{first}, and {rest[0]}"
    return f"{first}, " + ", ".join(rest[:-1]) + ", and " + rest[-1]


def _authors_numbered(authors: list[str]) -> str:
    """Initials-first form used by IEEE / Vancouver."""
    formatted = []
    for name in authors[:6]:
        surname, given = _split_name(name)
        inits = _initials(given, sep=".", space=" ")
        formatted.append(f"{inits} {surname}".strip())
    joined = ", ".join(formatted)
    if len(authors) > 6:
        joined += ", et al."
    return joined


# --- full reference entries --------------------------------------------------

def format_reference(paper: Paper, style: str = "harvard", number: int | None = None) -> str:
    """Return a reference-list entry for ``paper`` in the given style.

    ``number`` is used by numbered styles (IEEE/Vancouver) for the [n]
    prefix. Ignored by author-date styles.
    """
    style = _normalize(style)
    title = paper.title.rstrip(".")
    year = paper.year or "n.d."
    venue = paper.venue or paper.source
    vol, iss, pages = paper.volume, paper.issue, paper.pages
    doi = f"https://doi.org/{paper.doi}" if paper.doi else paper.url

    if style == "harvard":
        vi = f"{vol}({iss})" if vol and iss else vol
        tail = ", ".join(b for b in (vi, f"pp. {pages}" if pages else "") if b)
        ref = f"{_authors_harvard_apa(paper.authors)} ({year}) '{title}', {venue}"
        if tail:
            ref += f", {tail}"
        if doi:
            ref += f". Available at: {doi}"
        return ref + "."

    if style == "apa":
        vi = f"{vol}({iss})" if vol and iss else vol
        locus = ", ".join(b for b in (vi, pages) if b)
        ref = f"{_authors_harvard_apa(paper.authors)} ({year}). {title}. {venue}"
        if locus:
            ref += f", {locus}"
        if doi:
            ref += f". {doi}"
        return ref + "."

    if style == "mla":
        ref = f'{_authors_mla(paper.authors)}. "{title}." {venue}'
        if vol:
            ref += f", vol. {vol}"
        if iss:
            ref += f", no. {iss}"
        ref += f", {year}"
        if pages:
            ref += f", pp. {pages}"
        return ref + "."

    if style == "chicago":
        ref = f'{_authors_chicago(paper.authors)}. {year}. "{title}." {venue}'
        if vol:
            ref += f" {vol}"
        if iss:
            ref += f" ({iss})"
        if pages:
            ref += f": {pages}"
        if doi:
            ref += f". {doi}"
        return ref + "."

    if style == "ieee":
        n = f"[{number}] " if number else ""
        ref = f'{n}{_authors_numbered(paper.authors)}, "{title}," {venue}'
        if vol:
            ref += f", vol. {vol}"
        if iss:
            ref += f", no. {iss}"
        if pages:
            ref += f", pp. {pages}"
        ref += f", {year}"
        return ref + "."

    if style == "vancouver":
        n = f"{number}. " if number else ""
        ref = f"{n}{_authors_numbered(paper.authors)}. {title}. {venue}. {year}"
        if vol:
            ref += f";{vol}"
        if iss:
            ref += f"({iss})"
        if pages:
            ref += f":{pages}"
        return ref + "."

    return paper.citation_line()  # unreachable, keeps type checkers happy


# --- in-text citations -------------------------------------------------------

def in_text(
    paper: Paper,
    style: str = "harvard",
    locator: str | None = None,
    number: int | None = None,
) -> str:
    """Return an in-text citation, optionally pointing at a specific part.

    ``locator`` is a page or section, e.g. "p. 4", "pp. 4-5", "sec. 3.2",
    or "abstract" when that's all we have. It lets a student cite the exact
    passage they're quoting.
    """
    style = _normalize(style)
    year = paper.year or "n.d."
    surname = _split_name(paper.authors[0])[0] if paper.authors else "Anon"
    etal = " et al." if len(paper.authors) > 1 else ""

    if style in NUMBERED:
        n = number if number is not None else "n"
        if style == "ieee":
            # IEEE puts the locator inside the brackets: [1, p. 4].
            return f"[{n}, {locator}]" if locator else f"[{n}]"
        # Vancouver cites the whole reference by number; no page locator.
        return f"({n})"

    if style == "mla":
        # MLA uses a page number with no comma and no year.
        page = locator or ""
        page = page.replace("p. ", "").replace("pp. ", "")
        return f"({surname}{etal} {page})".replace("  ", " ").strip()

    if style == "chicago":
        loc = f", {locator.replace('p. ', '').replace('pp. ', '')}" if locator else ""
        return f"({surname}{etal} {year}{loc})"

    # harvard / apa
    sep = ", " if style == "apa" else ", "
    loc = f"{sep}{locator}" if locator else ""
    return f"({surname}{etal}{sep}{year}{loc})"
