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

# pylint: disable=cyclic-import  # `new_instance` lazy-imports plain/bagit (see PLC0415); entity lazy-imports plain too. The graph is broken at runtime.
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.uri import URI, validate_rocrate_uri

from .entity import ROCrateEntity
from .metadata import ROCrateMetadata

if TYPE_CHECKING:
    from rdflib import Graph

# set up logging
logger = logging.getLogger(__name__)


class ROCrate(ABC):
    """
    Base class for representing and interacting with a Research Object Crate (RO-Crate).
    """

    def __new__(cls, uri: str | Path | URI, relative_root_path: Path | None = None):
        """
        Factory method to create the appropriate ROCrate subclass instance.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :param relative_root_path: the relative root path inside the RO-Crate
        :type relative_root_path: Path

        :return: an instance of the appropriate ROCrate subclass
        :rtype: ROCrate

        :raises ROCrateInvalidURIError: if the URI is invalid
        """
        if cls is not ROCrate:
            # If called on a subclass, use normal instantiation
            return super().__new__(cls)

        # If called on ROCrate directly, use factory logic
        instance = cls.new_instance(uri)
        if relative_root_path:
            instance.relative_root_path = relative_root_path
        return instance

    def __init__(self, uri: str | Path | URI, relative_root_path: Path | None = None) -> None:
        """
        Initialize the RO-Crate.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :raises ROCrateInvalidURIError: if the URI is invalid
        """

        # store the path to the crate
        self._uri = uri if isinstance(uri, URI) else URI(uri)

        # the relative root path inside the RO-Crate
        self.relative_root_path = relative_root_path

        # cache the list of files
        self._files: list[Path] | None = None

        # initialize variables to cache the data
        self._dict: dict | None = None
        self._graph: Graph | None = None

        self._metadata: ROCrateMetadata | None = None

    @property
    def uri(self) -> URI:
        """
        The URI of the RO-Crate.
        """
        return self._uri

    @property
    def metadata(self) -> ROCrateMetadata:
        """
        An ROCrateMetadata object representing the RO-Crate metadata.

        :return: the metadata object
        :rtype: ROCrateMetadata
        """
        if not self._metadata:
            self._metadata = ROCrateMetadata(self)
        return self._metadata

    def is_detached(self) -> bool:
        root = self.metadata.get_root_data_entity()
        if root and root.has_type("Dataset") and root.id == "./":
            return False
        if root and root.id_as_uri.is_remote_resource():
            # An absolute root @id doesn't necessarily mean detached;
            # check if there are any local (non-web) data entities
            local_data_entities = self.metadata.get_data_entities(exclude_web_data_entities=True)
            return all(entity.id == root.id for entity in local_data_entities)
        return False

    @property
    def metadata_descriptor_id(self) -> str:
        return ROCrateMetadata.METADATA_FILE_DESCRIPTOR

    @property
    @abstractmethod
    def size(self) -> int:
        """
        The size of the RO-Crate.

        :return: the size of the RO-Crate
        :rtype: int
        """

    @abstractmethod
    def list_files(self) -> list[Path]:
        """
        List all the files in the RO-Crate.

        :return: a list of file paths
        :rtype: list[Path]
        """

    def __get_search_path__(self, path: Path) -> tuple[Path, Path]:
        """
        Get the search path relative to the RO-Crate root path.

        :param path: the path to resolve
        :type path: Path
        :return: the search path
        :rtype: Path
        """
        assert path, "Path cannot be None"
        # Identify the root path of the RO-Crate
        root_path = self.uri.as_path() if self.uri.is_local_resource() and isinstance(path, Path) else Path("./")
        # Extract the search path relative to the root of the RO-Crate root path
        try:
            search_path = path.relative_to(root_path)
        except Exception:
            search_path = path
        return search_path, root_path

    def __check_search_path__(self, path) -> tuple[Path | None, Path | None]:
        """ "
        Extract the search path if it does not contain the relative root path.

        :param path: the path to resolve
        :type path: Path
        :return: the search path if valid, None otherwise
        :rtype: Path or None
        """
        if not self.relative_root_path:
            return None, None

        search_path, root_path = self.__get_search_path__(path)
        # Check if the path has the substring 'relative_root_path/' in it
        has_sub_data_path = re.search(str(self.relative_root_path), str(search_path))
        if not has_sub_data_path:
            return search_path, root_path
        return None, None

    def __parse_path__(self, path: Path) -> Path:
        """ "
        Parse the given path to resolve it within the RO-Crate.
        :param path: the path to resolve
        :type path: Path
        :return: the resolved path
        :rtype: Path
        """
        assert path, "Path cannot be None"

        # Resolve the path based on the RO-Crate location
        rocrate_path = self.uri.as_path() if self.uri.is_local_resource() else None
        rocrate_path_arg = rocrate_path if not str(rocrate_path).endswith(".zip") else None
        paths_to_try = [path]
        unquoted_path = Path(unquote(str(path)))
        if str(path) != str(unquoted_path):
            paths_to_try.append(unquoted_path)
        path_identifier = path
        for p in paths_to_try:
            path_identifier = ROCrateEntity.get_path_from_identifier(
                str(p), rocrate_path=rocrate_path_arg, decode=False
            )
            search_path, base_path = self.__check_search_path__(path_identifier)
            if search_path and base_path:
                if self.relative_root_path:
                    path_identifier = base_path / self.relative_root_path / search_path
                else:
                    path_identifier = base_path / search_path
                if path_identifier.exists():
                    return path_identifier
        return path_identifier

    def has_descriptor(self) -> bool:
        """
        Check if the RO-Crate has a metadata descriptor file.

        :return: `True` if the RO-Crate has a metadata descriptor file, `False` otherwise
        :rtype: bool
        """
        path = self.__parse_path__(Path(self.metadata_descriptor_id))
        logger.debug("Checking for metadata descriptor at path: %s", path)
        return self.has_file(path)

    def get_descriptor_path(self) -> Path | None:
        """
        Get the path to the metadata descriptor file if it exists.

        :return: the path to the metadata descriptor file if it exists, `None` otherwise
        :rtype: Path | None
        """
        try:
            path = self.__parse_path__(Path(self.metadata_descriptor_id))
            logger.debug("Checking for metadata descriptor at path: %s", path)
            if self.has_file(path):
                return path
            return None
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error getting the metadata descriptor path")
            return None

    def has_file(self, path: Path) -> bool:
        """
        Check if the RO-Crate has a file.

        :param path: the path to the file
        :type path: Path

        :return: `True` if the RO-Crate has the file, `False` otherwise
        :rtype: bool
        """
        try:
            return self.__parse_path__(path).is_file()
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error checking if path is a file")
            return False

    def has_directory(self, path: Path) -> bool:
        """
        Check if the RO-Crate has a directory.

        :param path: the path to the directory
        :type path: Path

        :return: `True` if the RO-Crate has the directory, `False` otherwise
        :rtype: bool
        """
        try:
            return self.__parse_path__(path).is_dir()
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error checking if path is a directory")
            return False

    @abstractmethod
    def get_file_size(self, path: Path) -> int:
        """
        Get the size of a file in the RO-Crate.

        :param path: the path to the file
        :type path: Path

        :return: the size of the file
        :rtype: int
        """

    @abstractmethod
    def get_file_content(self, path: Path, binary_mode: bool = True) -> str | bytes:
        """
        Get the content of a file in the RO-Crate.

        :param path: the path to the file
        :type path: Path

        :param binary_mode: if `True`, return the file as a `bytes` object; otherwise, return it as a `str`
        :type binary_mode: bool

        :return: the content of the file
        :rtype: Union[str, bytes]
        """

    @staticmethod
    def get_external_file_content(uri: str, binary_mode: bool = True) -> str | bytes:
        """
        Get the content of an external file.

        :param uri: the URI of the file
        :type uri: str

        :param binary_mode: if `True`, return the file as a `bytes` object; otherwise, return it as a `str`
        :type binary_mode: bool

        :return: the content of the file
        :rtype: Union[str, bytes]
        """
        response = HttpRequester().get(str(uri))
        response.raise_for_status()
        return response.content if binary_mode else response.text

    @staticmethod
    def get_external_file_size(uri: str) -> int | None:
        """
        Get the size of an external file.

        :param uri: the URI of the file
        :type uri: str

        :return: the size of the file, or None if the server did not provide a Content-Length header
        :rtype: int | None

        :raises requests.HTTPError: if the request fails
        """
        response = HttpRequester().head(str(uri))
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is None:
            return None
        return int(content_length)

    @staticmethod
    def from_metadata_dict(metadata_dict: dict) -> ROCrate:
        """
        Create a new instance of the RO-Crate based on the metadata dictionary.

        :param metadata_dict: the metadata dictionary
        :type metadata_dict: dict

        :raises ROCrateInvalidURIError: if the URI is invalid
        """
        # create a new instance based on the URI (the ROCrate factory __new__
        # dispatches to a concrete subclass, so this is not truly abstract)
        ro_crate = ROCrate(URI("./"), relative_root_path=None)  # type: ignore[abstract]

        # override the metadata with the provided dictionary
        ro_crate._metadata = ROCrateMetadata(ro_crate, metadata_dict=metadata_dict)
        return ro_crate

    @staticmethod
    def new_instance(uri: str | Path | URI, relative_root_path: Path | None = None) -> ROCrate:
        """
        Create a new instance of the RO-Crate based on the URI.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :return: a new instance of the RO-Crate
        :rtype: ROCrate

        :raises ROCrateInvalidURIError: if the URI is invalid
        """
        # Lazy imports break a cycle: bagit/plain inherit from this class,
        # but the factory needs runtime references to dispatch to them.
        from .bagit import (  # noqa: PLC0415
            BagitROCrate,
            ROCrateBagitLocalFolder,
            ROCrateBagitLocalZip,
            ROCrateBagitRemoteZip,
        )
        from .plain import (  # noqa: PLC0415
            ROCrateLocalFolder,
            ROCrateLocalMetadataFile,
            ROCrateLocalZip,
            ROCrateRemoteMetadataFile,
            ROCrateRemoteZip,
        )

        # check if the URI is valid
        validate_rocrate_uri(uri, silent=False)
        # create a new instance based on the URI
        if not isinstance(uri, URI):
            uri = URI(uri)
        # check if the URI is a BagIt-wrapped crate
        is_bagit_crate = BagitROCrate.is_bagit_wrapping_crate(uri)

        # check if the URI is a local directory
        if uri.is_local_directory():
            return (
                ROCrateBagitLocalFolder(uri, relative_root_path=relative_root_path)
                if is_bagit_crate
                else ROCrateLocalFolder(uri, relative_root_path=relative_root_path)
            )
        # check if the URI is a local zip file
        if uri.is_local_file():
            suffix = uri.as_path().suffix.lower()
            if suffix == ".zip":
                return (
                    ROCrateBagitLocalZip(uri, relative_root_path=relative_root_path)
                    if is_bagit_crate
                    else ROCrateLocalZip(uri, relative_root_path=relative_root_path)
                )
            return ROCrateLocalMetadataFile(uri, relative_root_path=relative_root_path)
        # check if the URI is a remote zip file
        if uri.is_remote_resource():
            path_suffix = Path(uri.get_path()).suffix.lower()
            if path_suffix == ".zip":
                return (
                    ROCrateBagitRemoteZip(uri, relative_root_path=relative_root_path)
                    if is_bagit_crate
                    else ROCrateRemoteZip(uri, relative_root_path=relative_root_path)
                )
            return ROCrateRemoteMetadataFile(uri, relative_root_path=relative_root_path)
        # if the URI is not supported, raise an error
        raise ROCrateInvalidURIError(uri=uri, message="Unsupported RO-Crate URI")
