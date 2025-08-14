import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self
from urllib.parse import quote, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from lib2opds.config import Config
from lib2opds.publications import Publication

env = Environment(loader=PackageLoader("lib2opds"), autoescape=select_autoescape())


def get_id() -> str:
    return str(uuid.uuid4())


@dataclass
class AtomFeed:
    config: Config
    root: Self | None
    parent: Self | None
    title: str = ""
    id: str = field(default_factory=get_id)
    updated: str = datetime.now().isoformat(timespec="seconds")

    def export_as_xml(self, recursive: bool = True) -> bool:
        raise NotImplementedError(
            "AtomFeed.export_as_xml should be implement in child class"
        )

    def is_root(self) -> bool:
        return self.root == None

    def get_title(self) -> str:
        if self.is_root():
            return self.config.library_title
        elif self.title:
            return self.title
        else:
            local_path = self.get_local_path_xml()
            return local_path.name.capitalize()

    def get_local_path_xml(self) -> Path:
        if not self.is_root():
            return (
                self.config.opds_dir / self.config.feeds_dir / Path(str(self.id) + ".xml")
            )
        else:
            return self.config.opds_dir / self.config.root_filename

    def get_local_path_html(self) -> Path:
        if not self.is_root():
            return (
                self.config.opds_dir
                / self.config.pages_dir
                / Path(str(self.id) + ".html")
            )
        else:
            return self.config.opds_dir / self.config.index_filename

    def get_link_self_href_xml(self) -> str:
        local_path = self.get_local_path_xml()
        link_self_href = urljoin(
            str(self.config.opds_base_uri),
            str(local_path.relative_to(self.config.opds_dir)),
        )
        return link_self_href

    def get_link_self_href_html(self) -> str:
        local_path = self.get_local_path_html()
        link_self_href = urljoin(
            str(self.config.opds_base_uri),
            str(local_path.relative_to(self.config.opds_dir)),
        )
        return link_self_href

    def get_all_publications(self) -> list[Publication]:
        result: list[Publication] = []
        # TODO
        return result

    def export_as_html(self, recursive: bool = True) -> bool:
        raise NotImplementedError(
            "AtomFeed.export_as_xml should be implement in child class"
        )


@dataclass
class AcquisitionFeed(AtomFeed):
    publications: list[Publication] = field(default_factory=list)
    kind: str = "acquisition"

    def export_as_xml(self, recursive: bool = False) -> bool:
        template = env.get_template("acquisition-feed.xml")
        data = template.render(feed=self)
        local_path = self.get_local_path_xml()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open(mode="w") as f:
            f.write(data)
        return True

    def get_all_publications(self) -> list[Publication]:
        return self.publications

    def export_as_html(self, recursive: bool = False) -> bool:
        template = env.get_template("acquisition-feed.html")
        data = template.render(feed=self)
        local_path = self.get_local_path_html()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open(mode="w") as f:
            f.write(data)
        return True


@dataclass
class NavigationFeed(AtomFeed):
    entries: list[AcquisitionFeed | Self] = field(default_factory=list)
    kind: str = "navigation"

    def export_as_xml(self, recursive: bool = True) -> bool:
        template = env.get_template("navigation-feed.xml")
        data = template.render(feed=self)
        local_path = self.get_local_path_xml()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open(mode="w") as f:
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

    def export_as_html(self, recursive: bool = True) -> bool:
        template = env.get_template("navigation-feed.html")
        data = template.render(feed=self)
        local_path = self.get_local_path_html()
        local_path.parent.mkdir(parents=True, exist_ok=True)

        with local_path.open(mode="w") as f:
            f.write(data)
        if recursive:
            for entry in self.entries:
                entry.export_as_html(recursive)
        return True
