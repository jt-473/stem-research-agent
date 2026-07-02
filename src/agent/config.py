"""Shared configuration. Reads from environment / .env."""

from __future__ import annotations

import os

# Load a .env file if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Where generated reports are written.
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "outputs")

# Default referencing style for citations. One of: harvard, apa, mla,
# chicago, ieee, vancouver.
DEFAULT_STYLE = os.environ.get("CITATION_STYLE", "harvard")
