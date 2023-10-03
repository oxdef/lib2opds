# https://pypi.org/project/defusedxml/
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


@dataclass
class Publication:
    fpath: Path
    title: str
    creator: str = "Unknow"
    language: str = "Unknow"
    identifier: str = "Unknow"
    mimetype: str = "Unknow"
    description: str = ""
    cover_href: str = ""
    cover_mimetype: str = ""

    def load_metadata(self, config) -> bool:
        return True

    def _update(self, field_name, value):
        if hasattr(self, field_name):
            setattr(self, field_name, value)


@dataclass
class EpubPublication(Publication):
    mimetype: str = "application/epub+zip"

    def load_metadata(self, config) -> bool:
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
        metadata_fields = ["title", "creator", "language", "identifier", "description"]
        for f in metadata_fields:
            tmp = metadata_xml.find(f"dc:{f}", namespaces=namespaces)
            if tmp != None:
                self._update(f, tmp.text)

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
            cover_dir = config.opds_dir / "covers"
            cover_dir.mkdir(parents=True, exist_ok=True)
            cover_data = zip.read(cover_path)
            local_cover_path = cover_dir / str(uuid.uuid4())

            try:
                im = Image.open(io.BytesIO(cover_data))
                if im.mode != "RGB":
                    im = im.convert("RGB")
                im.thumbnail((config.cover_width, config.cover_height))
                im.save(local_cover_path, "JPEG", quality=config.cover_quality)
                self.cover_mimetype = "image/jpeg"
            except OSError:
                print(f"Can't convert cover for {self.fpath}")
                local_cover_path.write_bytes(cover_data)
                self.cover_mimetype = get_mimetype_by_filename(cover_path)

            self.cover_href = urljoin(
                config.opds_base_uri,
                quote(str(local_cover_path.relative_to(config.opds_dir))),
            )

        zip.close()

        return True


def get_mimetype_by_filename(fpath: Path) -> str:
    (pub_mimetype, pub_encoding) = mimetypes.guess_type(fpath)
    return pub_mimetype if pub_mimetype else "Unknow"


def get_publication(fpath: Path) -> Publication:
    pub_mimetype = get_mimetype_by_filename(fpath)
    pub_title = str(fpath.name.capitalize())
    if pub_mimetype == "application/epub+zip":
        return EpubPublication(fpath, pub_title)
    else:
        return Publication(fpath, pub_title)
