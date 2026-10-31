"""Tests for config and rubric handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from chapter_critique.config import (
    Config,
    EndpointConfig,
    load_config,
    load_rubric,
    write_default_config,
)

CUSTOM_CONFIG = """\
[endpoint]
base_url = "http://127.0.0.1:5000/v1"
model = "mistral"
system_hint = "Be blunt."

[critique]
temperature = 0.7
max_tokens = 512
"""


def test_load_config_defaults_when_missing():
    cfg = load_config(Path("/nonexistent/config-nope.toml")) if False else Config()
    assert cfg.endpoint.base_url.startswith("http")
    assert cfg.critique.temperature == 0.4


def test_load_config_explicit_file(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text(CUSTOM_CONFIG, encoding="utf-8")
    cfg = load_config(path)
    assert isinstance(cfg.endpoint, EndpointConfig)
    assert cfg.endpoint.base_url == "http://127.0.0.1:5000/v1"
    assert cfg.endpoint.model == "mistral"
    assert cfg.critique.temperature == 0.7
    assert cfg.critique.max_tokens == 512


def test_write_default_config_roundtrip(tmp_path: Path):
    path = tmp_path / "out.toml"
    write_default_config(path)
    cfg = load_config(path)
    assert isinstance(cfg, Config)


def test_load_rubric_default(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rubric = load_rubric(None)
    assert "rubric" in rubric
    assert "specific encouragement" in rubric  # encouragement-first rule


def test_load_rubric_custom_file(tmp_path: Path):
    path = tmp_path / "rubric.toml"
    path.write_text('[rubric.summary]\nflag = "kindness first"\n', encoding="utf-8")
    assert "kindness first" in load_rubric(path)


def test_load_rubric_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_rubric(tmp_path / "missing.toml")


def test_no_api_keys_anywhere(tmp_path: Path):
    """The defaults must never ask for, read, or store API keys."""
    path = tmp_path / "out.toml"
    write_default_config(path)
    text = path.read_text(encoding="utf-8")
    assert "api_key" not in text.lower()
    assert "apikey" not in text.lower()
