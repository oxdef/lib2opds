import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self
from urllib.parse import quote, urljoin

from lib2opds.config import Config
from lib2opds.feeds import AcquisitionFeed, AtomFeed, NavigationFeed
from lib2opds.publications import Publication
from lib2opds.repositories import CachingFilesystemRepository


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


def get_titles_from_publications(publications: list[Publication]) -> set[str]:
    result: set[str] = set()
    for p in publications:
        result.add(p.title)
    return result


def get_authors_from_publications(publications: list[Publication]) -> set[str]:
    result: set[str] = set()
    for p in publications:
        for author in p.authors:
            result.add(author)
    return result


def get_languages_from_publications(publications: list[Publication]) -> set[str]:
    result: set[str] = set()
    for p in publications:
        if p.language:
            result.add(p.language)
    return result


def get_index_by_filename(files: list[list[Path]], filename: Path) -> int:
    for i in range(len(files)):
        for f in files[i]:
            if f.stem == filename.stem:
                return i
    return -1


def group_files_by_filename(filenames: list[str]) -> list[list[Path]]:
    result: list[list[Path]] = []

    for f in filenames:
        tmp = Path(f)
        if (i := get_index_by_filename(result, tmp)) >= 0:
            result[i].append(tmp)
        else:
            result.append([tmp])

    return result


def dir2odps(
    config: Config, dirpath: Path, parent: AtomFeed, root: AtomFeed
) -> NavigationFeed | AcquisitionFeed:
    dirnames: list[str]
    filenames: list[str]
    dirnames, filenames = get_dir_contents(dirpath)
    last_updated = datetime.fromtimestamp(dirpath.stat().st_mtime)
    title = dirpath.name.capitalize()

    feed: AtomFeed
    repo = CachingFilesystemRepository(config)
    # Directory contains other directories or empty
    if len(dirnames) > 0 or (len(dirnames) + len(filenames) == 0):
        feed = NavigationFeed(config, root, parent, title)
        for d in dirnames:
            dir_feed: NavigationFeed | AcquisitionFeed = dir2odps(
                config, Path(d), feed, root
            )
            feed.entries.append(dir_feed)
    elif len(filenames) > 0:
        feed = AcquisitionFeed(config, root, parent, title)

        files = group_files_by_filename(filenames)

        for f in files:
            if p := repo.get_publication(f):
                feed.publications.append(p)
        return feed
    else:
        raise Exception("Mixed dir {}".format(dirpath))

    return feed


def author_to_first_letters(author: str) -> set[str]:
    chunks = [c.strip() for c in author.split(" ") if c.strip()]
    return set([l[0].upper() for l in chunks if len(l) > 1])


def generate_first_letters(strings: set[str], split: bool = True) -> set[str]:
    result: set[str] = set()
    for s in strings:
        if split:
            chunks = [c.strip() for c in s.split(" ") if c.strip()]
        else:
            chunks = [s.strip()]
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
    feed_all_publications = AcquisitionFeed(
        config, feed_root, feed_root, config.feed_all_publications_title
    )
    for p in all_publications:
        feed_all_publications.publications.append(p)
    return feed_all_publications


def get_feed_by_author(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> NavigationFeed:
    all_authors: set[str] = get_authors_from_publications(all_publications)
    result: NavigationFeed = NavigationFeed(
        config, feed_root, feed_root, config.feed_by_author_title
    )

    # A, B, C ... Z
    first_letters: set[str] = generate_first_letters(all_authors)

    # feed_by_author -> [A, B, C ... Z]
    for first_letter in first_letters:
        feed_by_author_first_letter: NavigationFeed = NavigationFeed(
            config, feed_root, result, first_letter
        )
        result.entries.append(feed_by_author_first_letter)
    # A -> [Author1, Author2], B -> ...
    for author in all_authors:
        for feed in result.entries:
            if not is_feed_sutable_to_author(feed, author):
                continue
            author_publications: AcquisitionFeed = AcquisitionFeed(
                config, feed_root, feed, author
            )
            for p in all_publications:
                if author in p.authors:
                    author_publications.publications.append(p)
            if isinstance(feed, NavigationFeed):
                feed.entries.append(author_publications)
    return result


def get_feed_all_publications_index(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> NavigationFeed:
    all_titles: set[str] = get_titles_from_publications(all_publications)
    result: NavigationFeed = NavigationFeed(
        config, feed_root, feed_root, config.feed_all_publications_title
    )

    first_letters: set[str] = generate_first_letters(all_titles, False)

    for first_letter in first_letters:
        feed_by_title_first_letter: AcquisitionFeed = AcquisitionFeed(
            config, feed_root, result, first_letter
        )
        for p in all_publications:
            if p.title.startswith(first_letter):
                feed_by_title_first_letter.publications.append(p)
        result.entries.append(feed_by_title_first_letter)
    return result


def get_feed_by_language(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> NavigationFeed:
    all_languages: set[str] = get_languages_from_publications(all_publications)
    result: NavigationFeed = NavigationFeed(
        config, feed_root, feed_root, config.feed_by_language_title
    )
    for language in all_languages:
        language_publications: AcquisitionFeed = AcquisitionFeed(
            config, feed_root, result, language
        )
        for p in all_publications:
            if language == p.language:
                language_publications.publications.append(p)
        result.entries.append(language_publications)

    return result


def get_feed_new_publications(
    config: Config, feed_root: NavigationFeed, all_publications: list[Publication]
) -> AcquisitionFeed:
    feed_new_publications = AcquisitionFeed(
        config, feed_root, feed_root, config.feed_new_publications_title
    )

    for p in all_publications:
        if (datetime.now() - p.updated).days < config.publication_freshness_days:
            feed_new_publications.publications.append(p)
    return feed_new_publications


def lib2odps(config: Config, dirpath: Path) -> AtomFeed:
    title = config.library_title
    feed_root = NavigationFeed(config, None, None, title)

    # By directory
    feed_by_directory = dir2odps(config, config.library_dir, feed_root, feed_root)
    feed_by_directory.title = config.feed_by_directory_title
    feed_root.entries.append(feed_by_directory)

    all_publications: list[Publication] = feed_by_directory.get_all_publications()

    # New
    feed_new_publications: AcquisitionFeed = get_feed_new_publications(
        config, feed_root, all_publications
    )

    if len(feed_new_publications.get_all_publications()):
        feed_root.entries.append(feed_new_publications)

    # All publications
    feed_all_publications: NavigationFeed = get_feed_all_publications_index(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_all_publications)

    # By author
    feed_by_author: NavigationFeed = get_feed_by_author(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_by_author)

    # By language
    feed_by_language: NavigationFeed = get_feed_by_language(
        config, feed_root, all_publications
    )
    feed_root.entries.append(feed_by_language)

    return feed_root
