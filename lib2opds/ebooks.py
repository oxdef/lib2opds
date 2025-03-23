import io
import mimetypes
import re
import xml.etree.ElementTree as ET  # nosec B405 because actually defusedxml is used
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import pypdf
from defusedxml.ElementTree import fromstring
from PIL import Image

from lib2opds.sidecars import (
    CoverSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


class EbookFile:
    fpath: Path
    _metadata_file: MetadataSidecarFile
    _cover_file: CoverSidecarFile

    def __init__(self, fpath: Path):
        self.fpath = fpath
        self._metadata_file = MetadataSidecarFile(fpath)
        self._cover_file = CoverSidecarFile(fpath)

    def get_metadata(self) -> MetadataSidecarFile:
        return self._metadata_file

    def get_cover(self) -> CoverSidecarFile:
        return self._cover_file


class PdfFile(EbookFile):
    mimetype: str = "application/pdf"

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


class EpubFile(EbookFile):
    mimetype: str = "application/epub+zip"

    def read(self) -> bool:
        namespaces: dict[str, str] = {
            "cont": "urn:oasis:names:tc:opendocument:xmlns:container",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "pkg": "http://www.idpf.org/2007/opf",
        }

        zip: zipfile.ZipFile = zipfile.ZipFile(self.fpath)
        mimetype_filename: str = "mimetype"
        container_filename: str = "META-INF/container.xml"

        # Perform some checks to be sure that we deal with EPUB format
        if (
            container_filename not in zip.namelist()
            or mimetype_filename not in zip.namelist()
        ):
            return False

        internal_mimetype: bytes = zip.read(mimetype_filename)
        if internal_mimetype.decode() != self.mimetype:
            return False

        # Get container file contents to find root file
        container_data: bytes = zip.read(container_filename)
        container_xml: ET.Element = fromstring(container_data)
        rootfile_el: ET.Element | None = container_xml.find(
            "cont:rootfiles/cont:rootfile", namespaces=namespaces
        )

        if rootfile_el is not None:
            root_filename: str = rootfile_el.attrib["full-path"]
        else:
            return False

        # Get root file
        root_data: bytes = zip.read(root_filename)
        root_xml: ET.Element = fromstring(root_data)

        # Get metadata and update pub
        metadata_xml: ET.Element | None = root_xml.find(
            "pkg:metadata", namespaces=namespaces
        )
        metadata_fields: dict[str, str] = {
            "title": "title",
            "language": "language",
            "identifier": "identifier",
            "description": "description",
            "date": "issued",
            "publisher": "publisher",
            "rights": "rights",
        }

        if metadata_xml is None:
            return False

        for f in metadata_fields:
            tmp: ET.Element | None = metadata_xml.find(f"dc:{f}", namespaces=namespaces)
            if tmp is not None:
                self._update_metadata(metadata_fields[f], tmp.text)

        # Multiple authors
        creators: list[ET.Element] = metadata_xml.findall(
            f"dc:creator", namespaces=namespaces
        )
        for c in creators:
            if c.text:
                self._metadata_file.authors.append(c.text)

        # Get cover
        manifest_xml: ET.Element | None = root_xml.find(
            "pkg:manifest", namespaces=namespaces
        )
        if manifest_xml is not None:
            manifest_cover_el: ET.Element | None = metadata_xml.find(
                'pkg:meta/[@name="cover"]', namespaces=namespaces
            )
        else:
            return False

        if self._cover_file.cover:
            return True

        cover_path: str | None = None

        if manifest_cover_el is not None:
            cover_id: str = manifest_cover_el.attrib["content"]
            valid: re.Pattern = re.compile(r"^[a-zA-Z._-]+$")

            if valid.match(cover_id):
                manifest_cover_path: ET.Element | None = manifest_xml.find(
                    f'pkg:item[@id="{cover_id}"]', namespaces=namespaces
                )

                if manifest_cover_path is not None:
                    cover_path = str(
                        Path(root_filename).parent
                        / Path(manifest_cover_path.attrib["href"])
                    )

        if cover_path and cover_path in zip.namelist():
            cover_data: bytes = zip.read(cover_path)
            try:
                im: Image.Image = Image.open(io.BytesIO(cover_data))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                self._cover_file.cover = im
                self._cover_file.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")

        zip.close()

        return True

    def _update_metadata(self, field_name: str, value: Any) -> None:
        if hasattr(self._metadata_file, field_name):
            setattr(self._metadata_file, field_name, value)

    def write(self) -> bool:
        return False


def get_mimetype_by_filename(fpath: Path) -> str:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else ""


def get_ebook_file_by_suffix(fpath: Path) -> EpubFile | PdfFile | None:
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
