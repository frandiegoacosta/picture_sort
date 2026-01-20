from pathlib import Path
from exif import Image
import argparse
import os


def get_creation_time(path: str):
    with open(path, "rb") as file:
        img = Image(file)
        if img.has_exif:
            ctime = img.datetime_original
            if isinstance(ctime, str):
                return ctime.replace(":", "-").replace(" ", "-")


def already_named(key: str):
    key_date = key.split("_")[0].replace("-", "")
    return key_date.isdigit() and len(key_date) == 24


def get_key_extension(file: Path):
    file = Path(file)
    if file.is_file():
        return file.name.split(".")
    return None, None


def file_name(file: Path):
    key, extension = get_key_extension(file)
    if key and extension:
        if not already_named(key):
            if extension.lower() == "jpg":
                ctime = get_creation_time(str(file))
                return (key, ctime)


def set_file_name(file: Path, file_dict: dict):
    key, extension = get_key_extension(file)
    if key and extension:
        if ctime := file_dict.get(key):
            new_filename = ctime + "_" + key + "." + extension
            return (str(file), os.path.join(file.parent, new_filename))


def main(path: str):
    file_dict = dict(filter(bool, map(file_name, Path(path).iterdir())))
    move_dict = dict(
        filter(bool, map(lambda i: set_file_name(i, file_dict), Path(path).iterdir()))
    )
    for k, v in move_dict.items():
        Path(k).rename(v)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rename JPG files in a directory based on EXIF date.",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Path to the directory containing files to rename",
    )
    args = parser.parse_args()
    main(args.path)
