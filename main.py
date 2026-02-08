from pathlib import Path
from exif import Image
import questionary
import logging
import os

class PictureSort:

    @staticmethod
    def get_creation_time(path: str):
        with open(path, "rb") as file:
            img = Image(file)
            if img.has_exif:
                ctime = img.datetime_original
                if isinstance(ctime, str):
                    return ctime.replace(":", "-").replace(" ", "-")

    @classmethod
    def key_time_map(cls, path: str):
        ls = Path(path).iterdir()
        ls = filter(lambda i: hasattr(i, 'name'), ls)
        ls = filter(lambda i: str(str(i.name).split('.')[-1]).lower() == 'jpg', ls)
        ls = map(lambda i: (str(i.name).split('.')[0], cls. get_creation_time(i)), ls)
        ls = filter(lambda i: bool(i[-1]), ls)
        return dict(ls)

    @classmethod
    def move_files_map(cls, path: str):
        key_time_map = cls.key_time_map(path)
        ls = Path(path).iterdir()
        ls = filter(lambda i: hasattr(i, 'name'), ls)
        ls = filter(lambda i: hasattr(i, 'parent'), ls)
        ls = map(lambda i: (i, str(i.name).split('.')), ls)
        ls = map(lambda i: list(i) + [key_time_map.get(i[1][0])], ls)
        ls = map(lambda i: (i[0], [i[2]] + [i[1][0]] + ['.'] + [i[1][-1]]), ls)
        ls = map(lambda i: (i[0], ''.join(map(str,i[1]))), ls)
        ls = map(lambda i: (str(i[0]),  os.path.join(i[0].parent, i[1])), ls)
        return dict(ls)

    @classmethod
    def run(cls, path: str):
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
