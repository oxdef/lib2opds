import argparse
import configparser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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
    clear_opds_dir: bool = True
    feeds_dir: Path = field(default_factory=Path)
    publication_freshness_days = 14
    root_filename: str = "index.xml"
    feed_by_directory_title: str = "Folders"
    feed_new_publications_title: str = "New Books"
    feed_all_publications_title: str = "All Books"
    feed_by_author_title: str = "Authors"
    cache_dir: Path | None = None

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
        self.clear_opds_dir = config["General"].getboolean("clear_opds_dir")
        self.publication_freshness_days = config["General"].getint(
            "publication_freshness_days", 14
        )
        self.root_filename = config["General"].get("root_filename")
        if config["General"].get("cache_dir", ""):
            self.cache_dir = Path(config["General"].get("cache_dir"))

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
        if args.clear_opds_dir:
            self.clear_opds_dir = args.clear_opds_dir
        if args.cache_dir:
            self.cache_dir = Path(args.cache_dir)

        return True
