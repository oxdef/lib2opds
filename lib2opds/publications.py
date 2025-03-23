import hashlib
import io
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from lib2opds.config import Config
from lib2opds.sidecars import (
    CoverSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


@dataclass
class AcquisitionLink:
    href: str
    mimetype: str


@dataclass
class Publication:
    title: str
    authors: list[str] = field(default_factory=list)
    language: str = ""
    identifier: str = ""
    description: str = ""
    cover_href: str = ""
    cover_mimetype: str = ""
    _id: str = ""
    issued: str = ""
    publisher: str = ""
    acquisition_links: list[AcquisitionLink] = field(
        default_factory=list[AcquisitionLink]
    )
    updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self._id = uuid.uuid4().urn
        self.cover_filename = str(uuid.uuid4())
