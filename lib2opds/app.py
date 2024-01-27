import argparse
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lib2opds.config import Config
from lib2opds.opds import lib2odps


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
        help="Base URI for OPDS, for example https://domain.example/opds",
    )
    parser.add_argument("--library_title", help="Lybrary title")
    parser.add_argument("-c", "--config", help="Config path", default="config.ini")
    parser.add_argument(
        "-u", "--update", help="Force recreation of ODPS feeds", action="store_true"
    )
    parser.add_argument(
        "--clear-opds-dir",
        help="Clear OPDS directory before generating result feeds",
        action="store_true",
    )
    parser.add_argument("--cache-dir", help="Directory for caching ebook metadata")

    args = parser.parse_args()

    config = Config()
    config.load_from_file(Path("/etc/lib2opds.ini"))
    config.load_from_file(Path(args.config))
    config.load_from_args(args)
    opds_updated = None
    config.feeds_dir = Path("feeds")
    library_updated = get_utime_dir(config.library_dir)

    if config.opds_dir.is_dir():
        opds_updated = datetime.fromtimestamp(config.opds_dir.stat().st_mtime)

    if args.update or not opds_updated or opds_updated < library_updated:
        if config.clear_opds_dir:
            clear_dir(config.opds_dir)
            if config.cache_dir is not None:
                clear_dir(config.cache_dir)
        opds_catalog = lib2odps(config, config.library_dir)
        opds_catalog.export_as_xml()
