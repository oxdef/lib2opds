import configparser
import io
import mimetypes
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urljoin

from defusedxml.ElementTree import fromstring
from PIL import Image
from pypdf import PdfReader

from lib2opds.config import Config


def get_urn():
    return uuid.uuid4().urn


@dataclass
class Publication:
    fpath: Path
    title: str
    authors: list[str] = field(default_factory=list)
    language: str = ""
    identifier: str = ""
    mimetype: str = "Unknow"
    description: str = ""
    cover_href: str = ""
    cover_mimetype: str = ""
    cover_data: Image = None
    acquisition_link: str = ""
    id: str = get_urn()
    issued: str = ""
    publisher: str = ""

    def _load_metadata(self, config) -> bool:
        return True

    def save_cover(self, config) -> True:
        if not self.cover_data:
            return False
        cover_dir = config.opds_dir / "covers"
        cover_dir.mkdir(parents=True, exist_ok=True)
        local_cover_path = cover_dir / str(uuid.uuid4())
        self.cover_data.save(local_cover_path, "JPEG", quality=config.cover_quality)
        self.cover_href = urljoin(
            config.opds_base_uri,
            quote(str(local_cover_path.relative_to(config.opds_dir))),
        )
        return True

    def load_metadata(self, config) -> bool:
        info_fpath = self.fpath.with_suffix(".ini")
        if info_fpath.is_file():
            info = configparser.ConfigParser()
            info.read(info_fpath)
            self.authors = [
                i.strip() for i in info["Publication"].get("authors", "").split(",")
            ]
            self.title = info["Publication"].get("title", "")
            self.description = info["Publication"].get("description", "")
            return True
        else:
            return self._load_metadata(config)

    def _update(self, field_name, value):
        if hasattr(self, field_name):
            setattr(self, field_name, value)


@dataclass
class EpubPublication(Publication):
    mimetype: str = "application/epub+zip"

    def _load_metadata(self, config) -> bool:
        namespaces = {
            "cont": "urn:oasis:names:tc:opendocument:xmlns:container",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "pkg": "http://www.idpf.org/2007/opf",
        }

        zip = zipfile.ZipFile(self.fpath)
        mimetype_filename = "mimetype"
        container_filename = "META-INF/container.xml"

        # Perform some checks to be sure we deal with EPUB format
        if (
            container_filename not in zip.namelist()
            or mimetype_filename not in zip.namelist()
        ):
            return False

        tmp = zip.read(mimetype_filename)
        if tmp.decode() != self.mimetype:
            return False

        # Get container file contents to find root file
        container_data = zip.read(container_filename)
        container_xml = fromstring(container_data)
        root_filename = container_xml.find(
            "cont:rootfiles/cont:rootfile", namespaces=namespaces
        ).attrib["full-path"]

        # Get root file
        root_data = zip.read(root_filename)
        root_xml = fromstring(root_data)

        # Get metadata and update pub
        metadata_xml = root_xml.find("pkg:metadata", namespaces=namespaces)
        metadata_fields = {
            "title": "title",
            "language": "language",
            "identifier": "identifier",
            "description": "description",
            "date": "issued",
            "publisher": "publisher",
            "rights": "rights",
        }
        for f in metadata_fields:
            tmp = metadata_xml.find(f"dc:{f}", namespaces=namespaces)
            if tmp != None:
                self._update(metadata_fields[f], tmp.text)
        # Multiple authors
        creators = metadata_xml.findall(f"dc:creator", namespaces=namespaces)
        for c in creators:
            self.authors.append(c.text)
        # Get cover
        manifest_xml = root_xml.find("pkg:manifest", namespaces=namespaces)
        manifest_cover = metadata_xml.find(
            'pkg:meta/[@name="cover"]', namespaces=namespaces
        )
        cover_path = None
        if manifest_cover != None:
            cover_id = manifest_cover.attrib["content"]
            valid = re.compile(r"^[a-zA-Z._-]+$")
            if valid.match(cover_id):
                manifest_cover_path = manifest_xml.find(
                    f'pkg:item[@id="{cover_id}"]', namespaces=namespaces
                )
                if manifest_cover_path != None:
                    cover_path = manifest_cover_path.attrib["href"]
                    cover_path = str(Path(root_filename).parent / Path(cover_path))

        if cover_path and cover_path in zip.namelist():
            cover_data = zip.read(cover_path)
            try:
                im = Image.open(io.BytesIO(cover_data))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                im.thumbnail((config.cover_width, config.cover_height))
                self.cover_data = im
                self.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")

        zip.close()

        return True


@dataclass
class PdfPublication(Publication):
    mimetype: str = "application/pdf"

    def _load_metadata(self, config) -> bool:
        try:
            reader = PdfReader(self.fpath)
            meta = reader.metadata
        except:
            return False
        if meta.author:
            self.authors.append(str(meta.author))
        if meta.title:
            self.title = str(meta.title)
        try:
            page = reader.pages[0]
            images = page.images
        except:
            print(f"Can't convert cover for {self.fpath}")
            return False
        if images:
            try:
                im = Image.open(io.BytesIO(images[0].data))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                im.thumbnail((config.cover_width, config.cover_height))
                self.cover_data = im
                self.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")
                return False

        return True


def get_mimetype_by_filename(fpath: Path) -> str | None:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else None


def get_title_by_filename(fpath: Path) -> str:
    return str(fpath.stem.replace("_", " ").capitalize())


def get_publication(fpath: Path, config: Config) -> Publication | None:
    pub_mimetype = get_mimetype_by_filename(fpath)
    if not pub_mimetype:
        return None
    pub_title = get_title_by_filename(fpath)
    if pub_mimetype == "application/epub+zip":
        p = EpubPublication(fpath, pub_title)
    elif pub_mimetype == "application/pdf":
        p = PdfPublication(fpath, pub_title)
    elif fpath.suffix != ".ini":
        p = Publication(fpath, pub_title)
        p.mimetype = pub_mimetype
    else:
        return None
    p.acquisition_link = urljoin(
        config.library_base_uri, quote(str(fpath.relative_to(config.library_dir)))
    )
    return p
