import argparse
import configparser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin


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
    feeds_dir: Path = Path("feeds")
    publication_freshness_days = 14
    root_filename: str = "index.xml"
    feed_by_directory_title: str = "Folders"
    feed_new_publications_title: str = "New Books"
    feed_all_publications_title: str = "All Books"
    feed_by_author_title: str = "Authors"
    feed_by_language_title: str = "Languages"
    feed_by_issued_date_title: str = "Issued"
    feed_random_book_title: str = "Random Book"
    cache_dir: Path | None = None
    invalidate_cache: bool = False
    index_filename: str = "index.html"
    generate_site: bool = False
    generate_site_xslt: bool = False
    generate_issued_feed: bool = True
    generate_languages_feed: bool = True
    generate_random_book_feed: bool = True
    pages_dir: Path = Path("pages")
    assets_dir: Path = Path("assets")

    def get_feeds_dir(self) -> Path:
        return self.opds_dir / self.feeds_dir

    def get_pages_dir(self) -> Path:
        return self.opds_dir / self.pages_dir

    def get_assets_dir(self) -> Path:
        return self.opds_dir / self.assets_dir

    def get_assets_uri(self) -> str:
        return urljoin(self.opds_base_uri, str(self.assets_dir))

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

        self.opds_dir = Path(config["General"].get("opds_dir", ""))
        self.library_dir = Path(config["General"].get("library_dir", ""))
        self.clear_opds_dir = config["General"].getboolean("clear_opds_dir", False)
        self.generate_site = config["General"].getboolean("generate_site", False)
        self.generate_site_xslt = config["General"].getboolean(
            "generate_site_xslt", False
        )
        self.generate_issued_feed = config["General"].getboolean(
            "generate_issued_feed", True
        )
        self.generate_languages_feed = config["General"].getboolean(
            "generate_languages_feed", True
        )
        self.generate_random_book_feed = config["General"].getboolean(
            "generate_random_book_feed", True
        )
        self.publication_freshness_days = config["General"].getint(
            "publication_freshness_days", 14
        )
        self.cover_quality = config["General"].getint("cover_quality", 70)

        if cache_dir := config["General"].get("cache_dir", ""):
            self.cache_dir = Path(cache_dir)

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
        if args.generate_site_xslt:
            self.generate_site_xslt = args.generate_site_xslt

        return True
