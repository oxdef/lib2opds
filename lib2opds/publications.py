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
from urllib.parse import quote, urljoin

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
class Publication:
    config: Config
    fpath: Path
    title: str
    authors: list[str] = field(default_factory=list)
    language: str = ""
    identifier: str = ""
    mimetype: str = "Unknow"
    description: str = ""
    cover_href: str = ""
    cover_mimetype: str = ""
    cover: Image.Image | None = None
    acquisition_link: str = ""
    id: str = ""
    issued: str = ""
    publisher: str = ""
    cover_filename: str = ""

    def __post_init__(self) -> None:
        self.id = uuid.uuid4().urn
        self.cover_filename = str(uuid.uuid4())

    def _load_metadata(self) -> bool:
        return True

    def _get_cache_path(self) -> Path | None:
        if self.config.cache_dir and self.config.cache_dir.exists():
            return (
                self.config.cache_dir
                / hashlib.md5(bytes(self.fpath)).hexdigest()  # nosec B324
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

    def _load_cover_from_sidecar_file(self, sidecar: CoverSidecarFile) -> bool:
        if not sidecar.read():
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
        return True

    def _save_cover_to_sidecar_file(self, sidecar: CoverSidecarFile) -> bool:
        sidecar.cover = self.cover
        sidecar.cover_mimetype = self.cover_mimetype
        return sidecar.write()

    def _save_metadata_to_sidecar_file(self, sidecar: MetadataSidecarFile) -> bool:
        sidecar.authors = self.authors
        sidecar.title = self.title
        sidecar.description = self.description
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

    def load_metadata(self) -> bool:
        if not self._load_metadata_from_cache():
            self._load_metadata()
        else:
            return True
        self._load_metadata_from_sidecar_files(self.fpath)
        self._save_cover()  # To have persistent path to the cover for XML output
        self._save_metadata_to_cache()
        return True

    def _update(self, field_name: str, value: Any) -> None:
        if hasattr(self, field_name):
            setattr(self, field_name, value)


@dataclass
class EpubPublication(Publication):
    mimetype: str = "application/epub+zip"

    def _load_metadata(self) -> bool:
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
                im.thumbnail((self.config.cover_width, self.config.cover_height))
                self.cover = im
                self.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")

        zip.close()

        return True


@dataclass
class PdfPublication(Publication):
    mimetype: str = "application/pdf"

    def _load_metadata(self) -> bool:
        try:
            reader: pypdf.PdfReader = pypdf.PdfReader(self.fpath)
            meta: pypdf.DocumentInformation | None = reader.metadata
        except:
            return False

        if meta is not None:
            if meta.author:
                self._update("authors", [str(meta.author)])
            if meta.title:
                self._update("title", str(meta.title))

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
                im.thumbnail((self.config.cover_width, self.config.cover_height))
                self.cover = im
                self.cover_mimetype = "image/jpeg"
            except:
                print(f"Can't convert cover for {self.fpath}")
                return False

        return True


def get_mimetype_by_filename(fpath: Path) -> str | None:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else None


def get_title_by_filename(fpath: Path) -> str:
    return str(fpath.stem.replace("_", " ").capitalize())


def get_publication(fpath: Path, config: Config) -> Publication | None:
    pub_mimetype: str | None = get_mimetype_by_filename(fpath)

    if pub_mimetype is None:
        return None

    metadata_suffixes: list[str] = [".info", ".cover"]
    pub_title: str = get_title_by_filename(fpath)
    p: Publication | None = None

    if pub_mimetype == "application/epub+zip":
        p = EpubPublication(config, fpath, pub_title)
    elif pub_mimetype == "application/pdf":
        p = PdfPublication(config, fpath, pub_title)
    elif fpath.suffix not in metadata_suffixes:
        p = Publication(config, fpath, pub_title)
        p.mimetype = pub_mimetype
    else:
        return None

    p.acquisition_link = urljoin(
        config.library_base_uri, quote(str(fpath.relative_to(config.library_dir)))
    )
    return p
