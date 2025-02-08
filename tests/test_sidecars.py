from pathlib import Path

import pytest

from lib2opds.sidecars import (
    CoverSidecarFile,
    InfoSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


class TestInfoSidecarFile:
    test_sidecar_path = Path("tests").joinpath("data").joinpath("sidecar")

    def test_factory(self) -> None:
        info = get_metadata_sidecar_file(self.test_sidecar_path)
        assert type(info) == InfoSidecarFile

    def test_read(self) -> None:
        info = get_metadata_sidecar_file(self.test_sidecar_path)
        assert info.read() == True

    def test_read_false(self) -> None:
        info = get_metadata_sidecar_file(self.test_sidecar_path.with_name("nonexist"))
        assert info.read() != True

    def test_parsing(self) -> None:
        info = get_metadata_sidecar_file(self.test_sidecar_path)
        info.read()
        assert info.title == "Some title"
        assert info.description == "Some description"
        assert info.authors == ["Some author"]

    def test_write(self, tmp_path: Path) -> None:
        test_sidecar_path = tmp_path / "somefile"
        info = get_metadata_sidecar_file(test_sidecar_path)
        info.title = "Some title"
        info.description = "Some description"
        info.authors = ["Some author"]
        assert info.write() == True

        info = get_metadata_sidecar_file(test_sidecar_path)
        info.read()
        assert info.title == "Some title"
        assert info.description == "Some description"
        assert info.authors == ["Some author"]


class TestCoverSidecarFile:
    test_sidecar_path = Path("tests").joinpath("data").joinpath("sidecar.cover")

    def test_factory(self) -> None:
        info = get_cover_sidecar_file(self.test_sidecar_path, 100, 100, 100)
        assert type(info) == CoverSidecarFile

    def test_load(self) -> None:
        info = get_cover_sidecar_file(self.test_sidecar_path, 100, 100, 100)
        assert info.read() == True
