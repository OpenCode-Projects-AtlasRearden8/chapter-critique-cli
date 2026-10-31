"""Tests for the CLI entry point (fully offline)."""

from __future__ import annotations

from pathlib import Path

import pytest
import urllib.error
import urllib.request

from chapter_critique.cli import main
from tests.conftest import SAMPLE, MockLLM


@pytest.fixture(autouse=True)
def offline_env(tmp_path, monkeypatch):
    """Run from an empty dir so no repo config leaks in; block real HTTP."""
    monkeypatch.chdir(tmp_path)

    def blocked(*a, **kw):
        raise urllib.error.URLError("blocked in tests")
    monkeypatch.setattr(urllib.request, "urlopen", blocked)


def test_no_llm_writes_output(tmp_path):
    out = tmp_path / "critique.md"
    rc = main([str(SAMPLE), "--no-llm", "-o", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "## What's Already Working" in text
    assert "Measured Stats" in text


def test_no_llm_stdout(monkeypatch):
    lines = []

    def fake_print(text):
        lines.append(text)
    monkeypatch.setattr("builtins.print", fake_print)
    rc = main([str(SAMPLE), "--no-llm"])
    assert rc == 0
    assert any("What's Already Working" in ln for ln in lines)


def test_llm_path_uses_mock_endpoint(tmp_path, monkeypatch):
    """Patching OpenAICompatibleClient with MockLLM end-to-end."""
    mock = MockLLM()
    import chapter_critique.cli as cli
    monkeypatch.setattr(cli, "OpenAICompatibleClient", lambda **kw: mock)
    out = tmp_path / "crit.md"
    rc = main([str(SAMPLE), "-o", str(out)])
    assert rc == 0
    assert mock.calls == [{"count": 1}]
    text = out.read_text(encoding="utf-8")
    assert "## Next Draft Checklist" in text


def test_init_writes_defaults(tmp_path):
    rc = main(["--init"])
    assert rc == 0
    assert (Path.cwd() / "config.toml").is_file()
    assert (Path.cwd() / "rubric.toml").is_file()


def test_missing_chapter_exits_1(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "nope.md")])
    assert exc.value.code == 1


def test_empty_chapter_exits_1(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([str(empty), "--no-llm"])
    assert exc.value.code == 1


def test_no_chapter_shows_help_and_returns_1():
    assert main([]) == 1


def test_unreachable_endpoint_falls_back_to_stats(tmp_path):
    """Without the network, the measured stats critique is still saved."""
    out = tmp_path / "fallback.md"
    rc = main([str(SAMPLE), "-o", str(out)])
    assert rc == 2
    text = out.read_text(encoding="utf-8")
    assert "## What's Already Working" in text   # encouragement-first even on failure
    assert "Measured Stats" in text


def test_custom_config_accepted(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text(
        '[endpoint]\nbase_url = "http://169.254.255.1"\nmodel = "m"\n',
        encoding="utf-8",
    )
    out = tmp_path / "o.md"
    rc = main([str(SAMPLE), "--no-llm", "-o", str(out), "-c", str(cfg)])
    assert rc == 0
    assert out.is_file()
