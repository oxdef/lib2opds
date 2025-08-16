import argparse
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lib2opds import __version__
from lib2opds.config import Config
from lib2opds.opds import lib2odps

CONFIG_PATH = "/etc/lib2opds.ini"


def clear_dir(top: Path) -> bool:
    if not top.is_dir():
        return False
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            (Path(root) / name).unlink()
        for name in dirs:
            (Path(root) / name).rmdir()
    return True


def get_utime_dir(dpath: Path) -> datetime:
    updated = datetime.fromtimestamp(dpath.stat().st_mtime)
    for root, dirs, files in os.walk(dpath):
        for name in dirs:
            dir_updated = datetime.fromtimestamp((Path(root) / name).stat().st_mtime)
            if dir_updated > updated:
                updated = dir_updated
    return updated


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="lib2opds", description="Generate OPDS catalog for local e-book library"
    )
    parser.add_argument("--library-dir", help="directory with your books")
    parser.add_argument("--opds-dir", help="target directory for OPDS feeds")
    parser.add_argument(
        "--library-base-uri",
        help="base URI for serving books from the library, for example https://your-domain.com/library",
    )
    parser.add_argument(
        "--opds-base-uri",
        help="base URI for OPDS, for example https://domain.example/opds",
    )
    parser.add_argument("--library_title", help="library title")
    parser.add_argument("-c", "--config", help="config path", default="config.ini")
    parser.add_argument(
        "-u", "--update", help="force recreation of ODPS feeds", action="store_true"
    )
    parser.add_argument(
        "--clear-opds-dir",
        help="clear OPDS directory before generating result feeds",
        action="store_true",
    )
    parser.add_argument("--cache-dir", help="directory for caching ebook metadata")
    parser.add_argument(
        "--invalidate-cache",
        help="clear cache directory before generating result feeds",
        action="store_true",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--generate-site",
        help="generate static site additionally to OPDS catalog",
        action="store_true",
    )
    args = parser.parse_args()

    config = Config()
    config.load_from_file(Path(CONFIG_PATH))
    config.load_from_file(Path(args.config))
    config.load_from_args(args)
    opds_updated = None
    config.feeds_dir = Path("feeds")
    config.pages_dir = Path("pages")
    library_updated = get_utime_dir(config.library_dir)

    if config.opds_dir.is_dir():
        opds_updated = datetime.fromtimestamp(config.opds_dir.stat().st_mtime)

    if args.update or not opds_updated or opds_updated < library_updated:
        if config.invalidate_cache and config.cache_dir is not None:
            clear_dir(config.cache_dir)
        if config.clear_opds_dir:
            clear_dir(config.opds_dir)
        opds_catalog = lib2odps(config, config.library_dir)
        opds_catalog.export_as_xml()
        if config.generate_site:
            opds_catalog.export_as_html()


if __name__ == "__main__":
    cli()
