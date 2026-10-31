"""Analysis engine: turns raw chapter text into a ChapterAnalysis."""

from __future__ import annotations

import re

from .textstats import (
    ChapterAnalysis,
    CONFLICT_MARKERS,
    DialogueStats,
    FANCY_TAGS,
    Flag,
    FILTER_WORDS,
    INTENT_MARKERS,
    PLAIN_TAGS,
    Scene,
    WEASEL_WORDS,
    WordStat,
)

SENTENCE_SPLIT = re.compile(r"[.!?]+[\"']?\s+")
DIALOGUE_LINE = re.compile(r'^\s*[\"\u201c\u201d]')
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\u2019-]*")


def _strip_dialogue(line: str) -> str:
    """Blank out quoted speech but KEEP the quote marks."""
    out, inside = [], False
    for ch in line:
        if ch in '"\u201c\u201d':
            inside = not inside
            out.append(ch)
        elif inside:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _count_verb_tags(line: str, stats: DialogueStats) -> None:
    """Count tag verbs in the tail after the first quote of a dialogue line."""
    text = _strip_dialogue(line)
    m = re.search(r"[\"\u201d](.*)$", text)
    if not m:
        return
    words = re.findall(r"[a-z]+", m.group(1).lower())
    for i, word in enumerate(words):
        if word not in PLAIN_TAGS and word not in FANCY_TAGS:
            continue
        stats.tag_counts[word] = stats.tag_counts.get(word, 0) + 1
        if word in PLAIN_TAGS:
            stats.plain_count += 1
        else:
            stats.fancy_count += 1
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if nxt.endswith("ly"):
            stats.adverb_tags.append(f"{word} {nxt}")


def _split_scenes(text: str) -> list[tuple[int, str, list[str]]]:
    """Split a chapter into scenes.

    Scenes are separated only by scene-break markers ('***', '---',
    '###' on a line by themselves). Blank lines stay inside the scene
    so paragraph structure (and pacing analysis) is preserved, and
    everything between two breaks counts as one scene, however long.
    """
    lines = text.splitlines()
    scenes: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start_line = 0

    def emit(start: int, block: list[str]) -> None:
        if any(ln.strip() for ln in block):
            scenes.append((start, block))

    for i, line in enumerate(lines, start=1):
        if re.fullmatch(r"\s*([*]{3}|[-]{3}|[#]{3})\s*", line):
            emit(start_line, current)
            current = []
            start_line = 0
        elif start_line == 0:
            if line.strip():
                start_line = i
                current.append(line)
            # blank lines before the first scene line are leading space
        else:
            current.append(line)
    emit(start_line, current)
    return [
        (start, "\n".join(block), block)
        for start, block in scenes
    ]


def _count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def count_word_stats(
    text: str, phrases: list[str], strip_quotes: bool
) -> list[WordStat]:
    """Count phrase occurrences (multi-word aware, case-insensitive)."""
    stats: dict[str, WordStat] = {}
    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        hay = _strip_dialogue(line) if strip_quotes else line
        hay = hay.lower()
        for phrase in phrases:
            # word-boundary aware: pad non-letters
            padded = re.sub(r"[^a-z0-9 ']", " ", hay)
            hits = _count_phrase(padded, phrase)
            if hits:
                st = stats.setdefault(phrase, WordStat(phrase, 0, []))
                st.count += hits
                st.lines.extend([lineno] * hits)
    # drop trivially-tiny counts for readability, keep all data
    return sorted(stats.values(), key=lambda s: (-s.count, s.word))


def _count_phrase(haystack: str, phrase: str) -> int:
    phrase = phrase.lower()
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return len(re.findall(pattern, haystack))


def _analyze_pacing(scenes: list[Scene], flags: list[Flag]) -> None:
    for sc in scenes:
        if sc.words > 1500:
            flags.append(Flag("pacing", f"Scene {sc.index} is long ({sc.words} words); consider a beat change or scene break.", None))
        elif 0 < sc.words < 100:
            flags.append(Flag("pacing", f"Scene {sc.index} is very thin ({sc.words} words).", None))
    # paragraph-level: long unbroken narration blocks
    for sc in scenes:
        for para in re.split(r"\n\s*\n", sc.text):
            clean = _strip_dialogue(para)
            if _count_words(clean) >= 150:
                flags.append(Flag(
                    "pacing",
                    "Long unbroken narration paragraph (150+ words) - consider splitting or a beat of dialogue.",
                    # first line of paragraph
                    sc.start_line + _line_offset(sc.text, para),
                ))
    # wild dialogue-ratio swings between neighbors
    for a, b in zip(scenes, scenes[1:]):
        if a.words < 50 or b.words < 50:
            continue
        d = abs(a.dialogue_ratio - b.dialogue_ratio)
        if d >= 0.6:
            flags.append(Flag(
                "pacing",
                f"Pace jump between scenes {a.index} and {b.index}: "
                f"(dialogue ratio {a.dialogue_ratio:.0%} -> {b.dialogue_ratio:.0%}). "
                "If unintended, ease the transition.",
                b.start_line,
            ))


def _line_offset(scene_text: str, para: str) -> int:
    idx = scene_text.find(para.splitlines()[0]) if para else 0
    if idx <= 0:
        return 0
    return scene_text.count("\n", 0, idx)


def _analyze_scene_goals(
    scenes: list[Scene], context_lines: int
) -> list[dict]:
    del context_lines
    goals = []
    for sc in scenes:
        if not sc.words:
            continue
        text = _strip_dialogue(sc.text).lower()
        intent = sum(marker in text for marker in INTENT_MARKERS)
        conflict = sum(marker in text for marker in CONFLICT_MARKERS)
        hook_words = ["when", "if ", "why", "what", "who ", "?"]
        hook = any(w in text[-220:] for w in hook_words)
        clear = intent >= 1 or sc.dialogue_ratio >= 0.25
        friction = conflict >= 1
        score = "clear" if (clear and friction) else (
            "partial" if (clear or friction) else "unclear"
        )
        goal = {
            "scene": sc.index,
            "start_line": sc.start_line,
            "opening": _opening_lines(sc.text),
            "intent_signals": intent,
            "conflict_signals": conflict,
            "has_hook": hook,
            "goal": score,
        }
        goals.append(goal)
    return goals


def _opening_lines(scene_text: str) -> str:  # noqa: N802
    paras = [p for p in re.split(r"\n\s*\n", scene_text) if p.strip()]
    return paras[0].strip()[:160] if paras else ""


def _analyze_over_explaining(scenes: list[Scene], flags: list[Flag]) -> list[dict]:
    findings = []
    fillers = [
        "as you know", "as is well known", "needless to say", "in other words",
        "which meant", "because of the fact", "the reason was", "and that is why",
    ]
    for sc in scenes:
        for para in re.split(r"\n\s*\n", sc.text):
            narration = _strip_dialogue(para)
            sentences = [s for s in SENTENCE_SPLIT.split(narration) if s.strip()]
            if len(sentences) >= 3:
                avg = sum(_count_words(s) for s in sentences) / len(sentences)
                if avg > 30:
                    findings.append({
                        "scene": sc.index,
                        "line": sc.start_line + _line_offset(sc.text, para),
                        "kind": "long-sentence paragraph",
                        "detail": f"avg sentence length {avg:.0f} words",
                    })
                    flags.append(Flag(
                        "over-explaining",
                        "Paragraph averages 30+ word sentences; check if the reader needs all of it.",
                        sc.start_line + _line_offset(sc.text, para),
                    ))
                # repeated-idea sentences within one paragraph
                for a, b in zip(sentences, sentences[1:]):
                    if _content_overlap(a, b) >= 0.6:
                        findings.append({
                            "scene": sc.index,
                            "line": sc.start_line + _line_offset(sc.text, para),
                            "kind": "repeated idea",
                            "detail": "consecutive sentences heavily overlap",
                        })
                        flags.append(Flag(
                            "over-explaining",
                            "Consecutive sentences say nearly the same thing; consider cutting one.",
                            sc.start_line + _line_offset(sc.text, para),
                        ))
            lower = narration.lower()
            for filler in fillers:
                if filler in lower:
                    findings.append({
                        "scene": sc.index,
                        "line": sc.start_line + _line_offset(sc.text, para),
                        "kind": "exposition filler",
                        "detail": filler,
                    })
                    flags.append(Flag(
                        "over-explaining",
                        f"Exposition filler in narration: \"{filler}\".",
                        sc.start_line + _line_offset(sc.text, para),
                    ))
    return findings


def _content_overlap(a: str, b: str) -> float:
    stops = {"a", "an", "the", "is", "was", "and", "of", "to", "in", "it", "that",
             "he", "she", "his", "her", "they", "them", "their", "with", "for",
             "on", "at", "as", "had", "have", "be", "not", "no"}
    words = [
        {w for w in WORD_RE.findall(s.lower()) if w not in stops and len(w) > 2}
        for s in (a, b)
    ]
    if not words[0] or not words[1]:
        return 0.0
    inter = len(words[0] & words[1])
    return inter / min(len(words[0]), len(words[1]))


def analyze(text: str) -> ChapterAnalysis:
    flags: list[Flag] = []
    stats = DialogueStats()
    scenes = []
    for idx, (start, sc_text, block) in enumerate(_split_scenes(text), start=1):
        dialogue_words = sum(
            _count_words(ln) for ln in block if DIALOGUE_LINE.match(ln)
        )
        scenes.append(Scene(
            index=idx,
            text=sc_text,
            words=sum(_count_words(ln) for ln in block),
            dialogue_words=dialogue_words,
            start_line=start,
        ))
        for ln in block:
            if DIALOGUE_LINE.match(ln):
                stats.dialogue_lines += 1
            if any(q in ln for q in '"\u201c\u201d'):
                _count_verb_tags(ln, stats)
        block_lines = sc_text.splitlines()
        for i, line in enumerate(block_lines):
            if not DIALOGUE_LINE.match(line) and line.strip():
                if _has_recent_dialogue(block_lines, i):
                    stats.action_beat_lines += 1

    filter_stats = count_word_stats(text, FILTER_WORDS, strip_quotes=True)
    weasel_stats = count_word_stats(text, WEASEL_WORDS, strip_quotes=True)
    _analyze_pacing(scenes, flags)
    scene_goals = _analyze_scene_goals(scenes, 1)
    over = _analyze_over_explaining(scenes, flags)

    total = sum(sc.words for sc in scenes)
    return ChapterAnalysis(
        total_words=total,
        scenes=scenes,
        flags=flags,
        filter_words=filter_stats,
        weasel_words=weasel_stats,
        dialogue=stats,
        scene_goals=scene_goals,
        over_explaining=over,
    )


def _has_recent_dialogue(block: list[str], idx: int) -> bool:
    """A narration line is an 'action beat' if it sits inside a run of dialogue."""
    prev_d = any(DIALOGUE_LINE.match(block[j]) for j in range(max(0, idx - 2), idx))
    next_d = any(DIALOGUE_LINE.match(block[j]) for j in range(idx + 1, min(len(block), idx + 3)))
    return prev_d and next_d
