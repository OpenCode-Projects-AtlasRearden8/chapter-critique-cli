"""chapter-critique command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .__init__ import __version__
from .analyzer import analyze
from .config import load_config, load_rubric, write_default_config, write_default_rubric
from .critique import run_critique
from .llm import OpenAICompatibleClient


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chapter-critique",
        description=(
            "Manuscript-first-draft helper: feed a chapter file, get a "
            "structured critique from any OpenAI-compatible endpoint "
            "(incl. local Ollama). No API keys."
        ),
    )
    p.add_argument("chapter", nargs="?", help="path to the chapter file (txt/md)")
    p.add_argument("-o", "--output", help="write critique markdown here (default: stdout)")
    p.add_argument("-c", "--config", help="path to config.toml (optional)")
    p.add_argument("-r", "--rubric", help="path to rubric.toml (default: built-in rubric)")
    p.add_argument("--no-llm", action="store_true",
                   help="stats-only critique; skip the LLM endpoint entirely")
    p.add_argument("--init", action="store_true",
                   help="write a starter config.toml and rubric.toml here and exit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _read_chapter(path: str) -> str:
    fp = Path(path)
    if not fp.is_file():
        sys.stderr.write(f"chapter file not found: {path}\n")
        raise SystemExit(1)
    text = fp.read_text(encoding="utf-8")
    if not text.strip():
        sys.stderr.write(f"chapter file is empty: {path}\n")
        raise SystemExit(1)
    return text


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.init:
        write_default_config(args.config or "config.toml")
        write_default_rubric(args.rubric or "rubric.toml")
        print("Wrote config.toml and rubric.toml - edit them freely.")
        return 0

    if not args.chapter:
        build_parser().print_help()
        return 1

    chapter = _read_chapter(args.chapter)
    analysis = analyze(chapter)
    rubric = load_rubric(args.rubric)

    llm = None
    if not args.no_llm:
        cfg = load_config(args.config)
        llm = OpenAICompatibleClient(
            base_url=cfg.endpoint.base_url,
            model=cfg.endpoint.model,
            temperature=cfg.critique.temperature,
            max_tokens=cfg.critique.max_tokens,
        )

    try:
        _analysis, critique = run_critique(
            chapter, llm,
            analysis=analysis, rubric=rubric, config=load_config(args.config) if llm else None,
        )
    except RuntimeError as err:
        if args.output:
            # save the measured stats so the run wasn't wasted
            from .critique import _stats_only_critique
            Path(args.output).write_text(
                _stats_only_critique(analysis) + "\n", encoding="utf-8"
            )
        sys.stderr.write(f"error: {err}\n")
        return 2
    if args.output:
        Path(args.output).write_text(critique + "\n", encoding="utf-8")
        print(f"Critique written to {args.output}")
    else:
        print(critique)
    return 0


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()
