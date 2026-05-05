"""Question-only CLI for picture_sort. No flags, no subcommands."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import prompts
from .executor import LOG_DIR_NAME, ExecutionResult, apply_plan
from .executor import undo as undo_log
from .planner import build_plan


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _format_summary(result: ExecutionResult, skipped) -> str:
    counts = Counter(s.reason for s in skipped)
    detail = ", ".join(f"{r.value}={n}" for r, n in counts.items()) or "none"
    return (
        f"renamed={len(result.renamed)} "
        f"failed={len(result.failed)} "
        f"skipped={sum(counts.values())} ({detail})"
    )


def _run_once(root: Path, recursive: bool) -> ExecutionResult:
    plan = build_plan(root, recursive=recursive)
    result = apply_plan(plan, root)
    line = _format_summary(result, plan.skipped)
    if result.failed:
        prompts.warn(line)
    else:
        prompts.success(line)
    if result.log_path is not None:
        prompts.info(f"log: {result.log_path}")
    return result


def _do_rename() -> int:
    raw = prompts.ask_path("Folder with photos:")
    if not raw:
        prompts.error("aborted")
        return 1
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        prompts.error(f"Not a directory: {root}")
        return 2

    recursive = prompts.ask_recursive()
    return 1 if _run_once(root, recursive=recursive).failed else 0


def _format_log_label(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return path.name
    when = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{when}   {path.name}"


def _do_undo() -> int:
    raw = prompts.ask_path(
        "Folder where the renames happened (we'll look for its log directory):"
    )
    if not raw:
        prompts.error("aborted")
        return 1
    root = Path(raw).expanduser().resolve()
    log_dir = root / LOG_DIR_NAME
    if not log_dir.is_dir():
        prompts.error(f"No log directory at {log_dir}")
        return 2

    logs = sorted(log_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        prompts.error(f"No logs found in {log_dir}")
        return 2

    labels = [(_format_log_label(p), str(p)) for p in logs]
    chosen = prompts.ask_log_choice(labels)
    if not chosen:
        prompts.error("aborted")
        return 1

    result = undo_log(Path(chosen))
    line = f"reverted={len(result.renamed)} failed={len(result.failed)}"
    if result.failed:
        prompts.warn(line)
    else:
        prompts.success(line)
    return 1 if result.failed else 0


def main() -> int:
    _setup_logging()
    prompts.banner()
    action = prompts.ask_action()
    if action in (None, prompts.ACTION_CANCEL):
        prompts.info("bye")
        return 0
    if action == prompts.ACTION_RENAME:
        return _do_rename()
    if action == prompts.ACTION_UNDO:
        return _do_undo()
    prompts.error(f"unknown action: {action}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
