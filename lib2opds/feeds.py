import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self
from urllib.parse import quote, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from lib2opds.config import Config
from lib2opds.publications import Publication, get_publication


def get_urn() -> str:
    return uuid.uuid4().urn


env = Environment(loader=PackageLoader("lib2opds"), autoescape=select_autoescape())


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
