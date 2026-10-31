"""Configuration loading (config.toml + rubric.toml).

No API keys anywhere. The top-level config points at any
OpenAI-compatible chat endpoint, e.g. a local Ollama server.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG = """\
# chapter-critique configuration.
# No API keys here - anything OpenAI-compatible works, including Ollama.

[endpoint]
# Local Ollama example. Change base_url/model for other servers.
base_url = "http://localhost:11434"
model = "llama3.1"
# Optional: set a flavor of the model to steer the voice.
system_hint = "You are a warm, encouraging developmental editor."

[critique]
# Temperature for the narrative critique.
temperature = 0.4
# Hard cap on tokens requested from the endpoint.
max_tokens = 2048
# Extra context lines sent around each excerpt.
context_lines = 1
"""

DEFAULT_RUBRIC = """\
# Editable style rubric. The LLM critique is checked against these rules.
# Add, remove, or reword anything; keep it in plain English.

[rubric]

[rubric.pacing]
good = "Scene lengths vary naturally; dialogue and action keep pages turning; no scene drags past ~1500 words without a beat change."
flag = "Flag scenes over ~1500 words or under ~100 words, and long unbroken narration paragraphs (150+ words)."

[rubric.filter_words]
good = "Direct sensory narration; the reader is inside the moment."
flag = "'felt', 'saw', 'heard', 'noticed', 'realized', 'seemed' push the reader out. Suggest direct rendering instead of listing every instance."

[rubric.weasel_words]
good = "Concrete, committed prose."
flag = "'very', 'really', 'just', 'suddenly', 'somehow' and hedging words weaken voice. Suggest deletion or a concrete replacement."

[rubric.dialogue_tags]
good = "'said' and action beats dominate; fancy tags are rare and earned."
flag = "Flag tag repetition above ~60% of one verb (excluding 'said') and adverb-stuffed tags; suggest action beats or revision."

[rubric.scene_goals]
good = "Every scene opens with a clear POV goal, meets friction, and ends on a hook."
flag = "Flag scenes with no stated intent, no obstacle, and no hook; suggest one opening line that names what the POV wants."

[rubric.over_explaining]
good = "Trust the reader; exposition is drip-fed through conflict."
flag = "Flag repeated-idea sentences, 'as you know' exposition, and paragraphs averaging 30+ word sentences."

[rubric.summary]
good = "Open with genuine, specific encouragement about what already works before anything else."
flag = "Never open the summary with criticism. Keep the voice friendly and plain-English, like a friend editing your draft."
"""


@dataclass
class EndpointConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    system_hint: str = "You are a warm, encouraging developmental editor."


@dataclass
class CritiqueConfig:
    temperature: float = 0.4
    max_tokens: int = 2048
    context_lines: int = 1


@dataclass
class Config:
    endpoint: EndpointConfig = field(default_factory=EndpointConfig)
    critique: CritiqueConfig = field(default_factory=CritiqueConfig)


def load_config(path: str | Path | None) -> Config:
    if path is None:
        if Path("config.toml").is_file():
            path = "config.toml"
        else:
            return Config()
    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = Config()
    for key, value in data.get("endpoint", {}).items():
        if hasattr(cfg.endpoint, key):
            setattr(cfg.endpoint, key, value)
    for key, value in data.get("critique", {}).items():
        if hasattr(cfg.critique, key):
            setattr(cfg.critique, key, value)
    return cfg


def write_default_config(path: str | Path) -> None:
    Path(path).write_text(DEFAULT_CONFIG, encoding="utf-8")


def load_rubric(path: str | Path | None) -> str:
    if path is None:
        if Path("rubric.toml").is_file():
            path = "rubric.toml"
        else:
            return DEFAULT_RUBRIC
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"rubric file not found: {path}")
    return path.read_text(encoding="utf-8")


def write_default_rubric(path: str | Path) -> None:
    Path(path).write_text(DEFAULT_RUBRIC, encoding="utf-8")
