from abc import ABC, abstractmethod
from pathlib import Path

from lib2opds.sidecars import (
    CoverSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


class EbookFile(ABC):
    fpath: Path
    metadata_quality_score: int = 0
    _metadata_file: MetadataSidecarFile
    _cover_file: CoverSidecarFile

    def __init__(self, fpath: Path):
        self.fpath = fpath
        self._metadata_file = MetadataSidecarFile(fpath)
        self._cover_file = CoverSidecarFile(fpath)

    def get_metadata(self) -> MetadataSidecarFile:
        return self._metadata_file

    def get_cover(self) -> CoverSidecarFile:
        return self._cover_file

    @abstractmethod
    def read(self) -> bool:
        pass
