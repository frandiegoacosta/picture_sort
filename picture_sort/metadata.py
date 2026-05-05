"""Read capture timestamps from image EXIF metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from exif import Image

log = logging.getLogger(__name__)

JPEG_SUFFIXES = frozenset({".jpg", ".jpeg", ".jpe"})

# Camera raw formats. We cannot read EXIF from these with the `exif`
# package, so the planner will pair each raw with a sibling JPEG (same
# folder, same stem) and reuse that JPEG's timestamp.
RAW_SUFFIXES = frozenset(
    {
        ".raf",
        ".cr2",
        ".cr3",
        ".nef",
        ".nrw",
        ".arw",
        ".srf",
        ".sr2",
        ".dng",
        ".orf",
        ".rw2",
        ".pef",
        ".srw",
        ".rwl",
        ".x3f",
        ".3fr",
    }
)

PHOTO_SUFFIXES = JPEG_SUFFIXES | RAW_SUFFIXES

# EXIF datetime fields, queried in priority order. The exif package exposes
# them as snake_case attributes on Image.
DATETIME_FIELDS: tuple[str, ...] = (
    "datetime_original",
    "datetime_digitized",
    "datetime",
)

_EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"


@dataclass(frozen=True)
class PhotoInfo:
    path: Path
    taken_at: datetime
    source_field: str


def _parse_exif_datetime(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), _EXIF_FORMAT)
    except (ValueError, AttributeError):
        return None


def read_taken_at(path: Path) -> PhotoInfo | None:
    """Return the earliest available EXIF capture time for `path`, or None.

    Falls back through DateTimeOriginal -> DateTimeDigitized -> DateTime so
    that cameras which only populate one of those still produce a timestamp.
    """
    try:
        with path.open("rb") as fh:
            img = Image(fh)
    except (OSError, ValueError) as exc:
        log.debug("could not open %s as image: %s", path, exc)
        return None

    if not getattr(img, "has_exif", False):
        return None

    for field in DATETIME_FIELDS:
        value = getattr(img, field, None)
        if not isinstance(value, str):
            continue
        parsed = _parse_exif_datetime(value)
        if parsed is not None:
            return PhotoInfo(path=path, taken_at=parsed, source_field=field)

    return None
