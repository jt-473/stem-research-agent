"""A small local web interface, no extra installs needed.

Run ``python main.py web`` and a browser page opens with a search box,
style picker, and results. Everything runs on Python's standard library
so a beginner doesn't need Node or any other toolchain.

The server binds to 127.0.0.1 only: it's a local tool, not something to
expose to a network.
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .citations import STYLES, format_reference, in_text
from .config import DEFAULT_STYLE, OUTPUT_DIR, has_api_key

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class Handler(BaseHTTPRequestHandler):
    # Quieter logs: one line per request, no noise.
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
                    "has_api_key": has_api_key(),
                }
            )
            return

        if self.path.startswith("/outputs/"):
            # Serve generated figures/reports. Resolve carefully so a crafted
            # path can't escape the outputs directory.
            name = self.path[len("/outputs/"):]
            base = os.path.abspath(OUTPUT_DIR)
            target = os.path.abspath(os.path.join(base, name))
            if not target.startswith(base + os.sep):
                self.send_error(403)
                return
            ctype = "image/png" if target.endswith(".png") else "text/plain; charset=utf-8"
            self._send_file(target, ctype)
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/research":
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
        want_quotes = bool(req.get("quotes"))
        try:
            limit = max(1, min(10, int(req.get("limit", 5))))
        except (TypeError, ValueError):
            limit = 5

        try:
            if has_api_key():
                self._send_json(self._full_research(question, style, want_quotes, limit))
            else:
                self._send_json(self._search_only(question, style, limit))
        except Exception as exc:
            self._send_json(
                {"error": f"Something went wrong: {exc}. Try a broader topic."},
                status=500,
            )

    # --- the two research paths -------------------------------------------

    def _full_research(self, question: str, style: str, want_quotes: bool, limit: int) -> dict:
        from .pipeline import run

        result = run(question, limit=limit, style=style, quotes=want_quotes)
        papers = result["papers"]
        return {
            "mode": "full",
            "style": style,
            "synthesis": result["synthesis"],
            "report": result["report"],
            "figures": ["/outputs/" + os.path.basename(f) for f in result["figures"]],
            "sources": [
                {
                    "title": p.title,
                    "year": p.year,
                    "url": p.url,
                    "reference": format_reference(p, style, number=i),
                    "in_text": in_text(p, style, number=i),
                    "main_finding": s.get("main_finding", ""),
                }
                for i, (p, s) in enumerate(zip(papers, result["summaries"]), start=1)
            ],
            "quotes": [
                {"paper": p.title, "items": q}
                for p, q in zip(papers, result["passages"] or [])
                if q
            ],
        }

    def _search_only(self, question: str, style: str, limit: int) -> dict:
        from .sources import search

        papers = search(question, limit=limit)
        return {
            "mode": "search_only",
            "style": style,
            "notice": "No API key set, so this is search and citations only. "
            "Add a key in .env for AI summaries and quotes.",
            "sources": [
                {
                    "title": p.title,
                    "year": p.year,
                    "url": p.url,
                    "reference": format_reference(p, style, number=i),
                    "in_text": in_text(p, style, number=i),
                }
                for i, p in enumerate(papers, start=1)
            ],
        }


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
