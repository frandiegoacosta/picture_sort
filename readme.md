# picture_sort

Rename JPEG files in a folder so each filename starts with the photo's EXIF capture time. The goal is reliable chronological ordering on disk without moving files into subfolders.

## Safety guarantees

The tool is built so a picture is never lost:

- **Plan first, apply second.** Every run first builds a complete plan and only mutates files after the plan has been built and validated (collision detection, idempotency check, EXIF check).
- **No silent overwrites.** Renames go through `os.link` (atomic, fails if the destination already exists) followed by `os.unlink` of the source. The original is removed only after the destination is confirmed in place at the same size. The worst case is a duplicate file, never a deletion.
- **Works on camera cards.** FAT32 / exFAT volumes (typical SD cards) don't support hard links, so on those volumes the tool falls back to a copy-then-verify-then-delete pattern with the same invariant: the source is removed only after the destination has been written and its size has been verified. A partial copy is cleaned up automatically if anything goes wrong mid-write.
- **Idempotent.** Filenames that already start with a `YYYY-MM-DD-HH-MM-SS` prefix are skipped, so re-running the tool is a no-op.
- **Per-run JSON log + undo.** Each successful run writes a log under `<folder>/.picture_sort/<timestamp>.json`. The undo flow lets you pick one of those logs and reverses it using the same safe-move primitive.

## Requirements

- Python 3.12+
- `uv` on `PATH`
- Runtime dependencies (already in `pyproject.toml`): `exif`, `questionary`.

## Usage

There is exactly one command, and it takes no arguments:

```bash
./picture-sort
```

You'll be guided through a short set of coloured questions. Nothing is ever passed on the command line.

### Rename flow

1. **What do you want to do?** → *Rename JPEGs in a folder*
2. **Folder with photos** (`~` is expanded; the path is resolved to an absolute path)
3. **Recurse into subfolders?** (default: no)

The renames are applied immediately using the safe-move primitive. If anything goes wrong, use the undo flow.

### Undo flow

1. **What do you want to do?** → *Undo a previous run*
2. **Folder where the renames happened** — the tool looks for its `.picture_sort/` directory inside.
3. **Which run do you want to undo?** — pick a log file from the list (newest first).

The undo reverses the chosen log entry by entry, in reverse order, using the same safe-move primitive — it will refuse to overwrite anything that's already back in place.

## How it works

1. **Scan** the chosen directory (top-level by default, or recursive if you said yes) for photo files. Two families are recognised (suffix match is case-insensitive):
   - **JPEG**: `.jpg`, `.jpeg`, `.jpe`
   - **Camera raw**: `.raf` (Fujifilm), `.cr2`/`.cr3` (Canon), `.nef`/`.nrw` (Nikon), `.arw`/`.srf`/`.sr2` (Sony), `.dng`, `.orf` (Olympus), `.rw2` (Panasonic), `.pef` (Pentax), `.srw` (Samsung), `.rwl` (Leica), `.x3f` (Sigma), `.3fr` (Hasselblad).
2. **Skip already-renamed files.** Anything whose stem matches `^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_` is left alone. This is what makes the tool safe to re-run.
3. **Read EXIF for JPEGs**, trying these fields in order:
   1. `DateTimeOriginal`
   2. `DateTimeDigitized`
   3. `DateTime` (modify time)

   The first one that parses as `YYYY:MM:DD HH:MM:SS` wins.
4. **Borrow timestamps for raw files.** Raw containers usually don't expose EXIF the way JPEG does, so each raw is paired with a sibling JPEG that has the **same stem** in the **same folder** (case-insensitive). The pairing also works after a previous run renamed the JPEG: indexing keeps both the current stem (`2026-06-27-20-30-38_DSCF1519`) and the original stem (`DSCF1519`), so a freshly downloaded `DSCF1519.RAF` still finds its already-prefixed JPEG sibling. A raw with no sibling JPEG is left unchanged (`no_exif`).
5. **Plan a rename** of `STEM.EXT` to `YYYY-MM-DD-HH-MM-SS_STEM.EXT`. The original suffix case is preserved (`.RAF` stays `.RAF`).
5. **Validate the plan.** Any of these reasons cause a file to be skipped (and reported in the summary):
   - `not_photo` — wrong extension or not a regular file
   - `already_prefixed` — stem already starts with the timestamp shape
   - `no_exif` — none of the EXIF datetime fields were usable
   - `dest_exists` — the target name already exists on disk
   - `dest_duplicate` — two source files map to the same target name
   - `name_unchanged` — the rename would be a no-op
6. **Apply** with the safe-move pattern: try `os.link` first, fall back to `shutil.copy2` on filesystems that don't support hard links (FAT32 / exFAT, SMB, some FUSE mounts), verify the destination size matches, and only then `os.unlink` the source. A JSON log of all successful renames is written to `<folder>/.picture_sort/<timestamp>.json`.

End-of-run summary line, e.g.:

```
renamed=12 failed=0 skipped=4 (not_photo=2, no_exif=1, already_prefixed=1)
log: /Users/you/Pictures/MyAlbum/.picture_sort/20260505-124824.json
```

## Project layout

```
picture_sort/
  __init__.py     version
  metadata.py     EXIF reader with fallback chain
  planner.py      builds Plan(renames=[...], skipped=[...])
  executor.py     safe-move (os.link + os.unlink) + JSON log + undo
  prompts.py      styled questionary widgets
  cli.py          fully interactive entry: rename / undo / cancel (no flags)
main.py           thin python entry: from picture_sort.cli import main
picture-sort      shell wrapper: uv run --no-sync python main.py
```

## Limitations / known gaps

- HEIC is not supported yet (no sidecar pairing rule).
- Raw files require a sibling JPEG with the same stem to get a timestamp. If you shoot raw-only, those files will be skipped with `no_exif` until a JPEG sibling exists.
- JPEG EXIF must be present and parseable; cameras that store dates only in proprietary makernotes are not supported.
- The tool only renames; it does not move files into date-based subfolders.
