import hashlib
import io
import mimetypes
import re
import uuid
import xml.etree.ElementTree as ET  # nosec B405 because actually defusedxml is used
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import errno
from urllib.parse import quote, urljoin
from datetime import datetime

import pypdf
from defusedxml.ElementTree import fromstring
from PIL import Image

from lib2opds.config import Config
from lib2opds.sidecars import (
    CoverSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)



@dataclass
class PdfFile(MetadataSidecarFile):

    cover_width: int | None = None
    cover_height: int | None = None
    cover_quality: int | None = None
    cover: Image.Image | None = None
    cover_mimetype: str = ""
    mimetype: str = "application/pdf"

    def read(self) -> bool:
        try:
            reader: pypdf.PdfReader = pypdf.PdfReader(self.fpath)
            meta: pypdf.DocumentInformation | None = reader.metadata
        except:
            return False

        if meta is not None:
            if meta.author:
                self.authors = [str(meta.author)]
            if meta.title:
                self.title = str(meta.title)

        if self.cover:
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
                im.thumbnail((self.cover_width, self.cover_height))
                self.cover = im
                self.cover_mimetype = "image/jpeg"
            except:
                print(f"Can't convert cover for {self.fpath}")
                return False
        return True

@dataclass
class EpubFile(MetadataSidecarFile):

    cover_width: int | None = None
    cover_height: int | None = None
    cover_quality: int | None = None
    cover: Image.Image | None = None
    cover_mimetype: str = ""
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
                self._update(metadata_fields[f], tmp.text)

        # Multiple authors
        creators: list[ET.Element] = metadata_xml.findall(
            f"dc:creator", namespaces=namespaces
        )
        for c in creators:
            if c.text:
                self.authors.append(c.text)

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

        if self.cover:
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
                im.thumbnail((self.cover_width, self.cover_height))
                self.cover = im
                self.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")

        zip.close()

        return True

    def _update(self, field_name: str, value: Any) -> None:
        if hasattr(self, field_name):
            setattr(self, field_name, value)


    def write(self) -> bool:
        return False

def get_ebook_file_by_suffix(fpath: Path, cover_width: int, cover_height: int, cover_quality: int) -> EpubFile|PdfFile|None:
    mimetype: str | None = get_mimetype_by_filename(fpath)

    if mimetype is None:
        return None

    if mimetype == "application/epub+zip":
        f = EpubFile(fpath)
        f.cover_width = cover_width
        f.cover_height = cover_height
        f.cover_quality = cover_quality
        return f
    elif mimetype == "application/pdf":
        p = PdfFile(fpath)
        p.cover_width = cover_width
        p.cover_height = cover_height
        p.cover_quality = cover_quality
        return p
    else:
        return None


@dataclass()
class AcquisitionLink:
    href: str
    mimetype: str

@dataclass
class Publication:
    config: Config
    files: list[Path]
    title: str
    authors: list[str] = field(default_factory=list)
    language: str = ""
    identifier: str = ""
    description: str = ""
    cover_href: str = ""
    cover_mimetype: str = ""
    cover: Image.Image | None = None
    id: str = ""
    issued: str = ""
    publisher: str = ""
    cover_filename: str = ""

    def __post_init__(self) -> None:
        self.id = uuid.uuid4().urn
        self.cover_filename = str(uuid.uuid4())

    # TODO use another source for hash
    def _get_cache_path(self) -> Path | None:
        if self.config.cache_dir and self.config.cache_dir.exists():
            return (
                self.config.cache_dir
                / hashlib.md5(bytes(self.files[0])).hexdigest()  # nosec B324
            )
        else:
            return None

    def _save_cover(self) -> bool:
        if not self.cover:
            return False
        cover_dir: Path = self.config.opds_dir / "covers"
        cover_dir.mkdir(parents=True, exist_ok=True)
        local_cover_path: Path = cover_dir / self.cover_filename
        self.cover.save(local_cover_path, "JPEG", quality=self.config.cover_quality)
        self.cover_href = urljoin(
            self.config.opds_base_uri,
            quote(str(local_cover_path.relative_to(self.config.opds_dir))),
        )
        return True

    def _load_cover_from_sidecar_file(self, sidecar: CoverSidecarFile|EpubFile|PdfFile, reread: bool = True) -> bool:
        if reread and not sidecar.read():
            return False
        self.cover = sidecar.cover
        self.cover_mimetype = sidecar.cover_mimetype
        return True

    def _load_metadata_from_sidecar_file(self, sidecar: MetadataSidecarFile) -> bool:
        if not sidecar.read():
            return False
        self.authors = sidecar.authors
        self.title = sidecar.title
        self.description = sidecar.description
        self.language = sidecar.language
        self.identifier = sidecar.identifier
        self.issued = sidecar.issued
        self.publisher = sidecar.publisher

        return True

    def _save_cover_to_sidecar_file(self, sidecar: CoverSidecarFile) -> bool:
        sidecar.cover = self.cover
        sidecar.cover_mimetype = self.cover_mimetype
        return sidecar.write()

    def _save_metadata_to_sidecar_file(self, sidecar: MetadataSidecarFile) -> bool:
        sidecar.authors = self.authors
        sidecar.title = self.title
        sidecar.description = self.description
        sidecar.language = self.language
        sidecar.identifier = self.identifier
        sidecar.issued = self.issued
        sidecar.publisher = self.publisher

        return sidecar.write()

    def _load_metadata_from_cache(self) -> bool:
        if cache_fpath := self._get_cache_path():
            return self._load_metadata_from_sidecar_files(cache_fpath)
        return False

    def _save_metadata_to_cache(self) -> bool:
        if cache_fpath := self._get_cache_path():
            return self._save_metadata_to_sidecar_files(cache_fpath)
        return False

    def _load_metadata_from_sidecar_files(self, fpath: Path) -> bool:
        if not self._load_metadata_from_sidecar_file(get_metadata_sidecar_file(fpath)):
            return False

        self._load_cover_from_sidecar_file(
            get_cover_sidecar_file(
                fpath,
                self.config.cover_width,
                self.config.cover_height,
                self.config.cover_quality,
            )
        )
        return True

    def _save_metadata_to_sidecar_files(self, fpath: Path) -> bool:
        if not self._save_metadata_to_sidecar_file(get_metadata_sidecar_file(fpath)):
            return False
        self._save_cover_to_sidecar_file(
            get_cover_sidecar_file(
                fpath,
                self.config.cover_width,
                self.config.cover_height,
                self.config.cover_quality,
            )
        )
        return True

    def _get_ebook_files(self) -> list[Path]:
        result: list[Path] = []
        metadata_suffixes: list[str] = [".info", ".cover"]
        for f in self.files:
            if f.suffix not in metadata_suffixes:
                result.append(f)
        return result

    def _load_metadata_from_ebook_files(self) -> bool:
        for f in self._get_ebook_files():
            ebook_file = get_ebook_file_by_suffix(f, self.config.cover_width, self.config.cover_height, self.config.cover_quality)
            if not ebook_file:
                continue
            self._load_metadata_from_sidecar_file(ebook_file)
            self._load_cover_from_sidecar_file(ebook_file, False)
            if isinstance(ebook_file, EpubFile):
                break
        return True

    def load_metadata(self) -> bool:
        if self._load_metadata_from_cache():
            self._save_cover()  # To have persistent path to the cover for XML output
            return True
        else:
            self._load_metadata_from_ebook_files()
        self._load_metadata_from_sidecar_files(self.files[0])
        self._save_cover()
        self._save_metadata_to_cache()
        return True

    def _update(self, field_name: str, value: Any) -> None:
        if hasattr(self, field_name):
            setattr(self, field_name, value)


    def get_acquisition_links(self) -> list[AcquisitionLink]:
        result:list[AcquisitionLink] = []
        metadata_suffixes: list[str] = [".info", ".cover"]
        for f in self._get_ebook_files():
            fmimetype = get_mimetype_by_filename(f)
            href = urljoin(self.config.library_base_uri, quote(str(f.relative_to(self.config.library_dir))))
            result.append(AcquisitionLink(href,fmimetype))
        return result

    def updated(self) -> datetime:
        ebook_files = self._get_ebook_files()
        return datetime.fromtimestamp(ebook_files[0].stat().st_mtime)

def get_mimetype_by_filename(fpath: Path) -> str:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else ""


def get_title_by_filename(fpath: Path) -> str:
    return str(fpath.stem.replace("_", " ").capitalize())


def get_publication(files: list[Path], config: Config) -> Publication | None:
    pub_title: str = get_title_by_filename(files[0])
    p = Publication(config, files, pub_title)
    return p
