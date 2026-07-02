"""A small local web interface, no extra installs needed.

Run ``python main.py web`` and a browser page opens with a search box and a
style picker. Everything runs on Python's standard library, and it binds to
127.0.0.1 only: it's a local tool, not something to expose to a network.
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .citations import STYLES, format_reference, in_text
from .config import DEFAULT_STYLE
from .sources import SORT_OPTIONS

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"  [web] {self.command} {self.path}")

    # --- helpers ---------------------------------------------------------

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str, ctype: str) -> None:
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- routes ----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path in ("/", "/index.html"):
            self._send_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
            return

        if self.path == "/api/meta":
            self._send_json(
                {
                    "styles": {k: v.split(". ")[0] for k, v in STYLES.items()},
                    "default_style": DEFAULT_STYLE,
                    "sorts": list(SORT_OPTIONS),
                }
            )
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/search":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "Bad request body."}, status=400)
            return

        question = (req.get("question") or "").strip()
        if not question:
            self._send_json({"error": "Type a research question first."}, status=400)
            return
        style = req.get("style") or DEFAULT_STYLE
        if style not in STYLES:
            style = DEFAULT_STYLE
        sort = req.get("sort") if req.get("sort") in SORT_OPTIONS else "relevance"
        try:
            limit = max(1, min(25, int(req.get("limit", 8))))
        except (TypeError, ValueError):
            limit = 8
        try:
            year_from = int(req["year_from"]) if req.get("year_from") else None
        except (TypeError, ValueError):
            year_from = None

        try:
            from .sources import search

            papers = search(question, limit=limit, sort=sort, year_from=year_from)
            self._send_json(
                {
                    "style": style,
                    "sort": sort,
                    "sources": [
                        {
                            "title": p.title,
                            "year": p.year,
                            "source": p.source,
                            "citations": p.citations,
                            "url": p.url,
                            "reference": format_reference(p, style, number=i),
                            "in_text": in_text(p, style, number=i),
                        }
                        for i, p in enumerate(papers, start=1)
                    ],
                }
            )
        except Exception as exc:
            self._send_json(
                {"error": f"Something went wrong: {exc}. Try a broader topic."},
                status=500,
            )


def serve(port: int = 8765, open_browser: bool = True) -> int:
    """Start the local web UI and block until Ctrl+C."""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"STEM Research Agent web UI running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0
