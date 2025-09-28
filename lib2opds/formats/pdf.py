import io
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import pypdf
from PIL import Image

from lib2opds.formats import EbookFile


class PdfFile(EbookFile):
    mimetype: str = "application/pdf"
    metadata_quality_score: int = -1

    def read(self) -> bool:
        try:
            reader: pypdf.PdfReader = pypdf.PdfReader(self.fpath)
            meta: pypdf.DocumentInformation | None = reader.metadata
        except:
            return False

        if meta is not None:
            if meta.author:
                self._metadata_file.authors = [str(meta.author)]
            if meta.title:
                self._metadata_file.title = str(meta.title)

        if self._cover_file.cover:
            return True

        try:
            page: pypdf.PageObject = reader.pages[0]
            images: list[pypdf._utils.ImageFile] = page.images
        except:
            print(f"Can't convert cover for {self.fpath}")
            return False

        if len(images) > 0:
            try:
                im: Image.Image = Image.open(io.BytesIO(images[0].data))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                self._cover_file.cover = im
                self._cover_file.cover_mimetype = "image/jpeg"
            except:
                print(f"Can't convert cover for {self.fpath}")
                return False
        return True
