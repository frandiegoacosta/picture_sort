from pathlib import Path
from exif import Image
import questionary
import logging
import os

_JPEG_SUFFIXES = frozenset({".jpg", ".jpeg", ".jpe"})


def _is_jpeg(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _JPEG_SUFFIXES


class PictureSort:

    @staticmethod
    def get_creation_time(path: Path):
        with open(path, "rb") as file:
            img = Image(file)
            if img.has_exif:
                ctime = img.datetime_original
                if isinstance(ctime, str):
                    return ctime.replace(":", "-").replace(" ", "-")

    @classmethod
    def key_time_map(cls, path: str):
        ls = Path(path).iterdir()
        ls = filter(_is_jpeg, ls)
        ls = map(lambda i: (i.stem, cls.get_creation_time(i)), ls)
        ls = filter(lambda i: bool(i[-1]), ls)
        return dict(ls)

    @classmethod
    def move_files_map(cls, path: str):
        key_time_map = cls.key_time_map(path)
        ls = Path(path).iterdir()
        ls = filter(_is_jpeg, ls)
        ls = map(
            lambda p: (
                p,
                key_time_map.get(p.stem),
            ),
            ls,
        )
        ls = filter(lambda item: item[1] is not None, ls)
        ls = map(
            lambda item: (
                str(item[0]),
                os.path.join(
                    item[0].parent,
                    f"{item[1]}{item[0].stem}{item[0].suffix.lower()}",
                ),
            ),
            ls,
        )
        return dict(ls)

    @classmethod
    def run(cls, path: str):
        path = str(Path(path).expanduser().resolve())
        move_files_map = cls.move_files_map(path)
        for k, v in move_files_map.items():
            try:
                Path(k).rename(v)    
            except Exception as e: 
                logging.info(str(e))
                pass

if __name__ == "__main__":
    path = questionary.path("Path Picture folder").ask()
    PictureSort.run(str(path))
