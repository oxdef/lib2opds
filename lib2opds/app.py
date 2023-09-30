import argparse
from dataclasses import dataclass
from pathlib import Path

from lib2opds.opds import dir2odps


@dataclass
class Config:
    library_dir: Path
    opds_dir: Path
    library_base_uri: str = ""
    opds_base_uri: str = ""
    library_title: str = ""


def cli():
    parser = argparse.ArgumentParser(
        description="Generate OPDS catalog for local e-book library"
    )
    parser.add_argument(
        "library_dir", metavar="library-dir", help="Directory with your books"
    )
    parser.add_argument(
        "opds_dir", metavar="opds-dir", help="Target directory for OPDS feeds"
    )
    parser.add_argument(
        "--library-base-uri",
        help="Base URI for serving books from the library, for example https://your-domain.com/library",
        default="/library/",
    )
    parser.add_argument(
        "--opds-base-uri",
        help="Base URI for OPDS, for example https://your-domain.com/opds",
        default="/opds/",
    )
    parser.add_argument("--library_title", help="Lybrary title", default="My library")
    args = parser.parse_args()
    config = Config(Path(args.library_dir), Path(args.opds_dir))
    config.opds_base_uri = args.opds_base_uri
    config.library_base_uri = args.library_base_uri
    config.library_title = args.library_title

    opds_catalog = dir2odps(config, args.library_dir)
    opds_catalog.export_as_xml()
