import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self
from urllib.parse import quote, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from lib2opds.config import Config
from lib2opds.publication import Publication, get_publication

env = Environment(loader=PackageLoader("lib2opds"), autoescape=select_autoescape())


def get_urn():
    return uuid.uuid4().urn


@dataclass
class AtomFeed:
    config: Config
    link_self_href: str
    link_start_href: str
    link_up_href: str
    title: str = ""
    local_path: Path = field(default_factory=Path)
    id: str = get_urn()
    updated: str = datetime.now().isoformat(timespec="seconds")

    def export_as_xml(self, recursive=True):
        raise NotImplementedError(
            "AtomFeed.export_as_xml should be implement in child class"
        )

    def is_root(self):
        return self.link_self_href == self.link_start_href

    def get_title(self) -> str:
        if self.is_root():
            return self.config.library_title
        elif self.title:
            return self.title
        else:
            return self.local_path.name.capitalize()

    def get_all_publications(self) -> list[Publication]:
        result: list[Publication] = []
        # TODO
        return result


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
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with self.local_path.open(mode="w") as f:
            f.write(data)
        if recursive:
            for entry in self.entries:
                entry.export_as_xml(recursive)

    def get_all_publications(self) -> list[Publication]:
        result = []
        for e in self.entries:
            result.extend(e.get_all_publications())
        return result


@dataclass
class AcquisitionFeed(AtomFeed):
    entries: list[OPDSCatalogEntry] = field(default_factory=list)
    kind: str = "acquisition"

    def export_as_xml(self, recursive=False):
        template = env.get_template("acquisition-feed.xml")
        data = template.render(feed=self)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with self.local_path.open(mode="w") as f:
            f.write(data)

    def get_all_publications(self) -> list[Publication]:
        # for p in self.entries:
        #    p.save_cover(self.config)
        return self.entries


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


def get_authors_from_publications(publications):
    result = set()
    for p in publications:
        for author in p.authors:
            result.add(author)
    return result


def dir2odps(
    config: Config, dirpath: Path, parent, root
) -> NavigationFeed | AcquisitionFeed:
    dirnames, filenames = get_dir_contents(dirpath)
    last_updated = datetime.fromtimestamp(dirpath.stat().st_mtime)
    title = dirpath.name.capitalize()
    local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )

    if dirnames:
        feed = NavigationFeed(
            config,
            link_self_href,
            root.link_self_href,
            parent.link_self_href,
            title,
            local_path,
        )
        for d in dirnames:
            f = dir2odps(config, Path(d), feed, root)
            feed.entries.append(f)
    elif filenames:
        feed = AcquisitionFeed(
            config,
            link_self_href,
            root.link_self_href,
            parent.link_self_href,
            title,
            local_path,
        )
        # TODO pagination https://specs.opds.io/opds-1.2#24-listing-acquisition-feeds
        for f in filenames:
            fpath = Path(f)
            p = get_publication(fpath, config)
            if p:
                p.load_metadata(config)
                p.save_cover(config)
                feed.entries.append(p)
        return feed
    else:
        raise Exception("Mixed dir {}".format(dirpath))

    return feed


def author_to_first_letters(author: str) -> set[str]:
    chunks = [c.strip() for c in author.split(" ") if c.strip()]
    return set([l[0].upper() for l in chunks if len(l) > 1])


def generate_first_letters(all_authors: set) -> set:
    result = set()
    for author in all_authors:
        chunks = [c.strip() for c in author.split(" ") if c.strip()]
        letters = [l[0].upper() for l in chunks if len(l) > 1]
        for l in letters:
            if l.isalnum():
                result.add(l)
    return result


def get_first_letter_feeds(
    feed_by_author: list[NavigationFeed], author: str
) -> list[NavigationFeed]:
    result = []
    letters = author_to_first_letters(author)
    for feed in feed_by_author:
        if feed.title.upper() in letters:
            result.append(feed)
    return result


def lib2odps(
    config: Config, dirpath: Path
) -> tuple[NavigationFeed | AcquisitionFeed, datetime]:
    title = config.library_title
    local_path = config.opds_dir / "index.xml"

    link_start_href = link_up_href = link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_root = NavigationFeed(
        config, link_self_href, link_start_href, link_up_href, title, local_path
    )

    # By directory
    feed_by_directory = dir2odps(config, config.library_dir, feed_root, feed_root)
    feed_by_directory.title = "Folders"
    feed_root.entries.append(feed_by_directory)

    # All publications
    local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_all_publications = AcquisitionFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        "All Books",
        local_path,
    )
    all_publications = feed_by_directory.get_all_publications()
    for p in all_publications:
        feed_all_publications.entries.append(p)
    feed_root.entries.append(feed_all_publications)

    # By author
    all_authors = get_authors_from_publications(all_publications)
    local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_by_author = NavigationFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        "Authors",
        local_path,
    )
    first_letters = generate_first_letters(all_authors)

    for first_letter in first_letters:
        local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
        link_self_href = urljoin(
            str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
        )
        feed_by_author_first_letter = NavigationFeed(
            config,
            link_self_href,
            feed_root.link_self_href,
            feed_by_author.link_self_href,
            first_letter,
            local_path,
        )
        feed_by_author.entries.append(feed_by_author_first_letter)

    for author in all_authors:
        local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
        link_self_href = urljoin(
            str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
        )

        feeds_by_author_first_letter = get_first_letter_feeds(
            feed_by_author.entries, author
        )
        for feed in feeds_by_author_first_letter:
            author_publications = AcquisitionFeed(
                config,
                link_self_href,
                feed_root.link_self_href,
                feed.link_self_href,
                author,
                local_path,
            )
            for p in all_publications:
                if author in p.authors:
                    author_publications.entries.append(p)
            feed.entries.append(author_publications)
    feed_root.entries.append(feed_by_author)

    # New
    local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_new_publications = AcquisitionFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        "New Books",
        local_path,
    )
    for p in all_publications:
        updated = datetime.fromtimestamp(p.fpath.stat().st_mtime)
        if (datetime.now() - updated).days < config.publication_freshness_days:
            feed_new_publications.entries.append(p)
    feed_root.entries.append(feed_new_publications)

    return feed_root
