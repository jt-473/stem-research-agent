"""One text-generation interface for every AI provider.

The rest of the app calls ``complete(prompt, system=...)`` and doesn't care
whether Claude or Gemini answers. Which one runs is decided by PROVIDER in
config (from your .env). Clients are created lazily, so importing this never
needs a key, and a missing key produces the plain-English setup help.
"""

from __future__ import annotations

import os

from . import config

_anthropic_client = None
_gemini_client = None


def _require_key() -> None:
    if not config.has_api_key():
        raise SystemExit(config.API_KEY_HELP)


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        _require_key()
        from anthropic import Anthropic

        _anthropic_client = Anthropic()
    return _anthropic_client


def _gemini():
    global _gemini_client
    if _gemini_client is None:
        _require_key()
        try:
            from google import genai
        except ImportError:
            raise SystemExit(
                "The Gemini SDK isn't installed. Run: pip install google-genai"
            )
        _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _gemini_client


def anthropic_client():
    """Raw Claude client for features that need Anthropic-specific APIs."""
    return _anthropic()


def complete(prompt: str, system: str = "", max_tokens: int = 1000) -> str:
    """Send one prompt, get the text back. Works on either provider."""
    if config.PROVIDER == "gemini":
        return _complete_gemini(prompt, system, max_tokens)
    return _complete_anthropic(prompt, system, max_tokens)


def _complete_anthropic(prompt: str, system: str, max_tokens: int) -> str:
    client = _anthropic()
    kwargs = {
        "model": config.MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text.strip()


def _complete_gemini(prompt: str, system: str, max_tokens: int) -> str:
    from google.genai import types

    client = _gemini()
    cfg_kwargs = {
        "system_instruction": system or None,
        "max_output_tokens": max_tokens,
    }
    # Gemini 2.5 models "think" by default, which can eat the whole output
    # budget on these short structured calls. Turn it off for them.
    if "2.5" in config.MODEL:
        cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    resp = client.models.generate_content(
        model=config.MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**cfg_kwargs),
    )
    return (resp.text or "").strip()
