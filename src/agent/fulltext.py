"""Fetch and read a paper's full text from its open-access PDF.

This is what turns a vague "from the abstract" quote into one with a real
page number. We download the PDF (only when the paper has an open-access
link), pull text out page by page with pypdf, and can then tell which
page any given quote came from.

Caveats worth knowing:
- Only open-access PDFs work. Paywalled papers have no usable link.
- PDF text extraction is imperfect: two-column layouts, math, and scanned
  images all come out messy. Page numbers are the PDF's page index, which
  usually matches the printed page but not always.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import requests

from .sources import HEADERS, Paper


@dataclass
class FullText:
    """Extracted text of a paper, kept per page so quotes can be located."""

    pages: list[str]
    source_url: str

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)

    def capped_text(self, max_chars: int) -> str:
        """Full text truncated to a token budget (keeps whole pages)."""
        out, total = [], 0
        for page in self.pages:
            if total + len(page) > max_chars:
                break
            out.append(page)
            total += len(page)
        return "\n\n".join(out) if out else self.text[:max_chars]

    def locate(self, quote: str) -> str | None:
        """Return "p. N" for the first page containing ``quote``, else None."""
        needle = _norm(quote)
        if not needle:
            return None
        for i, page in enumerate(self.pages, start=1):
            if needle in _norm(page):
                return f"p. {i}"
        return None


def _norm(text: str) -> str:
    """Collapse whitespace and lowercase so quote matching survives PDF quirks."""
    return " ".join(text.lower().split())


def fetch_fulltext(paper: Paper, timeout: int = 45, max_bytes: int = 25_000_000) -> FullText | None:
    """Download and extract a paper's PDF. Returns None if it can't.

    Failures (no link, paywall, unreadable PDF, oversized file) return None
    rather than raising, so callers can fall back to the abstract.
    """
    if not paper.pdf_url:
        return None
    try:
        from pypdf import PdfReader
    except ImportError:
        return None

    try:
        with requests.get(
            paper.pdf_url, headers=HEADERS, timeout=timeout, stream=True
        ) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if "pdf" not in ctype and not paper.pdf_url.lower().endswith(".pdf"):
                # Landing page, not a PDF. Bail rather than parse HTML.
                return None

            data = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=65536):
                data.write(chunk)
                if data.tell() > max_bytes:
                    return None  # too big, don't try to parse it

        data.seek(0)
        reader = PdfReader(data)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        if not any(pages):
            return None  # scanned/image PDF with no extractable text
        return FullText(pages=pages, source_url=paper.pdf_url)
    except Exception:
        return None
