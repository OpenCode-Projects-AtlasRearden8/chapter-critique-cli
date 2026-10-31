"""Deterministic (offline) chapter analysis.

Purely statistical heuristics, no LLM required:
  * pacing flags (scene length swings, long paragraphs)
  * filter-word counts with locations
  * weasel-word counts with locations
  * dialogue-tag repetition and adverb-stuffed tags
  * scene-goal clarity signals
  * over-explaining / repeated-idea detection

These numbers are also fed to the LLM so its narrative critique is
grounded in the chapter's real data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- word lists (kept simple and editable; they live in code so the CLI
# works with zero configuration) ---

FILTER_WORDS = [
    "felt", "seemed", "wondered", "realized", "noticed", "watched",
    "saw", "heard", "could feel", "could see", "could hear", "thought",
    "knew", "began to", "started to", "decided", "looked like",
    "sounded like", "remembered", "imagined", "realised",
]

WEASEL_WORDS = [
    "very", "really", "quite", "somewhat", "rather", "just", "simply",
    "basically", "actually", "literally", "kind of", "sort of", "almost",
    "nearly", "virtually", "definitely", "probably", "maybe", "fairly",
    "extremely", "totally", "absolutely", "suddenly", "somehow",
    "certainly", "obviously", "essentially",
]

PLAIN_TAGS = {"said", "asked", "answered", "replied"}
FANCY_TAGS = {
    "whispered", "shouted", "yelled", "hissed", "growled", "muttered",
    "murmured", "snapped", "gasped", "chuckled", "laughed", "cried",
    "drawled", "breathed", "sighed", "grunted", "croaked", "bellowed",
    "shrilled", "whined", "declared", "retorted", "exclaimed",
    "elaborated", "articulated", "queried",
}

INTENT_MARKERS = [
    "wanted to", "needed to", "had to", "must ", "was going to",
    "planned to", "hoped to", "decided to", "intended", "goal",
    "tried to", "had to find", "looking for", "searched for",
]

CONFLICT_MARKERS = [
    "but", "however", "couldn't", "wouldn't", "shouldn't", "unless",
    "refused", "balked", "blocked", "stalled", "failed", "wrong",
    "danger", "trouble", "argument", "against", "instead", "trapped",
]


@dataclass
class Scene:
    index: int          # 1-based
    text: str
    words: int
    dialogue_words: int
    start_line: int     # 1-based line number in the chapter file

    @property
    def dialogue_ratio(self) -> float:
        return self.dialogue_words / self.words if self.words else 0.0


@dataclass
class Flag:
    kind: str            # e.g. "pacing", "filter-words"
    detail: str
    line: int | None = None


@dataclass
class WordStat:
    word: str
    count: int
    lines: list[int] = field(default_factory=list)


@dataclass
class DialogueStats:
    tag_counts: dict[str, int] = field(default_factory=dict)
    plain_count: int = 0
    fancy_count: int = 0
    action_beat_lines: int = 0
    dialogue_lines: int = 0
    adverb_tags: list[str] = field(default_factory=list)


@dataclass
class ChapterAnalysis:
    total_words: int
    scenes: list[Scene]
    flags: list[Flag]
    filter_words: list[WordStat]
    weasel_words: list[WordStat]
    dialogue: DialogueStats
    scene_goals: list[dict]
    over_explaining: list[dict]

    def per_1000(self, count: int) -> float:
        if not self.total_words:
            return 0.0
        return round(1000 * count / self.total_words, 1)
