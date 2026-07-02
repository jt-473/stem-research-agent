"""Keep only papers whose title actually contains the search terms.

The scholarly APIs rank by relevance but still return loosely-related
papers (a search for "caffeine reaction time" can surface a physics paper
just because its title has the word "time"). This module enforces a hard
rule instead: every meaningful word in your query must show up in the
paper's title, either directly, as a word-form (kick / kicks / kicking),
or as a synonym (football / soccer).

Matching is deliberate and offline-friendly:
- word-forms are handled by a light stemmer (no dependencies)
- synonyms come from a built-in map, plus WordNet when it's available
"""

from __future__ import annotations

import re

# Common words we never require a title to contain.
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "is", "are",
    "be", "with", "by", "as", "at", "from", "into", "does", "do", "did", "how",
    "what", "why", "when", "which", "that", "this", "these", "those", "it",
    "its", "can", "could", "would", "should", "will", "vs", "versus", "using",
    "use", "study", "studies", "effect", "effects", "between", "about", "over",
}

# A small starter thesaurus for cross-word synonyms the stemmer can't catch.
# Each key maps to words treated as equivalent. Extend freely.
SYNONYMS: dict[str, set[str]] = {
    "football": {"soccer"},
    "soccer": {"football"},
    "kick": {"strike", "punt"},
    "car": {"automobile", "vehicle"},
    "kid": {"child", "children"},
    "heart": {"cardiac", "cardiovascular"},
    "cancer": {"tumor", "tumour", "carcinoma", "oncology"},
    "brain": {"neural", "cerebral", "cognitive"},
    "drug": {"medication", "pharmaceutical"},
    "exercise": {"training", "workout", "physical activity"},
    "diet": {"nutrition", "dietary"},
    "sleep": {"slumber"},
    "covid": {"coronavirus", "sars-cov-2"},
    "climate": {"global warming"},
}


def _stem(word: str) -> str:
    """Reduce a word to a rough root so word-forms match (kicks -> kick)."""
    w = re.sub(r"[^a-z0-9]+", "", word.lower())
    if len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("sses"):
        return w[:-2]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            root = w[: -len(suf)]
            # collapse a doubled final consonant (running -> run)
            if len(root) >= 2 and root[-1] == root[-2] and root[-1] not in "ls":
                root = root[:-1]
            return root
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


# --- WordNet synonyms (optional, best-effort) --------------------------------

_wn = None
_wn_tried = False


def _wordnet():
    """Return the WordNet corpus if usable, else None. Never raises."""
    global _wn, _wn_tried
    if _wn_tried:
        return _wn
    _wn_tried = True
    try:
        from nltk.corpus import wordnet as wn

        try:
            wn.synsets("test")  # triggers a LookupError if data is missing
        except LookupError:
            import nltk

            nltk.download("wordnet", quiet=True)
        _wn = wn
    except Exception:
        _wn = None
    return _wn


def _wordnet_synonyms(word: str) -> set[str]:
    wn = _wordnet()
    if not wn:
        return set()
    out: set[str] = set()
    try:
        for syn in wn.synsets(word)[:4]:  # top senses only, avoid drift
            for lemma in syn.lemmas():
                out.add(lemma.name().replace("_", " ").lower())
    except Exception:
        return set()
    return out


def _accepted_forms(term: str) -> tuple[set[str], set[str]]:
    """Return (single-word stems, multi-word phrases) that satisfy ``term``."""
    words = {term}
    words |= SYNONYMS.get(term, set())
    words |= _wordnet_synonyms(term)

    stems: set[str] = set()
    phrases: set[str] = set()
    for w in words:
        if " " in w:
            phrases.add(w.lower())
        else:
            stems.add(_stem(w))
    stems.discard("")
    return stems, phrases


def _content_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def title_matches(title: str, query: str) -> bool:
    """True if every meaningful query term appears in ``title``."""
    terms = _content_terms(query)
    if not terms:
        return True  # nothing specific to require

    title_low = title.lower()
    title_stems = {_stem(tok) for tok in re.findall(r"[a-zA-Z0-9]+", title_low)}

    for term in terms:
        stems, phrases = _accepted_forms(term)
        if title_stems & stems:
            continue
        if any(phrase in title_low for phrase in phrases):
            continue
        return False  # this term (and its synonyms) isn't in the title
    return True


def filter_by_title(papers: list, query: str) -> list:
    """Return only the papers whose title matches every query term."""
    return [p for p in papers if title_matches(p.title, query)]
