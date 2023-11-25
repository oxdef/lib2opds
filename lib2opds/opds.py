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


def get_urn() -> str:
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

    def export_as_xml(self, recursive: bool = True) -> bool:
        raise NotImplementedError(
            "AtomFeed.export_as_xml should be implement in child class"
        )

    def is_root(self) -> bool:
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
class AcquisitionFeed(AtomFeed):
    publications: list[Publication] = field(default_factory=list)
    kind: str = "acquisition"

    def export_as_xml(self, recursive: bool = False) -> bool:
        template = env.get_template("acquisition-feed.xml")
        data = template.render(feed=self)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with self.local_path.open(mode="w") as f:
            f.write(data)
        return True

    def get_all_publications(self) -> list[Publication]:
        return self.publications


@dataclass
class NavigationFeed(AtomFeed):
    entries: list[AcquisitionFeed | Self] = field(default_factory=list)
    kind: str = "navigation"

    def export_as_xml(self, recursive: bool = True) -> bool:
        template = env.get_template("navigation-feed.xml")
        data = template.render(feed=self)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with self.local_path.open(mode="w") as f:
            f.write(data)
        if recursive:
            for entry in self.entries:
                entry.export_as_xml(recursive)
        return True

    def get_all_publications(self) -> list[Publication]:
        result = []
        for e in self.entries:
            result.extend(e.get_all_publications())
        return result


def get_dir_contents(dirpath: Path) -> tuple[list[str], list[str]]:
    dirnames = []
    filenames = []
    with os.scandir(dirpath) as it:
        for entry in it:
            if entry.is_dir():
                dirnames.append(entry.path)
            elif entry.is_file():
                filenames.append(entry.path)
    return (dirnames, filenames)


def get_authors_from_publications(publications: list[Publication]) -> set[str]:
    result: set[str] = set()
    for p in publications:
        for author in p.authors:
            result.add(author)
    return result


def dir2odps(
    config: Config, dirpath: Path, parent: AtomFeed, root: AtomFeed
) -> NavigationFeed | AcquisitionFeed:
    dirnames: list[str]
    filenames: list[str]
    dirnames, filenames = get_dir_contents(dirpath)
    last_updated = datetime.fromtimestamp(dirpath.stat().st_mtime)
    title = dirpath.name.capitalize()
    local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )

    feed: AtomFeed
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
            dir_feed: NavigationFeed | AcquisitionFeed = dir2odps(
                config, Path(d), feed, root
            )
            feed.entries.append(dir_feed)
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
                feed.publications.append(p)
        return feed
    else:
        raise Exception("Mixed dir {}".format(dirpath))

    return feed


def author_to_first_letters(author: str) -> set[str]:
    chunks = [c.strip() for c in author.split(" ") if c.strip()]
    return set([l[0].upper() for l in chunks if len(l) > 1])


def generate_first_letters(all_authors: set[str]) -> set[str]:
    result: set[str] = set()
    for author in all_authors:
        chunks = [c.strip() for c in author.split(" ") if c.strip()]
        letters = [l[0].upper() for l in chunks if len(l) > 1]
        for l in letters:
            if l.isalnum():
                result.add(l)
    return result


def is_feed_sutable_to_author(feed: AtomFeed, author: str) -> bool:
    letters = author_to_first_letters(author)
    if feed.title.upper() in letters:
        return True
    else:
        return False


def get_feed_all_publications(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> AcquisitionFeed:
    local_path: Path = (
        config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    )
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_all_publications = AcquisitionFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        config.feed_all_publications_title,
        local_path,
    )
    for p in all_publications:
        feed_all_publications.publications.append(p)
    return feed_all_publications


def get_feed_by_author(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> NavigationFeed:
    all_authors: set[str] = get_authors_from_publications(all_publications)
    local_path: Path = (
        config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    )
    link_self_href: str = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    result: NavigationFeed = NavigationFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        config.feed_by_author_title,
        local_path,
    )

    # A, B, C ... Z
    first_letters: set[str] = generate_first_letters(all_authors)

    # feed_by_author -> [A, B, C ... Z]
    for first_letter in first_letters:
        local_path = config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
        link_self_href = urljoin(
            str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
        )
        feed_by_author_first_letter: NavigationFeed = NavigationFeed(
            config,
            link_self_href,
            feed_root.link_self_href,
            result.link_self_href,
            first_letter,
            local_path,
        )
        result.entries.append(feed_by_author_first_letter)
    # A -> [Author1, Author2], B -> ...
    for author in all_authors:
        for feed in result.entries:
            if not is_feed_sutable_to_author(feed, author):
                continue

            local_path = (
                config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
            )
            link_self_href = urljoin(
                str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
            )
            author_publications: AcquisitionFeed = AcquisitionFeed(
                config,
                link_self_href,
                feed_root.link_self_href,
                feed.link_self_href,
                author,
                local_path,
            )
            for p in all_publications:
                if author in p.authors:
                    author_publications.publications.append(p)
            if isinstance(feed, NavigationFeed):
                feed.entries.append(author_publications)
    return result


def get_feed_new_publications(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> AcquisitionFeed:
    local_path: Path = (
        config.opds_dir / config.feeds_dir / Path(str(uuid.uuid4()) + ".xml")
    )
    link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_new_publications = AcquisitionFeed(
        config,
        link_self_href,
        feed_root.link_self_href,
        feed_root.link_self_href,
        config.feed_new_publications_title,
        local_path,
    )
    for p in all_publications:
        updated = datetime.fromtimestamp(p.fpath.stat().st_mtime)
        if (datetime.now() - updated).days < config.publication_freshness_days:
            feed_new_publications.publications.append(p)
    return feed_new_publications


def lib2odps(config: Config, dirpath: Path) -> AtomFeed:
    title = config.library_title
    local_path: Path = config.opds_dir / config.root_filename
    link_start_href = link_up_href = link_self_href = urljoin(
        str(config.opds_base_uri), str(local_path.relative_to(config.opds_dir))
    )
    feed_root = NavigationFeed(
        config, link_self_href, link_start_href, link_up_href, title, local_path
    )

    # By directory
    feed_by_directory = dir2odps(config, config.library_dir, feed_root, feed_root)
    feed_by_directory.title = config.feed_by_directory_title
    feed_root.entries.append(feed_by_directory)

    # All publications
    all_publications: list[Publication] = feed_by_directory.get_all_publications()
    feed_all_publications: AcquisitionFeed = get_feed_all_publications(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_all_publications)

    # By author
    feed_by_author: NavigationFeed = get_feed_by_author(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_by_author)

    # New
    feed_new_publications: AcquisitionFeed = get_feed_new_publications(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_new_publications)

    return feed_root
