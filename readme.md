# Picture Sort

A small Python CLI that renames JPEG files in a folder by prefixing each filename with the photo’s capture time from EXIF. The goal is chronological sorting on disk without moving files to subfolders.

## What it does

1. Asks you for a **folder path** (interactive prompt).
2. Resolves that path: **`~` is expanded** to your home directory, and the path is made **absolute** (`expanduser` + `resolve`).
3. Looks at **regular files only** whose extension is **`.jpg`**, **`.jpeg`**, or **`.jpe`** (case-insensitive).
4. For each of those files, reads EXIF. If **`datetime_original`** is present and is a **string**, it is normalized for use in a filename (`:` → `-`, space → `-`).
5. **Renames** the file to:

   `{normalized_datetime}{original_stem}{original_suffix}`

   Example: `DSCF1274.jpeg` with `datetime_original` `2024:01:15 14:30:45` becomes something like:

   `2024-01-15-14-30-45DSCF1274.jpeg`

6. Files **without** usable EXIF for that field are **left unchanged** (they never get a `None` prefix in the name).

Non-JPEG files in the same folder are ignored. The script only renames inside the directory you chose (no recursion).

## Requirements

- Python 3.12+
- Dependencies are declared in `pyproject.toml`; for a minimal run of `main.py` you need **`exif`** (metadata) and **`questionary`** (path prompt). Install everything the project pins with:

  ```bash
  uv sync
  ```

## Usage

From the project root:

```bash
uv run python main.py
```

You will be prompted: **Path Picture folder**. Enter a path, for example:

- `/Users/you/Pictures/vacation`
- `~/Pictures/vacation` (tilde is expanded)

Confirm with Enter. The tool then applies the renames described above.

## Behaviour details

| Topic | Behaviour |
|--------|-----------|
| EXIF field used | `datetime_original` only, and only when it is a `str` |
| Extensions | `.jpg`, `.jpeg`, `.jpe` |
| Key used for matching | `Path.stem` (filename without last extension), so names with extra dots in the stem are handled consistently |
| Collisions / errors | `rename` failures are caught, logged at INFO, and skipped (no crash) |
| Backup | Renaming is in-place; keep a backup if the folder is irreplaceable |

## Limitations

- No subfolders: only the **top-level** of the chosen directory.
- No detection of “already date-prefixed” names; running again on already-renamed files will **prepend another** timestamp unless you change the code.
- Cameras that omit `datetime_original` or expose it in a non-string form are not supported by the current reader logic.
