"""Shared configuration. Reads from environment / .env.

The AI provider is pluggable: set PROVIDER=anthropic (Claude) or
PROVIDER=gemini (Google Gemini, which has a free tier). Everything else
in the app is provider-agnostic and goes through llm.py.
"""

from __future__ import annotations

import os

# Load a .env file if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Which AI provider to use: "anthropic" (Claude) or "gemini" (Google).
PROVIDER = os.environ.get("PROVIDER", "anthropic").strip().lower()

# Default model per provider. Gemini's 2.5 Flash has a generous free tier;
# Claude Sonnet is a good cost/quality balance. Override with CLAUDE_MODEL /
# GEMINI_MODEL.
_MODEL_DEFAULTS = {
    "anthropic": "claude-sonnet-5",
    "gemini": "gemini-2.5-flash",
}


def _resolve_model() -> str:
    if PROVIDER == "gemini":
        return os.environ.get("GEMINI_MODEL", _MODEL_DEFAULTS["gemini"])
    return os.environ.get("CLAUDE_MODEL", _MODEL_DEFAULTS["anthropic"])


MODEL = _resolve_model()

# Where generated charts and reports are written.
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "outputs")

# Default referencing style for citations. One of: harvard, apa, mla,
# chicago, ieee, vancouver.
DEFAULT_STYLE = os.environ.get("CITATION_STYLE", "harvard")


def _key_env() -> str:
    """Name of the API-key environment variable for the active provider."""
    return "GEMINI_API_KEY" if PROVIDER == "gemini" else "ANTHROPIC_API_KEY"


def has_api_key() -> bool:
    """True if an API key is available for the active provider's AI features."""
    return bool(os.environ.get(_key_env()))


def _build_key_help() -> str:
    if PROVIDER == "gemini":
        return (
            "No Google Gemini API key found, so the AI features can't run yet.\n\n"
            "To fix it (one-time setup, free):\n"
            "  1. Get a free key at https://aistudio.google.com/apikey\n"
            "  2. Copy .env.example to a file named .env\n"
            "  3. Paste your key after GEMINI_API_KEY=\n\n"
            "The 'search', 'cite', and 'styles' commands work without a key."
        )
    return (
        "No Anthropic API key found, so the AI features can't run yet.\n\n"
        "To fix it (one-time setup):\n"
        "  1. Get a key at https://console.anthropic.com/\n"
        "  2. Copy .env.example to a file named .env\n"
        "  3. Paste your key after ANTHROPIC_API_KEY=\n\n"
        "The 'search', 'cite', and 'styles' commands work without a key."
    )


API_KEY_HELP = _build_key_help()
