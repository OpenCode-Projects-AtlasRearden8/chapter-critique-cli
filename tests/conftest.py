"""Shared fixtures: a sample chapter and a mock LLM client."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample-chapter.md"

MOCK_RESPONSE = """\
## What's Already Working

Maren's want is stated early and cleanly, and the dialogue in scene 2
carries the plot without rescue from narration: 2 of 2 scenes open with
intent plus visible friction. The plain-tag discipline is real.

## Pacing

Scene 1 is only 60 words, so the harbor image lands but evaporates;
consider extending it to a beat of choice (line 1). The dialogue ratio
swings hard into scene 2, which may read as a jump.

## Voice and Word Choice

The data shows heavy filter use: "felt" (line 3), "seemed", "wondered",
"realized". Render the storm directly: "Wind hit first. Then iron."

## Dialogue

Tag counts look tidy, but "she said quietly" (line 14) pairs a plain tag
with an adverb; let the sentence carry the hush instead.

## Scene Goals

Both scenes name a goal ("find Bram", "go to the tower") and both get an
obstacle; the bell hook at line 19 is doing work. Keep it.

## Over-Explaining

The ledger paragraph (line 15) repeats the chain of custody three times
in one breath; cut to two links. No "as you know" filler found.

## Next Draft Checklist

1. Cut filter words in scene 1 (lines 3-5).
2. Trim the ledger paragraph to two clauses.
3. Drop "quietly" from the "said" tag at line 14.
"""


class MockLLM:
    """Deterministic stand-in for an OpenAI-compatible endpoint."""

    def __init__(self, response: str = MOCK_RESPONSE):
        self.response = response
        self.calls: list[dict] = []
        self.messages: list[list[dict]] = []

    def chat(self, messages: list[dict]) -> str:
        self.calls.append({"count": 1})
        self.messages.append(messages)
        return self.response


@pytest.fixture()
def chapter_text() -> str:
    return SAMPLE.read_text(encoding="utf-8")


@pytest.fixture()
def mock_llm() -> MockLLM:
    return MockLLM()


@pytest.fixture()
def mock_response() -> str:
    return MOCK_RESPONSE


__all__ = ["MOCK_RESPONSE", "MockLLM"]
