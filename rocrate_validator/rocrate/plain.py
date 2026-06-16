# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester

from .base import ROCrate
from .metadata import ROCrateMetadata

if TYPE_CHECKING:
    from rocrate_validator.utils.uri import URI

# set up logging
logger = logging.getLogger(__name__)


class ROCrateLocalFolder(ROCrate):
    """
    Class representing an RO-Crate stored in a local folder.
    """

    def __init__(self, path: str | Path | URI, relative_root_path: Path | None = None):
        super().__init__(path, relative_root_path=relative_root_path)

        # cache the list of files
        self._files = None
        self._metadata_descriptor_id: str | None = None

        # check if the path is a directory
        if not self.has_directory(self.uri.as_path()):
            raise ROCrateInvalidURIError(uri=path)

    @property
    def size(self) -> int:
        return sum(f.stat().st_size for f in self.list_files() if f.is_file())

    @property
    def metadata_descriptor_id(self) -> str:
        if self._metadata_descriptor_id:
            return self._metadata_descriptor_id
        base_path = self.uri.as_path()
        candidates = sorted(
            (p for p in base_path.rglob(f"*{ROCrateMetadata.METADATA_FILE_DESCRIPTOR}") if p.is_file()),
            key=lambda p: (len(p.relative_to(base_path).parts), str(p)),
        )
        if not candidates:
            self._metadata_descriptor_id = ROCrateMetadata.METADATA_FILE_DESCRIPTOR
            return self._metadata_descriptor_id
        self._metadata_descriptor_id = str(candidates[0].relative_to(base_path))
        return self._metadata_descriptor_id

    def list_files(self) -> list[Path]:
        if not self._files:
            self._files = []
            base_path = self.uri.as_path()
            for file in base_path.rglob("*"):
                if file.is_file():
                    self._files.append(base_path / file)
        return self._files

    def get_file_size(self, path: Path) -> int:
        path = self.__parse_path__(path)
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        return path.stat().st_size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> str | bytes:
        path = self.__parse_path__(path)
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes() if binary_mode else path.read_text(encoding="utf-8")


class ROCrateLocalZip(ROCrate):
    def __init__(
        self,
        path: str | Path | URI,
        relative_root_path: Path | None = None,
        init_zip: bool = True,
    ):
        super().__init__(path, relative_root_path=relative_root_path)

        # initialize the zip reference
        self._zipref: zipfile.ZipFile | None = None
        if init_zip:
            self.__init_zip_reference__()

        # cache the list of files
        self._files = None
        self._metadata_descriptor_id: str | None = None

    def __del__(self):
        try:
            if self._zipref and self._zipref.fp is not None:
                self._zipref.close()
                del self._zipref
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error closing zip reference")

    def __parse_path__(self, path):
        assert path, "Path cannot be None"
        # If the RO-Crate is a zip file, the path should be changed
        return path

    @property
    def size(self) -> int:
        return self.uri.as_path().stat().st_size

    def __init_zip_reference__(self):
        path = self.uri.as_path()
        # check if the path is a file
        if not self.uri.as_path().is_file():
            raise ROCrateInvalidURIError(uri=path)
        # check if the file is a zip file
        if self.uri.as_path().suffix != ".zip":
            raise ROCrateInvalidURIError(uri=path)
        self._zipref = zipfile.ZipFile(path)  # pylint: disable=consider-using-with
        logger.debug("Initialized zip reference: %s", self._zipref)

    def __get_file_info__(self, path: str | Path) -> zipfile.ZipInfo:
        assert self._zipref is not None, "Zip reference not initialized"
        try:
            return self._zipref.getinfo(str(path))
        except KeyError:
            logger.error("File not found in zip: %s", path)
            raise FileNotFoundError(f"File not found in zip: {path}") from None

    def has_descriptor(self) -> bool:
        """
        Check if the RO-Crate has a metadata descriptor file.
        :rtype: bool
        """
        path = self.__parse_path__(Path(self.metadata_descriptor_id))
        return str(path) in [str(_) for _ in self.list_files()]

    @property
    def metadata_descriptor_id(self) -> str:
        if self._metadata_descriptor_id:
            return self._metadata_descriptor_id
        candidates = sorted(
            (p for p in self.list_files() if str(p).endswith(ROCrateMetadata.METADATA_FILE_DESCRIPTOR)),
            key=lambda p: (len(p.parts), str(p)),
        )
        if not candidates:
            self._metadata_descriptor_id = ROCrateMetadata.METADATA_FILE_DESCRIPTOR
            return self._metadata_descriptor_id
        self._metadata_descriptor_id = str(candidates[0])
        return self._metadata_descriptor_id

    def has_file(self, path: Path) -> bool:
        path = self.__parse_path__(path)
        for p in self.list_files():
            if str(path) == str(p):
                info = self.__get_file_info__(path)
                return not info.is_dir()
        return False

    def has_directory(self, path: Path) -> bool:
        assert path, "Path cannot be None"
        assert self._zipref is not None, "Zip reference not initialized"
        for px in (path, self.__parse_path__(path)):
            for p in self._zipref.namelist():
                if f"{px!s}/" == str(p) or str(px) == str(p):
                    info = self.__get_file_info__(p)
                    return info.is_dir()
        return False

    def list_files(self) -> list[Path]:
        if not self._files:
            assert self._zipref is not None, "Zip reference not initialized"
            self._files = []
            for file in self._zipref.namelist():
                self._files.append(Path(file))
        return self._files

    def list_entries(self) -> list[zipfile.ZipInfo]:
        assert self._zipref is not None, "Zip reference not initialized"
        return self._zipref.infolist()

    def get_entry(self, path: Path) -> zipfile.ZipInfo:
        """
        Return the ZipInfo object for the specified path.
        """
        return self.__get_file_info__(self.__parse_path__(path))

    def get_file_size(self, path: Path) -> int:
        assert self._zipref is not None, "Zip reference not initialized"
        return self._zipref.getinfo(str(self.__parse_path__(path))).file_size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> str | bytes:
        path = self.__parse_path__(path)
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        assert self._zipref is not None, "Zip reference not initialized"
        data = self._zipref.read(str(path))
        return data if binary_mode else data.decode("utf-8")


class ROCrateLocalMetadataFile(ROCrate):
    def __init__(self, path: str | Path | URI, relative_root_path: Path | None = None):
        super().__init__(path, relative_root_path=relative_root_path)

        if not self.uri.is_local_file():
            raise ROCrateInvalidURIError(uri=path)

        suffix = self.uri.as_path().suffix.lower()
        if suffix not in (".json", ".jsonld"):
            raise ROCrateInvalidURIError(uri=path, message="Unsupported metadata file format")

    def is_detached(self) -> bool:
        return True

    @property
    def metadata_descriptor_id(self) -> str:
        return self.uri.as_path().name

    @property
    def size(self) -> int:
        return self.uri.as_path().stat().st_size

    def list_files(self) -> list[Path]:
        return [Path(self.metadata_descriptor_id)]

    def has_descriptor(self) -> bool:
        return True

    def has_file(self, path: Path) -> bool:
        return path.name == self.metadata_descriptor_id

    def get_file_size(self, path: Path) -> int:
        if path.name != self.metadata_descriptor_id:
            raise FileNotFoundError(f"File not found: {path}")
        return self.uri.as_path().stat().st_size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> str | bytes:
        if path.name != self.metadata_descriptor_id:
            raise FileNotFoundError(f"File not found: {path}")
        return self.uri.as_path().read_bytes() if binary_mode else self.uri.as_path().read_text(encoding="utf-8")


class ROCrateRemoteMetadataFile(ROCrate):
    def __init__(self, uri: str | Path | URI, relative_root_path: Path | None = None):
        super().__init__(uri, relative_root_path=relative_root_path)

        if not self.uri.is_remote_resource():
            raise ROCrateInvalidURIError(uri=uri)

    def is_detached(self) -> bool:
        return True

    @property
    def metadata_descriptor_id(self) -> str:
        return Path(self.uri.get_path()).name

    @property
    def size(self) -> int:
        response = HttpRequester().head(str(self.uri))
        response.raise_for_status()
        file_size = response.headers.get("Content-Length")
        if file_size is None:
            raise ValueError("Could not determine the file size from the headers")
        return int(file_size)

    def list_files(self) -> list[Path]:
        return [Path(self.metadata_descriptor_id)]

    def has_descriptor(self) -> bool:
        return True

    def has_file(self, path: Path) -> bool:
        return path.name == self.metadata_descriptor_id

    def get_file_size(self, path: Path) -> int:
        if path.name != self.metadata_descriptor_id:
            raise FileNotFoundError(f"File not found: {path}")
        return self.size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> str | bytes:
        if path.name != self.metadata_descriptor_id:
            raise FileNotFoundError(f"File not found: {path}")
        response = HttpRequester().get(str(self.uri), headers={"Accept": "application/ld+json"})
        response.raise_for_status()
        return response.content if binary_mode else response.text


class ROCrateRemoteZip(ROCrateLocalZip):
    def __init__(self, path: str | Path | URI, relative_root_path: Path | None = None):
        super().__init__(path, relative_root_path=relative_root_path, init_zip=False)

        # # initialize the zip reference
        self.__init_zip_reference__()

    def __init_zip_reference__(self):
        url = str(self.uri)

        # check if the URI is available
        if not self.uri.is_available():
            raise ROCrateInvalidURIError(uri=url, message="URI is not available")

        # Step 1: Fetch the last 22 bytes to find the EOCD record
        eocd_data = self.__fetch_range__(url, -22, "")

        # Step 2: Find the EOCD record
        eocd_offset = self.__find_eocd__(eocd_data)

        # Step 3: Fetch the EOCD and parse it
        eocd_full_data = self.__fetch_range__(url, -22 - eocd_offset, -1)
        central_directory_offset, central_directory_size = self.__parse_eocd__(eocd_full_data)

        # Step 4: Fetch the central directory
        central_directory_data = self.__fetch_range__(
            url, central_directory_offset, central_directory_offset + central_directory_size - 1
        )
        # Step 5: Parse the central directory and return the zip file
        self._zipref = zipfile.ZipFile(io.BytesIO(central_directory_data))  # pylint: disable=consider-using-with

    @property
    def size(self) -> int:
        response = HttpRequester().head(str(self.uri))
        response.raise_for_status()  # Check if the request was successful
        file_size = response.headers.get("Content-Length")
        if file_size is not None:
            return int(file_size)
        raise ValueError("Could not determine the file size from the headers")

    @staticmethod
    def __fetch_range__(uri: str, start, end):
        headers = {"Range": f"bytes={start}-{end}"}
        response = HttpRequester().get(uri, headers=headers)
        response.raise_for_status()
        return response.content

    @staticmethod
    def __find_eocd__(data):
        eocd_signature = b"PK\x05\x06"
        eocd_offset = data.rfind(eocd_signature)
        if eocd_offset == -1:
            raise ValueError("EOCD not found")
        return eocd_offset

    @staticmethod
    def __parse_eocd__(data):
        eocd_size = struct.calcsize("<4s4H2LH")
        eocd = struct.unpack("<4s4H2LH", data[-eocd_size:])
        central_directory_size = eocd[5]
        central_directory_offset = eocd[6]
        return central_directory_offset, central_directory_size
