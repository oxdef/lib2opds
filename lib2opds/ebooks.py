import mimetypes
from pathlib import Path

from lib2opds.formats import EbookFile
from lib2opds.formats.epub import EpubFile
from lib2opds.formats.m4b import M4bFile
from lib2opds.formats.pdf import PdfFile

mimetypes.add_type(M4bFile.mimetype, ".m4b")


def get_mimetype_by_filename(fpath: Path) -> str:
    (pub_mimetype, pub_encoding) = mimetypes.guess_file_type(fpath)
    return pub_mimetype if pub_mimetype else ""


def get_ebook_file_by_suffix(fpath: Path) -> EbookFile | None:
    mimetype: str | None = get_mimetype_by_filename(fpath)

    if mimetype is None:
        return None
    if mimetype == EpubFile.mimetype:
        f = EpubFile(fpath)
        return f
    elif mimetype == PdfFile.mimetype:
        p = PdfFile(fpath)
        return p
    elif mimetype == M4bFile.mimetype:
        m = M4bFile(fpath)
        return m
    else:
        return None
