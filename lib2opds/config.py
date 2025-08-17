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
    feed_by_language_title: str = "Languages"
    cache_dir: Path | None = None
    invalidate_cache: bool = False
    index_filename: str = "index.html"
    generate_site: bool = False
    pages_dir: Path = field(default_factory=Path)

    def _update_str_field(self, field_name: str, value: str) -> None:
        if hasattr(self, field_name):
            setattr(self, field_name, value)

    def load_from_file(self, config_path: Path) -> bool:
        if not config_path.exists():
            return False

        config = configparser.ConfigParser()
        config.read(config_path)

        str_fields = (
            "root_filename",
            "opds_base_uri",
            "library_base_uri",
            "library_title",
            "feed_by_directory_title",
            "feed_new_publications_title",
            "feed_all_publications_title",
            "feed_by_author_title",
            "feed_by_language_title",
            "index_filename",
        )

        for str_field in str_fields:
            if str_value := config["General"].get(str_field):
                self._update_str_field(str_field, str_value)

        self.opds_dir = Path(config["General"].get("opds_dir"))
        self.library_dir = Path(config["General"].get("library_dir"))
        self.clear_opds_dir = config["General"].getboolean("clear_opds_dir")
        self.site = config["General"].getboolean("site")
        self.publication_freshness_days = config["General"].getint(
            "publication_freshness_days", 14
        )

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
        if args.invalidate_cache:
            self.invalidate_cache = args.invalidate_cache
        if args.generate_site:
            self.generate_site = args.generate_site

        return True
