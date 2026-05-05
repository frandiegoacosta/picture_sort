"""Build a rename plan from a directory of photos."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

from .metadata import (
    JPEG_SUFFIXES,
    PHOTO_SUFFIXES,
    PhotoInfo,
    read_taken_at,
)

# A filename whose stem matches this is considered already processed and
# is left alone. The trailing underscore matches our format
# `<timestamp>_<original_stem>`. This is what makes the tool idempotent.
PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})_(.+)$")


class SkipReason(str, Enum):
    NOT_PHOTO = "not_photo"
    ALREADY_PREFIXED = "already_prefixed"
    NO_EXIF = "no_exif"
    NAME_UNCHANGED = "name_unchanged"
    DEST_EXISTS = "dest_exists"
    DEST_DUPLICATE = "dest_duplicate"


@dataclass(frozen=True)
class RenamePlan:
    src: Path
    dst: Path
    source_field: str


@dataclass(frozen=True)
class SkippedFile:
    src: Path
    reason: SkipReason
    detail: str = ""


@dataclass
class Plan:
    renames: list[RenamePlan] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)


def _format_prefix(info: PhotoInfo) -> str:
    return info.taken_at.strftime("%Y-%m-%d-%H-%M-%S")


def _original_stem(stem: str) -> str:
    """Return the part of `stem` after the timestamp prefix, if any."""
    m = PREFIX_RE.match(stem)
    return m.group(2) if m else stem


def _iter_files(root: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for p in root.rglob("*"):
            if p.is_file():
                yield p
    else:
        for p in root.iterdir():
            if p.is_file():
                yield p


def build_plan(root: Path, recursive: bool = False) -> Plan:
    """Inspect `root` and produce the full set of renames + skipped files.

    Two passes:

    1. Read EXIF from every JPEG and index its timestamp under both the
       file's current stem and (if already prefixed) its original stem.
       Indexing is per-folder and case-insensitive so that raw siblings
       can find their JPEG even after a previous run renamed it.
    2. For every photo (JPEG or raw), build the rename plan. Raws look up
       their timestamp in the JPEG index from step 1.
    """
    plan = Plan()
    used_dests: dict[Path, Path] = {}

    files = list(_iter_files(root, recursive))

    info_by_path: dict[Path, PhotoInfo] = {}
    sibling_index: dict[Path, dict[str, PhotoInfo]] = {}
    for path in files:
        if path.suffix.lower() not in JPEG_SUFFIXES:
            continue
        info = read_taken_at(path)
        if info is None:
            continue
        info_by_path[path] = info
        bucket = sibling_index.setdefault(path.parent, {})
        bucket[path.stem.lower()] = info
        bucket.setdefault(_original_stem(path.stem).lower(), info)

    for path in files:
        suffix = path.suffix.lower()
        if suffix not in PHOTO_SUFFIXES:
            plan.skipped.append(SkippedFile(path, SkipReason.NOT_PHOTO))
            continue
        if PREFIX_RE.match(path.stem):
            plan.skipped.append(SkippedFile(path, SkipReason.ALREADY_PREFIXED))
            continue

        if suffix in JPEG_SUFFIXES:
            info = info_by_path.get(path)
        else:
            info = sibling_index.get(path.parent, {}).get(path.stem.lower())

        if info is None:
            plan.skipped.append(SkippedFile(path, SkipReason.NO_EXIF))
            continue

        new_name = f"{_format_prefix(info)}_{path.stem}{path.suffix}"
        dst = path.with_name(new_name)

        if dst == path:
            plan.skipped.append(SkippedFile(path, SkipReason.NAME_UNCHANGED))
            continue
        if dst in used_dests:
            plan.skipped.append(
                SkippedFile(
                    path,
                    SkipReason.DEST_DUPLICATE,
                    detail=f"clashes with {used_dests[dst]}",
                )
            )
            continue
        if dst.exists():
            plan.skipped.append(
                SkippedFile(path, SkipReason.DEST_EXISTS, detail=str(dst))
            )
            continue

        used_dests[dst] = path
        plan.renames.append(
            RenamePlan(src=path, dst=dst, source_field=info.source_field)
        )

    return plan
