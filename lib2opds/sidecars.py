import configparser
import errno
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps


@dataclass
class SidecarFile:
    fpath: Path

    def read(self) -> bool:
        return True

    def write(self, fpath: Path | None = None) -> bool:
        return True


@dataclass
class CoverSidecarFile(SidecarFile):
    cover_mimetype: str = ""
    cover: Image.Image | None = None
    cover_width: int | None = None
    cover_height: int | None = None
    cover_quality: int | None = None

    def read(self) -> bool:
        try:
            if not self.fpath.is_file():
                return False
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                return False
            raise

        try:
            im: Image.Image = Image.open(self.fpath)
            if im.mode != "RGB":
                im = im.convert("RGB")
            if self.cover_width and self.cover_height:
                im.thumbnail((self.cover_width, self.cover_height))
            self.cover = im
            # TODO fix cover_mimetype
            self.cover_mimetype = "image/jpeg"
            return True
        except OSError:
            print(f"Can't convert cover for {self.fpath}")
            return False

    def write(
        self,
        fpath: Path | None = None,
        cover_quality: int | None = None,
        cover_width: int | None = None,
        cover_height: int | None = None,
    ) -> bool:
        if not self.cover:
            return False
        try:
            fpath = fpath if fpath else self.fpath
            cover_quality = cover_quality if cover_quality else self.cover_quality
            if cover_width and cover_height:
                cover = ImageOps.contain(self.cover, (cover_width, cover_height))
                cover.save(fpath, "JPEG", quality=cover_quality)
            else:
                self.cover.save(fpath, "JPEG", quality=cover_quality)
            return True
        except:
            return False


@dataclass
class MetadataSidecarFile(SidecarFile):
    title: str = ""
    authors: list[str] = field(default_factory=list)
    description: str = ""
    language: str = ""
    identifier: str = ""
    issued: str = ""
    publisher: str = ""


@dataclass
class InfoSidecarFile(MetadataSidecarFile):
    def read(self) -> bool:
        try:
            if not self.fpath.is_file():
                return False
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                return False
            raise

        info: configparser.ConfigParser = configparser.ConfigParser(interpolation=None)
        info.read(self.fpath)

        self.authors = [
            i.strip()
            for i in info["Publication"].get("authors", "").split(",")
            if i.strip()
        ]
        self.title = info["Publication"].get("title", "")
        self.description = info["Publication"].get("description", "")
        self.language = info["Publication"].get("language", "")
        self.identifier = info["Publication"].get("identifier", "")
        self.issued = info["Publication"].get("issued", "")
        self.publisher = info["Publication"].get("publisher", "")

        return True

    def write(self, fpath: Path | None = None) -> bool:
        info: configparser.ConfigParser = configparser.ConfigParser(interpolation=None)
        info["Publication"] = {}
        info["Publication"]["authors"] = ", ".join(self.authors)
        info["Publication"]["title"] = self.title
        info["Publication"]["description"] = self.description
        info["Publication"]["language"] = self.language
        info["Publication"]["identifier"] = self.identifier
        info["Publication"]["issued"] = self.issued
        info["Publication"]["publisher"] = self.publisher

        try:
            fpath = fpath if fpath else self.fpath
            with fpath.open("w") as fp:
                info.write(fp)
        except:
            return False

        return True


def get_metadata_sidecar_file(fpath: Path, kind: str = "info") -> MetadataSidecarFile:
    return InfoSidecarFile(fpath.with_suffix(".info"))


def get_cover_sidecar_file(
    fpath: Path,
    cover_width: int | None = None,
    cover_height: int | None = None,
    cover_quality: int | None = None,
) -> CoverSidecarFile:
    sidecar = CoverSidecarFile(fpath.with_suffix(".cover"))
    sidecar.cover_width = cover_width
    sidecar.cover_height = cover_height
    sidecar.cover_quality = cover_quality
    return sidecar
