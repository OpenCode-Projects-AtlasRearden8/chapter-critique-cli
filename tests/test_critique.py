"""Tests for critique orchestration with a mocked LLM (no network)."""

from __future__ import annotations

from chapter_critique.critique import (
    REQUIRED_SECTIONS,
    build_messages,
    build_stats_block,
    ensure_sections,
    run_critique,
)
from chapter_critique.analyzer import analyze
from chapter_critique.llm import OpenAICompatibleClient

from tests.conftest import MOCK_RESPONSE, MockLLM


def test_run_critique_uses_mock_and_returns_text(chapter_text, mock_llm, mock_response):
    analysis, text = run_critique(chapter_text, mock_llm)
    assert text == mock_response.strip() or text.startswith("## What's Already Working")
    assert mock_llm.calls, "LLM should be called exactly once"
    assert len(mock_llm.messages) == 1


def test_mock_messages_build_payload(chapter_text, mock_llm):
    run_critique(chapter_text, mock_llm)
    messages = mock_llm.messages[0]
    assert [m["role"] for m in messages] == ["system", "user"]
    user = messages[1]["content"]
    assert "Measured Data" in user or "MEASURED DATA" in user
    assert "STYLE RUBRIC" in user
    # measured stats are injected so the LLM can't invent numbers
    assert "Filter words" in user
    assert "Weasel words" in user
    assert "Dialogue tagging" in user
    assert "Scene goals:" in user
    # real measured values, not placeholders
    assert "said quietly" in user  # actual adverb tag measured in the sample


def test_build_stats_block_is_grounded(chapter_text):
    block = build_stats_block(analyze(chapter_text))
    assert "Total words:" in block
    assert f"Scenes: {len(analyze(chapter_text).scenes)}" in block
    assert "Dialogue tag counts" in block
    assert "said quietly" in block  # measured adverb tag appears


def test_prompt_requests_exact_sections(chapter_text):
    analysis = analyze(chapter_text)
    messages = build_messages(analysis, chapter_text, "RUBRIC")
    assert all(s in messages[0]["content"] for s in REQUIRED_SECTIONS)


def test_ensure_sections_fills_missing():
    partial = "## What's Already Working\nNice work here."
    filled = ensure_sections(partial)
    for s in REQUIRED_SECTIONS:
        assert f"## {s}" in filled


def test_ensure_sections_keeps_complete():
    good = MOCK_RESPONSE
    filled = ensure_sections(good)
    assert filled == good


def test_run_critique_offline_mode(chapter_text):
    analysis, text = run_critique(chapter_text, None)
    assert "## What's Already Working" in text   # encouragement-first
    assert "Measured Stats" in text
    # no network objects touched
    assert analysis.total_words > 0


def test_offline_mode_orders_encouragement_first(chapter_text):
    _a, text = run_critique(chapter_text, None)
    heading = text.lstrip().split("\n", 1)[0]
    assert heading.startswith("## What's Already Working")


def test_openai_client_url_for_ollama():
    client = OpenAICompatibleClient(base_url="http://localhost:11434", model="llama3.1")
    assert client.endpoint_url == "http://localhost:11434/v1/chat/completions"


def test_openai_client_keeps_existing_v1():
    client = OpenAICompatibleClient(base_url="http://127.0.0.1:5000/v1")
    assert client.endpoint_url == "http://127.0.0.1:5000/v1/chat/completions"


def test_mock_llm_matches_client_protocol(chapter_text):
    """MockLLM must satisfy the same Protocol as OpenAICompatibleClient."""
    from chapter_critique.llm import LLMClient
    analysis = analyze(chapter_text)
    messages = build_messages(analysis, chapter_text, "R")
    assert MockLLM().chat(messages) == MOCK_RESPONSE
    # structural typing: both declare chat(list[dict]) -> str
    assert callable(MockLLM().chat)
    assert hasattr(LLMClient, "chat")
