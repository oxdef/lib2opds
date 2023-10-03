import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Self
from urllib.parse import quote, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from lib2opds.publication import Publication, get_publication

env = Environment(loader=PackageLoader("lib2opds"), autoescape=select_autoescape())


def get_urn():
    return uuid.uuid4().urn


@dataclass
class AtomFeed:
    link_self_href: str
    link_start_href: str
    link_up_href: str
    title: str = ""
    id: str = get_urn()
    updated: str = datetime.now().isoformat(timespec="seconds")
    local_path: Path = field(default_factory=Path)
    filename: str = "index.xml"

    def export_as_xml(self, recursive=True):
        raise NotImplementedError(
            "AtomFeed.export_as_xml should be implement in child class"
        )


@dataclass
class OPDSCatalogEntry:
    publication: Publication
    acquisition_link: str
    id: str = get_urn()


@dataclass
class NavigationFeed(AtomFeed):
    entries: list[AtomFeed] = field(default_factory=list)
    kind: str = "navigation"

    def export_as_xml(self, recursive=True):
        template = env.get_template("navigation-feed.xml")
        data = template.render(feed=self)
        self.local_path.mkdir(parents=True, exist_ok=True)
        feed_filename = self.local_path / self.filename
        with feed_filename.open(mode="w") as f:
            f.write(data)
        if recursive:
            for entry in self.entries:
                entry.export_as_xml(recursive)


@dataclass
class AcquisitionFeed(AtomFeed):
    entries: list[OPDSCatalogEntry] = field(default_factory=list)
    kind: str = "acquisition"

    def export_as_xml(self, recursive=False):
        template = env.get_template("acquisition-feed.xml")
        data = template.render(feed=self)
        self.local_path.mkdir(parents=True, exist_ok=True)
        feed_filename = self.local_path / self.filename
        with feed_filename.open(mode="w") as f:
            f.write(data)


def get_dir_contents(dirpath):
    dirnames = []
    filenames = []
    with os.scandir(dirpath) as it:
        for entry in it:
            if entry.is_dir():
                dirnames.append(entry.path)
            elif entry.is_file():
                filenames.append(entry.path)
    return (dirnames, filenames)


def dir2odps(config, dirpath, parent=None, root=None):
    dpath = Path(dirpath)
    link_self_href = urljoin(
        str(config.opds_base_uri), quote(str(dpath.relative_to(config.library_dir)))
    )
    link_start_href = root.link_self_href if root else link_self_href
    link_up_href = parent.link_self_href if parent else link_start_href
    dirnames, filenames = get_dir_contents(dirpath)
    if link_self_href == link_start_href:
        title = config.library_title
    else:
        title = dpath.name.capitalize()
    local_path = config.opds_dir / dpath.relative_to(config.library_dir)
    if dirnames:
        feed = NavigationFeed(link_self_href, link_start_href, link_up_href, title)
        feed.local_path = local_path
        if not root:
            root = feed
        for d in dirnames:
            feed.entries.append(dir2odps(config, d, feed, root))
    elif filenames:
        feed = AcquisitionFeed(link_self_href, link_start_href, link_up_href, title)
        feed.local_path = local_path
        # TODO pagination https://specs.opds.io/opds-1.2#24-listing-acquisition-feeds
        for f in filenames:
            fpath = Path(f)
            p = get_publication(fpath)
            # TODO move to export_as_xml
            p.load_metadata(config)
            entry = OPDSCatalogEntry(
                p,
                urljoin(
                    config.library_base_uri,
                    quote(str(fpath.relative_to(config.library_dir))),
                ),
            )
            feed.entries.append(entry)
        return feed
    else:
        raise Exception("Mixed dir {}".format(dirpath))

    return feed
