import io
import mimetypes
from pathlib import Path
from typing import Any

from mutagen import MutagenError
from mutagen.mp4 import MP4, MP4Tags
from PIL import Image

from lib2opds.formats import EbookFile


class M4bFile(EbookFile):
    mimetype: str = "audio/x-m4b"
    metadata_quality_score: int = 1

    def read(self) -> bool:
        try:
            f = MP4(self.fpath)
            meta: MP4Tags = f.tags
        except MutagenError:
            return False
        if authors := meta.get("\xa9ART", None):
            self._metadata_file.authors = authors[0].split(";")
        if title := meta.get("\xa9alb", None):
            self._metadata_file.title = title[0]
        if desc := meta.get("desc", None):
            self._metadata_file.description = desc[0]
        if cprt := meta.get("cprt", None):
            self._metadata_file.publisher = cprt[0]
        if (cover_data := meta.get("covr", None)) and not self._cover_file.cover:
            try:
                im: Image.Image = Image.open(io.BytesIO(cover_data[0]))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                self._cover_file.cover = im
                self._cover_file.cover_mimetype = "image/jpeg"
            except:
                print(f"Can't convert cover for {self.fpath}")
                return False
        return True
