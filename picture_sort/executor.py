"""Apply a rename plan and persist an undo log.

Renames are designed so a picture is never lost:

- The destination is never silently overwritten — we refuse to start if
  it already exists.
- We try `os.link` first (atomic, fails if the destination exists). On
  filesystems that don't support hard links (FAT/exFAT camera cards,
  SMB shares, some FUSE mounts) we fall back to a copy + verify pattern.
- In every case the source is removed only after the destination is
  confirmed in place at the same size. If anything goes wrong the worst
  case is a duplicate file, never a deletion.
"""

from __future__ import annotations

import errno
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .planner import Plan, RenamePlan

# Errno values that mean "this filesystem cannot create a hard link". When
# we see one of these we transparently fall back to copy + verify + unlink.
_LINK_UNSUPPORTED_ERRNOS = {
    getattr(errno, "ENOTSUP", -1),
    getattr(errno, "EOPNOTSUPP", -1),
    errno.EXDEV,
}

log = logging.getLogger(__name__)

LOG_DIR_NAME = ".picture_sort"


@dataclass
class ExecutionResult:
    renamed: list[RenamePlan] = field(default_factory=list)
    failed: list[tuple[RenamePlan, str]] = field(default_factory=list)
    log_path: Path | None = None


def _safe_move(src: Path, dst: Path) -> None:
    """Move `src` to `dst` without ever risking data loss.

    Strategy:
      1. Refuse if `dst` already exists.
      2. Try `os.link` (atomic, no copy). If the filesystem doesn't
         support hard links, fall back to `shutil.copy2`.
      3. Verify the destination exists and has the same size as the
         source before removing the source.
      4. If verification fails the source stays put and the partial
         destination (if any) is cleaned up.
    """
    if dst.exists():
        raise FileExistsError(f"destination already exists: {dst}")

    src_size = src.stat().st_size

    try:
        os.link(src, dst)
    except OSError as exc:
        if exc.errno in _LINK_UNSUPPORTED_ERRNOS:
            log.debug(
                "hard link unsupported on %s (errno %s); falling back to copy",
                dst.parent,
                exc.errno,
            )
            _safe_copy(src, dst, src_size)
            return
        raise

    try:
        dst_stat = dst.stat()
    except OSError:
        raise

    if dst_stat.st_size != src_size:
        raise OSError(
            f"size mismatch after linking ({src_size} vs {dst_stat.st_size}); "
            f"source kept at {src}"
        )

    os.unlink(src)


def _safe_copy(src: Path, dst: Path, src_size: int) -> None:
    """Copy `src` to `dst`, verify, then remove `src`.

    Used when hard links aren't supported. Same invariant as `_safe_move`:
    the source is unlinked only after the destination has been verified.
    A partial destination is cleaned up if the copy or verification fails.
    """
    try:
        shutil.copy2(src, dst)
    except OSError:
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                log.warning("could not clean up partial copy at %s", dst)
        raise

    try:
        dst_size = dst.stat().st_size
    except OSError:
        raise

    if dst_size != src_size:
        try:
            dst.unlink()
        except OSError:
            log.warning("could not clean up partial copy at %s", dst)
        raise OSError(
            f"size mismatch after copying ({src_size} vs {dst_size}); "
            f"source kept at {src}"
        )

    os.unlink(src)


def apply_plan(plan: Plan, root: Path) -> ExecutionResult:
    """Execute `plan`. Uses the safe-move primitive for every rename."""
    result = ExecutionResult()

    for item in plan.renames:
        try:
            _safe_move(item.src, item.dst)
        except OSError as exc:
            log.warning("rename failed %s -> %s: %s", item.src, item.dst, exc)
            result.failed.append((item, str(exc)))
            continue
        log.info("%s -> %s", item.src.name, item.dst.name)
        result.renamed.append(item)

    if result.renamed:
        result.log_path = _write_log(root, result.renamed)

    return result


def _write_log(root: Path, renamed: list[RenamePlan]) -> Path:
    log_dir = root / LOG_DIR_NAME
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"{stamp}.json"
    payload = {
        "root": str(root),
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "renames": [
            {
                "src": str(item.src),
                "dst": str(item.dst),
                "source": item.source_field,
            }
            for item in renamed
        ],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def undo(log_file: Path) -> ExecutionResult:
    """Reverse the renames recorded in `log_file`.

    Iterates in reverse order so any chained renames within a single run
    are unwound from the most recent backwards. Uses the same safe-move
    primitive, so undoing also never overwrites or deletes blindly.
    """
    data = json.loads(log_file.read_text())
    entries = data.get("renames", [])

    result = ExecutionResult(log_path=log_file)
    for entry in reversed(entries):
        current = Path(entry["dst"])
        original = Path(entry["src"])
        item = RenamePlan(
            src=current,
            dst=original,
            source_field=entry.get("source", ""),
        )
        try:
            if not current.exists():
                raise FileNotFoundError(f"{current} no longer exists")
            _safe_move(current, original)
        except OSError as exc:
            log.warning("undo failed %s -> %s: %s", current, original, exc)
            result.failed.append((item, str(exc)))
            continue
        log.info("undo %s -> %s", current.name, original.name)
        result.renamed.append(item)

    return result
