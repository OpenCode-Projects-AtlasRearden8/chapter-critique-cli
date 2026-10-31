"""chapter-critique: manuscript-first-draft helper.

Feed a chapter file and get a structured critique from any
OpenAI-compatible endpoint (including local Ollama) - no API keys.
A deterministic analysis layer (pacing, filter words, weasel words,
dialogue tags, scene goals, over-explaining) is blended with an
LLM narrative critique checked against an editable style rubric.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
