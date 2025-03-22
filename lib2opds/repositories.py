import errno
import hashlib
import io
import mimetypes
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

from PIL import Image

from lib2opds.config import Config
from lib2opds.ebooks import (
    EpubFile,
    PdfFile,
    get_ebook_file_by_suffix,
    get_mimetype_by_filename,
)
from lib2opds.publications import AcquisitionLink, Publication
from lib2opds.sidecars import (
    CoverSidecarFile,
    MetadataSidecarFile,
    get_cover_sidecar_file,
    get_metadata_sidecar_file,
)


class FilesystemRepository:
    config: Config

    def __init__(self, config: Config):
        self.config = config

    def get_title_by_filename(self, fpath: Path) -> str:
        return str(fpath.stem.replace("_", " ").capitalize())

    def get_publication(self, files: list[Path]) -> Publication | None:
        ebook_files = self._get_ebook_files(files)
        if not len(ebook_files):
            return None

        pub_title: str = self.get_title_by_filename(ebook_files[0])
        p = Publication(pub_title)

        (metadata, cover) = self._load_metadata_from_files(files)

        if metadata:
            p = self._init_publication_from_metadata(p, metadata)
        # Save cover to local path and create href for the publication
        if cover:
            local_cover_path = self._get_cover_local_path(p.cover_filename)
            cover.write(
                local_cover_path,
                self.config.cover_quality,
                self.config.cover_width,
                self.config.cover_height,
            )
            p.cover_href = self._get_cover_href(local_cover_path)
            p.cover_mimetype = "image/jpeg"

        p.acquisition_links = self._get_acquisition_links(ebook_files)
        p.updated = self._get_updated_from_ebook_files(ebook_files)
        return p

    def _get_updated_from_ebook_files(self, ebook_files: list[Path]) -> datetime:
        return datetime.fromtimestamp(ebook_files[0].stat().st_mtime)

    def _get_cover_local_path(self, cover_filename: str) -> Path:
        cover_dir: Path = self.config.opds_dir / "covers"
        cover_dir.mkdir(parents=True, exist_ok=True)
        local_cover_path: Path = cover_dir / cover_filename
        return local_cover_path

    def _get_cover_href(self, local_cover_path: Path) -> str:
        cover_href = urljoin(
            self.config.opds_base_uri,
            quote(str(local_cover_path.relative_to(self.config.opds_dir))),
        )
        return cover_href

    def _init_publication_from_metadata(
        self, p: Publication, metadata: MetadataSidecarFile
    ) -> Publication:
        result = p
        result.authors = metadata.authors
        result.title = metadata.title
        result.description = metadata.description
        result.language = metadata.language
        result.identifier = metadata.identifier
        result.issued = metadata.issued
        result.publisher = metadata.publisher
        return result

    def _get_ebook_path(self, files: list[Path]) -> Path | None:
        ebook_files = self._get_ebook_files(files)
        return ebook_files[0] if len(ebook_files) else None

    def _get_ebook_files(self, files: list[Path]) -> list[Path]:
        result: list[Path] = []
        metadata_suffixes: list[str] = [".info", ".cover"]
        for f in files:
            if f.suffix not in metadata_suffixes:
                result.append(f)
        return result

    def _load_metadata_from_ebook_files(
        self, files: list[Path]
    ) -> tuple[MetadataSidecarFile | None, CoverSidecarFile | None]:
        metadata: MetadataSidecarFile | None = None
        cover: CoverSidecarFile | None = None
        for f in self._get_ebook_files(files):
            ebook_file = get_ebook_file_by_suffix(f)
            if not ebook_file:
                continue
            if not ebook_file.read():
                continue
            metadata = ebook_file.get_metadata()
            cover = ebook_file.get_cover()
            if isinstance(ebook_file, EpubFile):
                break
        return (metadata, cover)

    def _load_metadata_from_sidecar_files(
        self, files: list[Path]
    ) -> tuple[MetadataSidecarFile | None, CoverSidecarFile | None]:
        if not (ebook_path := self._get_ebook_path(files)):
            return (None, None)
        metadata = get_metadata_sidecar_file(ebook_path)
        if not metadata.read():
            return (None, None)
        cover = get_cover_sidecar_file(ebook_path)
        if not cover.read():
            return (metadata, None)
        return (metadata, cover)

    def _load_metadata_from_files(
        self, files: list[Path]
    ) -> tuple[MetadataSidecarFile | None, CoverSidecarFile | None]:
        (metadata, cover) = self._load_metadata_from_ebook_files(files)
        (sidecar_metadata, sidecar_cover) = self._load_metadata_from_sidecar_files(files)

        if sidecar_metadata:
            metadata = sidecar_metadata

        if sidecar_cover:
            cover = sidecar_cover

        return (metadata, cover)

    def _update(self, field_name: str, value: Any) -> None:
        if hasattr(self, field_name):
            setattr(self, field_name, value)

    def _get_acquisition_links(self, ebook_files: list[Path]) -> list[AcquisitionLink]:
        result: list[AcquisitionLink] = []
        metadata_suffixes: list[str] = [".info", ".cover"]
        for f in ebook_files:
            fmimetype = get_mimetype_by_filename(f)
            href = urljoin(
                self.config.library_base_uri,
                quote(str(f.relative_to(self.config.library_dir))),
            )
            result.append(AcquisitionLink(href, fmimetype))
        return result


class CachingFilesystemRepository(FilesystemRepository):
    def get_publication(self, files: list[Path]) -> Publication | None:
        ebook_files = self._get_ebook_files(files)
        if not len(ebook_files):
            return None

        pub_title: str = self.get_title_by_filename(ebook_files[0])
        p = Publication(pub_title)

        # Try to load metadata from cache
        metadata = self._load_metadata_from_cache(files)
        cover = self._load_cover_from_cache(files)

        # Try to load metadata from ebook files and sidecar files
        if metadata == None:
            (metadata, cover) = self._load_metadata_from_files(files)

        if metadata:
            p = self._init_publication_from_metadata(p, metadata)

            # Save metadata to cache
            if cache_path := self._get_cache_path(files):
                if metadata:
                    metadata.write(cache_path.with_suffix(".info"))

        # Save cover to local path and create href for the publication
        if cover:
            local_cover_path = self._get_cover_local_path(p.cover_filename)
            cover.write(
                local_cover_path,
                self.config.cover_quality,
                self.config.cover_width,
                self.config.cover_height,
            )
            p.cover_href = self._get_cover_href(local_cover_path)
            p.cover_mimetype = "image/jpeg"

            # Save cover to cache
            if cache_path:
                cover.write(cache_path.with_suffix(".cover"), self.config.cover_quality)

        p.acquisition_links = self._get_acquisition_links(ebook_files)
        p.updated = self._get_updated_from_ebook_files(ebook_files)
        return p

    def _load_metadata_from_cache(self, files: list[Path]) -> MetadataSidecarFile | None:
        if cache_fpath := self._get_cache_path(files):
            metadata = get_metadata_sidecar_file(cache_fpath)
            if metadata.read():
                return metadata
        return None

    # TODO use another source for hash
    def _get_cache_path(self, files: list[Path]) -> Path | None:
        if self.config.cache_dir and self.config.cache_dir.exists():
            return (
                self.config.cache_dir
                / hashlib.md5(bytes(files[0])).hexdigest()  # nosec B324
            )
        else:
            return None

    def _load_cover_from_cache(self, files: list[Path]) -> CoverSidecarFile | None:
        if cache_fpath := self._get_cache_path(files):
            cover = get_cover_sidecar_file(cache_fpath)
            if cover.read():
                return cover
        return None
