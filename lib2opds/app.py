import argparse
import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

from lib2opds.opds import dir2odps


@dataclass
class Config:
    library_dir: Path = field(default_factory=Path)
    opds_dir: Path = field(default_factory=Path)
    library_base_uri: str = ""
    opds_base_uri: str = ""
    library_title: str = ""
    cover_width: int = 500
    cover_height: int = 500
    cover_quality: int = 70

    def load_from_file(self, config_path: Path) -> bool:
        if not config_path.exists():
            return False

        config = configparser.ConfigParser()
        config.read(config_path)
        self.opds_dir = Path(config["General"].get("opds_dir"))
        self.opds_base_uri = config["General"].get("opds_base_uri")

        self.library_dir = Path(config["General"].get("library_dir"))
        self.library_base_uri = config["General"].get("library_base_uri")
        self.library_title = config["General"].get("library_title")

        return True

    def load_from_args(self, args: argparse.Namespace) -> bool:
        if args.library_dir:
            self.library_dir = Path(args.library_dir)
        if args.library_base_uri:
            self.library_base_uri = args.library_base_uri
        if args.opds_dir:
            self.opds_dir = Path(args.opds_dir)
        if args.opds_base_uri:
            self.opds_base_uri = args.opds_base_uri
        if args.library_title:
            self.library_title = args.library_title
        return True


def clean_dir(top: Path) -> bool:
    if not top.is_dir():
        return False
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            (Path(root) / name).unlink()
        for name in dirs:
            (Path(root) / name).rmdir()
    return True


def cli():
    parser = argparse.ArgumentParser(
        description="Generate OPDS catalog for local e-book library"
    )
    parser.add_argument("--library-dir", help="Directory with your books")
    parser.add_argument("--opds-dir", help="Target directory for OPDS feeds")
    parser.add_argument(
        "--library-base-uri",
        help="Base URI for serving books from the library, for example https://your-domain.com/library",
    )
    parser.add_argument(
        "--opds-base-uri",
        help="Base URI for OPDS, for example https://your-domain.com/opds",
    )
    parser.add_argument("--library_title", help="Lybrary title")
    parser.add_argument("-c", "--config", help="Config path", default="config.ini")
    parser.add_argument(
        "--clean-opds-dir",
        help="Clean OPDS directory before generating result feeds",
        action="store_true",
    )
    args = parser.parse_args()

    config = Config()
    config.load_from_file(Path("/etc/lib2opds.ini"))
    config.load_from_file(Path(args.config))
    config.load_from_args(args)

    if args.clean_opds_dir:
        clean_dir(config.opds_dir)

    opds_catalog = dir2odps(config, config.library_dir)
    opds_catalog.export_as_xml()
