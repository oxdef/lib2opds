import configparser
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class SidecarFile:
    fpath: Path

    def read(self) -> bool:
        return True

    def write(self) -> bool:
        return True


@dataclass
class CoverSidecarFile(SidecarFile):
    cover_mimetype: str = ""
    cover: Image.Image | None = None
    cover_width: int | None = None
    cover_height: int | None = None
    cover_quality: int | None = None

    def read(self) -> bool:
        if not self.fpath.is_file():
            return False

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

    def write(self) -> bool:
        if not self.cover:
            return False
        try:
            self.cover.save(self.fpath, "JPEG", quality=self.cover_quality)
            return True
        except:
            return False


@dataclass
class MetadataSidecarFile(SidecarFile):
    title: str = ""
    authors: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class InfoSidecarFile(MetadataSidecarFile):
    def read(self) -> bool:
        if not self.fpath.is_file():
            return False

        info: configparser.ConfigParser = configparser.ConfigParser(interpolation=None)
        info.read(self.fpath)

        self.authors = [
            i.strip()
            for i in info["Publication"].get("authors", "").split(",")
            if i.strip()
        ]
        self.title = info["Publication"].get("title", "")
        self.description = info["Publication"].get("description", "")

        return True

    def write(self) -> bool:
        info: configparser.ConfigParser = configparser.ConfigParser(interpolation=None)
        info["Publication"] = {}
        info["Publication"]["authors"] = ", ".join(self.authors)
        info["Publication"]["title"] = self.title
        info["Publication"]["description"] = self.description

        try:
            with self.fpath.open("w") as fp:
                info.write(fp)
        except:
            return False

        return True


def get_metadata_sidecar_file(fpath: Path, kind: str = "info") -> MetadataSidecarFile:
    return InfoSidecarFile(fpath.with_suffix(".info"))


def get_cover_sidecar_file(
    fpath: Path, cover_width: int, cover_height: int, cover_quality: int
) -> CoverSidecarFile:
    sidecar = CoverSidecarFile(fpath.with_suffix(".cover"))
    sidecar.cover_width = cover_width
    sidecar.cover_height = cover_height
    sidecar.cover_quality = cover_quality
    return sidecar
