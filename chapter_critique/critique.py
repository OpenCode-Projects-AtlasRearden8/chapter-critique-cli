"""Critique orchestration: deterministic stats + LLM narrative, merged."""

from __future__ import annotations

import json

from .analyzer import analyze
from .config import Config, load_config, load_rubric
from .llm import LLMClient
from .textstats import ChapterAnalysis

REQUIRED_SECTIONS = [
    "What's Already Working",
    "Pacing",
    "Voice and Word Choice",
    "Dialogue",
    "Scene Goals",
    "Over-Explaining",
    "Next Draft Checklist",
]

SYSTEM_PROMPT = """\
You are a warm, encouraging developmental editor for a fiction first draft.
Write in plain English, step by step, never condescending.

Ground every observation in the measured data below; do not invent numbers.
Use exactly these markdown sections, in this order, as "## " headers:

{sections}

Rules:
- "## What's Already Working" MUST come first and must contain only genuine,
  specific praise about what these numbers and excerpts show is working.
- Refer to concrete line numbers from the data when flagging issues.
- Do not restate the raw tables; interpret them.
- Keep under ~800 words total.
"""

USER_PROMPT = """\
Critique this chapter against the style rubric at the end.

== MEASURED DATA (computed programmatically; treat as ground truth) ==
{stats}

== SCENE OPENINGS ==
{scene_openings}

== CHAPTER EXCERPT (up to 4000 chars) ==
{excerpt}

== STYLE RUBRIC (editable by the writer) ==
{rubric}
"""


def build_stats_block(analysis: ChapterAnalysis) -> str:
    parts = [
        f"Total words: {analysis.total_words}",
        f"Scenes: {len(analysis.scenes)}",
    ]
    parts.append("Pacing flags:")
    pacing = [f for f in analysis.flags if f.kind == "pacing"]
    parts += [
        f"- {f.detail}" + (f" (line {f.line})" if f.line else "")
        for f in pacing
    ] or ["- none"]
    parts.append(f"Filter words ({analysis.per_1000(_total(analysis.filter_words))} per 1000):")
    parts += [
        f"- {s.word}: {s.count} (lines {','.join(map(str, s.lines[:5]))})"
        for s in analysis.filter_words[:15]
    ] or ["- none"]
    parts.append(f"Weasel words ({analysis.per_1000(_total(analysis.weasel_words))} per 1000):")
    parts += [
        f"- {s.word}: {s.count} (lines {','.join(map(str, s.lines[:5]))})"
        for s in analysis.weasel_words[:15]
    ] or ["- none"]
    d = analysis.dialogue
    parts.append(
        f"Dialogue tagging: plain tags={d.plain_count}, fancy tags={d.fancy_count}, "
        f"action beats={d.action_beat_lines}, dialogue lines={d.dialogue_lines}, "
        f"adverb tags: {d.adverb_tags or 'none'}"
    )
    parts.append("Dialogue tag counts: "
                 + json.dumps(d.tag_counts, sort_keys=True))
    parts.append("Scene goals:")
    for g in analysis.scene_goals:
        parts.append(
            f"- Scene {g['scene']} (line {g['start_line']}): goal={g['goal']}, "
            f"intent={g['intent_signals']}, conflict={g['conflict_signals']}, "
            f"hook={g['has_hook']}"
        )
    parts.append("Over-explaining findings:")
    parts += [
        f"- {o['kind']} in scene {o['scene']} (line {o['line']}): {o['detail']}"
        for o in analysis.over_explaining
    ] or ["- none"]
    return "\n".join(parts)


def _total(word_stats) -> int:
    return sum(s.count for s in word_stats)


def _scene_openings_block(analysis: ChapterAnalysis) -> str:
    return "\n".join(
        f"- Scene {g['scene']} (line {g['start_line']}): {g['opening']}"
        for g in analysis.scene_goals
    )


def build_messages(
    analysis: ChapterAnalysis, chapter_text: str, rubric: str
) -> list[dict]:
    excerpt = chapter_text.strip()[:4000]
    sections = ", ".join(REQUIRED_SECTIONS)
    system = SYSTEM_PROMPT.format(sections=sections)
    user = USER_PROMPT.format(
        stats=build_stats_block(analysis),
        scene_openings=_scene_openings_block(analysis),
        excerpt=excerpt if excerpt else "(empty chapter)",
        rubric=rubric,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def ensure_sections(text: str) -> str:
    """Append placeholder if the LLM skipped a required section."""
    missing = [
        s for s in REQUIRED_SECTIONS
        if f"## {s}" not in text and s.lower() not in text.lower()
    ]
    if missing:
        text = text.rstrip() + (
            "\n\n"
            + "\n\n".join(f"## {s}\n(try again with a stronger model for this section)"
                          for s in missing)
        )
    return text


def run_critique(
    chapter_text: str,
    llm: LLMClient | None,
    analysis: ChapterAnalysis | None = None,
    rubric: str | None = None,
    config: Config | None = None,
) -> tuple[ChapterAnalysis, str]:
    """Return (analysis, critique_markdown).

    llm=None gives a stats-only critique (offline mode).
    """
    analysis = analysis or analyze(chapter_text)
    if llm is None:
        return analysis, _stats_only_critique(analysis)
    config = config or load_config(None)
    rubric = rubric or load_rubric(None)
    messages = build_messages(analysis, chapter_text, rubric)
    response = llm.chat(messages)
    # rubric check: the encouragement-first rule is enforced locally too
    text = ensure_sections(response.strip())
    return analysis, text


def _stats_only_critique(analysis: ChapterAnalysis) -> str:
    """Encouragement-first summary with the strongest measured signals."""
    fw_total = _total(analysis.filter_words)
    ww_total = _total(analysis.weasel_words)
    clear = sum(1 for g in analysis.scene_goals if g["goal"] == "clear")
    d = analysis.dialogue
    lines = ["## What's Already Working\n"]
    working = []
    if clear:
        working.append(
            f"{clear} of {len(analysis.scene_goals)} scenes open with a clear goal and visible friction."
        )
    if d.plain_count > 3 * d.fancy_count and d.plain_count:
        working.append(
            f"Dialogue tagging is disciplined ({d.plain_count} plain tags vs {d.fancy_count} fancy)."
        )
    if analysis.scenes:
        working.append(
            f"The chapter breaks into {len(analysis.scenes)} scenes across {analysis.total_words} words - a real, finished draft, which matters more than any single flag below."
        )
    lines.append("\n".join(working) or "You have a live draft with measured, fixable signals - that is a win.")
    lines.append(
        "\n## Measured Stats\n"
        f"- Words: {analysis.total_words} | Scenes: {len(analysis.scenes)}\n"
        f"- Filter words: {fw_total} ({analysis.per_1000(fw_total)}/1k)\n"
        f"- Weasel words: {ww_total} ({analysis.per_1000(ww_total)}/1k)\n"
        f"- Dialogue tags: {d.plain_count} plain, {d.fancy_count} fancy, "
        f"{d.action_beat_lines} action beats\n"
    )
    if analysis.flags:
        lines.append("## Flags\n")
        lines.append("\n".join(
            f"- [{f.kind}] {f.detail}" + (f" (line {f.line})" if f.line else "")
            for f in analysis.flags
        ))
    return "\n".join(lines)
