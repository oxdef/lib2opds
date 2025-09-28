import mimetypes
from pathlib import Path

from lib2opds.formats import EbookFile
from lib2opds.formats.epub import EpubFile
from lib2opds.formats.pdf import PdfFile


def get_mimetype_by_filename(fpath: Path) -> str:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else ""


def get_ebook_file_by_suffix(fpath: Path) -> EbookFile | None:
    mimetype: str | None = get_mimetype_by_filename(fpath)

    if mimetype is None:
        return None

    if mimetype == "application/epub+zip":
        f = EpubFile(fpath)
        return f
    elif mimetype == "application/pdf":
        p = PdfFile(fpath)
        return p
    else:
        return None
