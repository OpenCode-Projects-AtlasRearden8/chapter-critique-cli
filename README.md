# chapter-critique

A manuscript-first-draft helper. Feed it a chapter file and get a structured
critique from any OpenAI-compatible endpoint - including your **local Ollama**
server - with **no API keys and no cloud required**.

Every critique blends two layers:

1. **Measured analysis** (fast, deterministic, done before the LLM is asked
   anything): pacing flags, filter-word and weasel-word counts with line
   numbers, dialogue-tag repetition, scene-goal clarity, and
   over-explaining detection.
2. **A narrative critique** from the model of your choice, grounded in
   those measured numbers and checked against a style rubric *you can
   edit* (`rubric.toml`).

The summary always opens with genuine encouragement about what already
works, because first drafts deserve to survive their first review.

> Part of the Asdale Dynamics, LLC toolset - beginner-friendly, local-first
> writing tools. Plain English, step by step, never condescending.

## What it measures

| Check | What you see |
| --- | --- |
| Pacing | Scene lengths, drag-outs (1500+ word scenes), paragraphs of 150+ unbroken narration words, wild dialogue-ratio jumps between scenes |
| Filter words | `felt`, `seemed`, `wondered`, `realized`, `noticed`, `saw`, `heard`... with counts and line numbers (dialogue is excluded) |
| Weasel words | `very`, `really`, `just`, `suddenly`, `somehow`, `probably`... with counts and line numbers |
| Dialogue tags | Plain vs. fancy tag counts, tag repetition, adverb-stuffed tags ("said quietly"), action beats |
| Scene goals | Per scene: does it state an intent, meet friction, end on a hook? Scored clear / partial / unclear |
| Over-explaining | Repeated-idea sentences, "as you know" filler, paragraphs averaging 30+ word sentences |

## Install

```bash
pip install -e .
```

Python 3.11+. No dependencies beyond the standard library; `pytest` only
for the tests.

## Use

```bash
# 1. (optional) Generate starter config.toml + rubric.toml to edit
chapter-critique --init

# 2. Point it at your local Ollama (or edit config.toml)
ollama serve &
ollama pull llama3.1

# 3. Critique a chapter
chapter-critique chapters/two.md -o critique-two.md
```

Works with **any** OpenAI-compatible server - change `base_url` and
`model` in `config.toml`:

```toml
[endpoint]
base_url = "http://localhost:11434"   # Ollama; try http://localhost:1234/v1 for LM Studio
model = "llama3.1"

[critique]
temperature = 0.4
```

### No LLM? Still useful.

```bash
chapter-critique chapters/two.md --no-llm
```

gives a stats-only critique: encouragement-first summary plus every
measured number. The LLM layer is a bonus, not a requirement.

## The rubric is yours

`chapter-critique --init` writes a `rubric.toml`. It is plain English -
rules per topic like:

```toml
[rubric.filter_words]
good = "Direct sensory narration; the reader is inside the moment."
flag = "'felt', 'saw', 'heard', 'noticed', 'realized' push the reader out..."
```

Reword, add, or delete anything. The critique is rubbed against your
rubric, not ours. One rule is enforced no matter what you write: the
critique opens with **What's Already Working** before any criticism.

### How it differs from the neighbors

- `chapter-critique` (this project): first-draft chapter feedback.
- `book-bible-audit-cli`: consistency across a *series bible*.
- `doc-proofreader-cli`: grammar and mechanics for finished prose.

## Privacy

- No API keys, ever - the config has no key field and the code reads none.
- Your manuscript text goes only to the endpoint you configure
  (e.g. your own machine running Ollama). Run with `--no-llm` and
  nothing leaves the process.

## Development

```bash
pip install -e . pytest
pytest            # 49 tests, mocked LLM responses, no network
```

Tests mock the endpoint entirely (`MockLLM` in `tests/conftest.py`),
so the suite runs offline and stable.

## License

MIT - see [LICENSE](LICENSE).

Copyright (c) 2026 Asdale Dynamics, LLC. Built the way we'd want a friend
to explain it: plain, warm, and tested.
