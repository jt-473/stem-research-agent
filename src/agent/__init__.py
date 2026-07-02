"""stem-research-agent: pull papers, cite them, summarize them, and chart data.

Submodules are imported lazily (not eagerly here) so lightweight parts
like ``sources`` and ``citations`` don't drag in the Anthropic SDK or
matplotlib unless you actually use them.
"""

__version__ = "0.2.0"
