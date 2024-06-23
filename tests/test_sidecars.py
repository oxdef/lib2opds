from pathlib import Path

import pytest

from lib2opds.sidecars import (
    CoverSidecarFile,
    InfoSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


def test_metadata_sidecar_file() -> None:
    info = get_metadata_sidecar_file(Path("sidecar"))
    assert type(info) == InfoSidecarFile  # nosec B101
