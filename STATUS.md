# STATUS.md — chapter-critique

Last updated: 2026-10-31

## What was built

`chapter-critique` — a manuscript-first-draft helper. Feed a chapter file and
get a structured critique from any OpenAI-compatible endpoint (including a
local Ollama server), with **no API keys** and a fully offline `--no-llm`
mode.

Components:

- `chapter_critique/analyzer.py` — deterministic analysis engine:
  - **pacing flags**: scene length spreads (drag-outs 1500+, thin <100),
    paragraphs of 150+ unbroken narration words, dialogue-ratio jumps
    between neighboring scenes — all with file line numbers
  - **filter-word counts** (`felt`, `seemed`, `wondered`, `realized`, ...)
    and **weasel-word counts** (`very`, `really`, `just`, `suddenly`, ...),
    dialogue excluded, with per-line locations
  - **dialogue-tag repetition**: plain vs. fancy tag totals, per-tag counts,
    adverb-stuffed tags ("said quietly") detected automatically
  - **scene-goal clarity**: per scene, measured intent/conflict signal counts
    and an ending-hook check, scored clear / partial / unclear
  - **over-explaining detection**: repeated-idea consecutive sentences,
    "as you know"-style exposition fillers, paragraphs averaging 30+
    word sentences
- `chapter_critique/critique.py` — prompt builder that feeds the LLM the
  measured numbers as ground truth, requests exactly seven fixed sections
  (opening with **What's Already Working** — encouragement-first is
  enforced both in the prompt and locally), plus a stats-only critique
  generator
- `chapter_critique/llm.py` — 70-line OpenAI-compatible chat client on the
  standard library's `urllib` (Ollama, LM Studio, llama.cpp, vLLM, OpenAI);
  no key is read, stored, or sent
- `chapter_critique/config.py` — `config.toml` (endpoint + sampling) and
  `rubric.toml` (fully editable style rubric the critique is rubbed against)
- `chapter_critique/cli.py` — the `chapter-critique` command
- `examples/sample-chapter.md` — worked sample chapter

## How to run it

```bash
pip install -e .            # Python 3.11+, stdlib-only at runtime
chapter-critique --init     # writes editable config.toml + rubric.toml
ollama serve & ollama pull llama3.1   # or point base_url at any OpenAI-compatible server
chapter-critique examples/sample-chapter.md -o critique.md
chapter-critique examples/sample-chapter.md --no-llm   # stats-only, zero network
```

## Verification results

- `pytest`: **50/50 passing** — `tests/` mocks the LLM entirely
  (`MockLLM` in `tests/conftest.py`), so the suite runs offline and
  deterministic. Covers analyzer behaviors (filter/weasel words, tags,
  pacing, scene goals, over-explaining), config/rubric loading
  (including the no-API-keys guarantee), critique orchestration with
  mocked responses, and the CLI.
- End-to-end HTTP verified against a **fake OpenAI-compatible server** on
  `127.0.0.1` serving canned chat completions: the real client path
  (`/v1/chat/completions` POST → seven required sections rendered) works.
- Endpoint-unreachable path verified: clean error message, exit code 2,
  and the measured-stats critique is still written to `--output`.
- `pyflakes`: clean.
- Repo scan: no secrets, API keys, or personal data; LICENSE copyright
  line is exactly `Copyright (c) 2026 Asdale Dynamics, LLC`.

## Known gaps

- The narrative critique quality depends entirely on the model you point
  it at; small local models may skip sections (the CLI appends placeholders
  rather than hallucinating them).
- Scene splitting is driven by `***`/`---`/`###` breaks only — paragraphs
  act as internal blocks, so a chapter without hard breaks is one scene.
- Category word lists (filter words, weasel words, fancies/cliches tags)
  are editable in code but not yet exposed in `rubric.toml`.
- No streaming responses; the client reads the full completion in one POST.
- Sentences split on `.!?` — no markdown-aware headers/excerpt handling
  beyond truncation to 4000 chars for the LLM context.
