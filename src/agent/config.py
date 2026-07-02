"""Shared configuration. Reads from environment / .env."""

from __future__ import annotations

import os

# Load a .env file if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Claude model used for summarizing and synthesizing. Sonnet is a good
# cost/quality balance for this workload; override with CLAUDE_MODEL.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

# Where generated charts and reports are written.
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "outputs")

# Default referencing style for citations. One of: harvard, apa, mla,
# chicago, ieee, vancouver.
DEFAULT_STYLE = os.environ.get("CITATION_STYLE", "harvard")


def has_api_key() -> bool:
    """True if an Anthropic API key is available for the LLM features."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


API_KEY_HELP = """No Anthropic API key found, so the AI features can't run yet.

To fix it (one-time setup):
  1. Get a key at https://console.anthropic.com/
  2. Copy .env.example to a file named .env
  3. Paste your key after ANTHROPIC_API_KEY=

The 'search', 'cite', and 'styles' commands work without a key."""
