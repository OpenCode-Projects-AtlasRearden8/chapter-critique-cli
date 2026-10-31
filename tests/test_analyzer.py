"""Tests for the deterministic analysis engine."""

from __future__ import annotations

from chapter_critique.analyzer import analyze, _strip_dialogue
from chapter_critique.textstats import ChapterAnalysis


def _analyze(text):
    return analyze(text)


# --- filter words -------------------------------------------------------

def test_filter_words_counted(chapter_text):
    result = _analyze(chapter_text)
    words = {s.word: s.count for s in result.filter_words}
    assert words["felt"] == 1
    assert words["wondered"] == 1
    assert words["realized"] == 1
    assert words["seemed"] == 2


def test_filter_words_exclude_dialogue():
    text = '"I felt it," she said.\nBut the floor was cold anyway.'
    result = _analyze(text)
    felt = [s for s in result.filter_words if s.word == "felt"]
    assert felt == []  # dialogue-only filter words are skipped


def test_filter_word_lines_recorded(chapter_text):
    result = _analyze(chapter_text)
    felt = next(s for s in result.filter_words if s.word == "felt")
    assert felt.lines, "line numbers must be recorded"


def test_per_1000(chapter_text):
    result = _analyze(chapter_text)
    assert result.per_1000(0) == 0.0
    assert result.per_1000(result.total_words) == 1000.0


# --- weasel words -------------------------------------------------------

def test_weasel_words_counted(chapter_text):
    result = _analyze(chapter_text)
    words = {s.word: s.count for s in result.weasel_words}
    assert words["very"] == 1
    assert words["suddenly"] == 1
    assert words["somehow"] == 2
    assert words["probably"] == 1


def test_multiword_weasel_phrase():
    result = _analyze("It was kind of strange. Kind of strange, she said")
    phrase = next(s for s in result.weasel_words if s.word == "kind of")
    assert phrase.count == 2


# --- dialogue tags ------------------------------------------------------

def test_dialogue_tags_simple(chapter_text):
    d = _analyze(chapter_text).dialogue
    assert d.tag_counts.get("said") == 4
    assert d.tag_counts.get("shouted") == 1
    assert d.plain_count + d.fancy_count == sum(d.tag_counts.values())


def test_adverb_tag_detected():
    text = '"Move now," she said quietly.'
    d = _analyze(text).dialogue
    assert "said quietly" in d.adverb_tags


def test_plain_vs_fancy_split():
    text = '"Hi," he said. "Fine," she whispered.'
    d = _analyze(text).dialogue
    assert d.plain_count == 1
    assert d.fancy_count == 1


# --- pacing -------------------------------------------------------------


def test_long_scene_flagged():
    text = ("Marin walked. " * 1000) + "\n\n***\n\n" + '"Stop," she said.'
    result = _analyze(text)
    assert any(
        f.kind == "pacing" and "long" in f.detail.lower()
        for f in result.flags
    )


def test_thin_scene_flagged():
    text = '""Fine," she said.\n\n***\n\nA leaf fell and was gone and that was that and nothing more was said about it and the sun went down behind the roofline of the empty customs house.'
    result = _analyze(text)
    # second scene should be over min size; first scene (2 words) is thin
    assert any("thin" in f.detail for f in result.flags)


def test_scene_count(chapter_text):
    result = _analyze(chapter_text)
    assert len(result.scenes) == 2  # harbor+title; salt road/bell merged after ***


def test_scene_start_line_is_first_real_line(chapter_text):
    result = _analyze(chapter_text)
    assert result.scenes[0].start_line == 1
    assert result.scenes[1].start_line == 7  # *** on line 5, blank 6 skipped


def test_long_paragraph_flagged_line_number():
    sentence = (
        "She described the harbor that her grandfather had built for her "
        "family long ago, long before the riots. "
    )
    para = sentence * 13  # ~180 narration words in one paragraph
    text = para + "\n\n***\n\nLater she slept."
    result = _analyze(text)
    paced = [f for f in result.flags
             if f.kind == "pacing" and "narration" in f.detail.lower()]
    assert paced, result.flags
    assert paced[0].line is not None


# --- scene goals --------------------------------------------------------

def test_scene_goals_present(chapter_text):
    result = _analyze(chapter_text)
    assert result.scene_goals, "every scene gets a goal dict"
    scenes = {g["scene"]: g for g in result.scene_goals}
    assert any(g["goal"] in {"clear", "partial", "unclear"} for g in scenes.values())


def test_clear_scene():
    text = ("She needed to find the gold. But the guard blocked the door, "
            "and he refused to step aside.\n\n\"Move,\" she said.")
    result = _analyze(text)
    g = result.scene_goals[0]
    assert g["goal"] == "clear"
    assert g["intent_signals"] >= 1
    assert g["conflict_signals"] >= 1


def test_unclear_scene():
    text = "Morning came early. The kettle cooled on the stove."
    result = _analyze(text)
    assert result.scene_goals[0]["goal"] == "unclear"


# --- over-explaining ----------------------------------------------------

def test_repeated_idea_detected():
    text = ("The ledger proved the theft. The theft was proven by the "
            "ledger. The proofs were the coin the master stole weekly. "
            "The master stole coin weekly from the till.")
    result = _analyze(text)
    kinds = {o["kind"] for o in result.over_explaining}
    assert "repeated idea" in kinds


def test_exposition_filler_detected():
    text = "As you know, the harbor master took the ledger in the fall."
    result = _analyze(text)
    kinds = {o["kind"] for o in result.over_explaining}
    assert "exposition filler" in kinds


def test_over_explaining_flags_added():
    text = "As you know, the harbor master took the ledger in the fall."
    result = _analyze(text)
    assert any(f.kind == "over-explaining" for f in result.flags)


# --- misc ---------------------------------------------------------------

def test_strip_dialogue_blanks_speech_keeps_quotes():
    # quote marks stay so tag detection can find the tag tail
    assert _strip_dialogue('"felt very" she felt') == '"         " she felt'


def test_empty_chapter_is_safe():
    result = _analyze("")
    assert isinstance(result, ChapterAnalysis)
    assert result.total_words == 0
    assert result.per_1000(1) == 0.0


def test_word_stats_sorted_by_count():
    text = ("really very actually really really very\n\n" * 2)
    result = _analyze(text)
    top = result.weasel_words[0]
    assert top.word == "really"
    assert top.count == 6
