# Copyright (c) 2024-2025 CRS4
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
import json
import struct
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote

from rdflib import Graph

from rocrate_validator import log as logging
from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils import URI, HttpRequester, validate_rocrate_uri

# set up logging
logger = logging.getLogger(__name__)


class ROCrateEntity:

    def __init__(self, metadata: ROCrateMetadata, raw_data: object) -> None:
        self._raw_data = raw_data
        self._metadata = metadata

    @property
    def id(self) -> str:
        return self._raw_data.get('@id')

    @property
    def type(self) -> Union[str, list[str]]:
        return self._raw_data.get('@type')

    @property
    def name(self) -> str:
        return self._raw_data.get('name')

    @property
    def metadata(self) -> ROCrateMetadata:
        return self._metadata

    @property
    def ro_crate(self) -> ROCrate:
        return self.metadata.ro_crate

    def is_remote(self) -> bool:
        return self.id_as_uri.is_remote_resource()

    @classmethod
    def get_id_as_path(cls, entity_id: str, ro_crate: Optional[ROCrate] = None) -> Path:
        return cls.get_path_from_identifier(entity_id, ro_crate.uri.as_path() if ro_crate else None)

    @staticmethod
    def get_path_from_identifier(identifier: str, rocrate_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Get the path from an identifier.


        :param identifier: the identifier of the entity
        :type identifier: str

        :param rocrate_path: the path to the RO-Crate
        :type rocrate_path: Optional[Union[str, Path]

        :return: the path to the entity
        :rtype: Path

        """
        def __define_path__(path: str, decode: bool = False) -> Path:
            # ensure the path is a string and remove the file:// prefix
            path = str(path).replace('file://', '')
            # Decode the path if required
            if decode:
                path = unquote(path)
            # Convert the path to a Path object
            path = Path(path)
            # if the path is absolute, return it
            if path.is_absolute():
                return path
            try:
                # set the base path
                base_path = rocrate_path
                if base_path is None:
                    base_path = Path('./')
                elif not isinstance(base_path, Path):
                    base_path = Path(base_path)
                # Check if the path if the root of the RO-Crate
                if path == Path('./'):
                    return base_path
                # if the path is relative, try to resolve it
                return base_path / path.relative_to(base_path)
            except ValueError:
                # if the path cannot be resolved, return the absolute path
                return base_path / path
        # Define the path based on the identifier
        path = __define_path__(identifier)
        if not path.exists():
            path = __define_path__(identifier, decode=True)
        return path

    @property
    def id_as_path(self) -> Path:
        return self.get_id_as_path(self.id, self.ro_crate)

    @classmethod
    def get_id_as_uri(cls, entity_id: str, ro_crate: ROCrate) -> URI:
        assert entity_id, "Entity ID cannot be None"
        if entity_id.startswith("http"):
            return URI(entity_id)
        return URI(cls.get_id_as_path(entity_id, ro_crate))

    @property
    def id_as_uri(self) -> URI:
        return self.get_id_as_uri(self.id, self.ro_crate)

    def has_absolute_path(self) -> bool:
        return self.get_id_as_path(self.id).is_absolute()

    def has_relative_path(self) -> bool:
        return not self.has_absolute_path()

    def has_type(self, entity_type: str) -> bool:
        assert isinstance(entity_type, str), "Entity type must be a string"
        e_types = self.type if isinstance(self.type, list) else [self.type]
        return entity_type in e_types

    def has_types(self, entity_types: list[str], all_types: bool = False) -> bool:
        """
        Check if the entity has any or all of the specified types.
        """
        assert isinstance(entity_types, list), "Entity types must be a list"
        e_types = self.type if isinstance(self.type, list) else [self.type]
        if all_types:
            return all([t in e_types for t in entity_types])
        return any([t in e_types for t in entity_types])

    def __process_property__(self, name: str, data: object) -> object:
        if isinstance(data, dict) and '@id' in data:
            entity = self.metadata.get_entity(data['@id'])
            if entity is None:
                return ROCrateEntity(self, data)
            return entity
        return data

    def get_property(self, name: str, default=None) -> Union[str, ROCrateEntity]:
        data = self._raw_data.get(name, default)
        if data is None:
            return None
        if isinstance(data, list):
            return [self.__process_property__(name, _) for _ in data]
        return self.__process_property__(name, data)

    @property
    def raw_data(self) -> object:
        return self._raw_data

    def is_local(self) -> bool:
        return not self.is_remote()

    def is_available(self) -> bool:
        try:
            # check if the entity points to an external file
            if self.id.startswith("http"):
                return ROCrate.get_external_file_size(self.id) > 0

            # check if the entity is part of the local RO-Crate
            if self.ro_crate.uri.is_local_resource():
                # check if the file exists in the local file system
                if isinstance(self.ro_crate, ROCrateLocalFolder):
                    logger.debug("Checking the availability of a local entity in a local folder")
                    return self.ro_crate.has_file(self.id_as_path) \
                        or self.ro_crate.has_directory(self.id_as_path)
                # check if the file exists in the local zip file
                if isinstance(self.ro_crate, ROCrateLocalZip):
                    logger.debug("Checking the availability of a local entity in a local zip file")
                    # Skip the check for the root of a ZIP archive
                    if self.id == "./":
                        logger.debug("Skipping the check for the presence of the Data Entity '%s' within the RO-Crate "
                                     "as it is the root of a ZIP archive", self.id)
                        return True
                    return self.ro_crate.get_entry(str(self.id)) is not None

            # check if the entity is part of the remote RO-Crate
            if self.ro_crate.uri.is_remote_resource():
                return self.ro_crate.get_file_size(Path(self.id)) > 0
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False

        raise ROCrateInvalidURIError(uri=self.id, message="Could not determine the availability of the entity")

    def get_size(self) -> int:
        try:
            return self.metadata.ro_crate.get_file_size(Path(self.id))
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return 0

    def __str__(self) -> str:
        return f"Entity({self.id})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: ROCrateEntity) -> bool:
        if not isinstance(other, ROCrateEntity):
            return False
        return self.id == other.id


class ROCrateMetadata:

    METADATA_FILE_DESCRIPTOR = 'ro-crate-metadata.json'

    def __init__(self, ro_crate: ROCrate) -> None:
        self._ro_crate = ro_crate
        self._dict = None
        self._json: str = None

    @property
    def ro_crate(self) -> ROCrate:
        return self._ro_crate

    @property
    def size(self) -> int:
        try:
            return len(self.as_json())
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return 0

    def get_file_descriptor_entity(self) -> ROCrateEntity:
        metadata_file_descriptor = self.get_entity(self.METADATA_FILE_DESCRIPTOR)
        if not metadata_file_descriptor:
            raise ValueError("no metadata file descriptor in crate")
        return metadata_file_descriptor

    def get_root_data_entity(self) -> ROCrateEntity:
        metadata_file_descriptor = self.get_file_descriptor_entity()
        main_entity = metadata_file_descriptor.get_property('about')
        if not main_entity:
            raise ValueError("no main entity in metadata file descriptor")
        return main_entity

    def get_root_data_entity_conforms_to(self) -> Optional[list[str]]:
        try:
            root_data_entity = self.get_root_data_entity()
            result = root_data_entity.get_property('conformsTo', [])
            if result is None:
                return None
            if not isinstance(result, list):
                result = [result]
            return [_.id for _ in result]
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return None

    def get_main_workflow(self) -> ROCrateEntity:
        root_data_entity = self.get_root_data_entity()
        main_workflow = root_data_entity.get_property('mainEntity')
        if not main_workflow:
            raise ValueError("no main workflow in metadata file descriptor")
        return main_workflow

    def get_entity(self, entity_id: str) -> ROCrateEntity:
        for entity in self.as_dict().get('@graph', []):
            if entity.get('@id') == entity_id:
                return ROCrateEntity(self, entity)
        return None

    def get_entities(self) -> list[ROCrateEntity]:
        entities = []
        for entity in self.as_dict().get('@graph', []):
            entities.append(ROCrateEntity(self, entity))
        return entities

    def get_entities_by_type(self, entity_type: Union[str, list[str]]) -> list[ROCrateEntity]:
        entities = []
        for e in self.get_entities():
            if e.has_types(entity_type):
                entities.append(e)
        return entities

    def get_dataset_entities(self) -> list[ROCrateEntity]:
        return self.get_entities_by_type('Dataset')

    def get_file_entities(self) -> list[ROCrateEntity]:
        return self.get_entities_by_type('File')

    def get_data_entities(self, exclude_web_data_entities: bool = False) -> list[ROCrateEntity]:
        if not exclude_web_data_entities:
            return self.get_entities_by_type(['Dataset', 'File'])
        return [e for e in self.get_entities_by_type(['Dataset', 'File'])
                if not e.is_remote()]

    def get_web_data_entities(self) -> list[ROCrateEntity]:
        entities = []
        for entity in self.get_entities():
            if entity.has_type('File') or entity.has_type('Dataset'):
                if entity.is_remote():
                    entities.append(entity)
        return entities

    def get_conforms_to(self) -> Optional[list[str]]:
        try:
            file_descriptor = self.get_file_descriptor_entity()
            result = file_descriptor.get_property('conformsTo', [])
            if result is None:
                return None
            if not isinstance(result, list):
                result = [result]
            return [_.id for _ in result]
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return None

    def as_json(self) -> str:
        if not self._json:
            self._json = self.ro_crate.get_file_content(
                Path(self.METADATA_FILE_DESCRIPTOR), binary_mode=False)
        return self._json

    def as_dict(self) -> dict:
        if not self._dict:
            # if the dictionary is not cached, load it
            self._dict = json.loads(self.as_json())
        return self._dict

    def as_graph(self, publicID: str = None) -> Graph:
        if not self._graph:
            # if the graph is not cached, load it
            self._graph = Graph(base=publicID or self.ro_crate.uri)
            self._graph.parse(data=self.as_json, format='json-ld')
        return self._graph

    def __str__(self) -> str:
        return f"Metadata({self.ro_crate})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: ROCrateMetadata) -> bool:
        if not isinstance(other, ROCrateMetadata):
            return False
        return self.ro_crate == other.ro_crate


class ROCrate(ABC):

    """
    Base class for representing and interacting with a Research Object Crate (RO-Crate).
    """

    def __init__(self, uri: Union[str, Path, URI]):
        """
        Initialize the RO-Crate.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :raises ROCrateInvalidURIError: if the URI is invalid
        """

        # store the path to the crate
        self._uri = URI(uri)

        # cache the list of files
        self._files = None

        # initialize variables to cache the data
        self._dict: dict = None
        self._graph = None

        self._metadata = None

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

    @abstractmethod
    def size(self) -> int:
        """
        The size of the RO-Crate.

        :return: the size of the RO-Crate
        :rtype: int
        """
        pass

    @property
    @abstractmethod
    def list_files(self) -> list[Path]:
        """
        List all the files in the RO-Crate.

        :return: a list of file paths
        :rtype: list[Path]
        """
        pass

    def __parse_path__(self, path: Path) -> Path:
        assert path, "Path cannot be None"
        return ROCrateEntity.get_path_from_identifier(str(path), rocrate_path=self.uri.as_path())

    def has_descriptor(self) -> bool:
        """
        Check if the RO-Crate has a metadata descriptor file.

        :return: `True` if the RO-Crate has a metadata descriptor file, `False` otherwise
        :rtype: bool
        """
        return (self.uri.as_path().absolute() / self.metadata.METADATA_FILE_DESCRIPTOR).is_file()

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
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
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
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
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
        pass

    @abstractmethod
    def get_file_content(self, path: Path, binary_mode: bool = True) -> Union[str, bytes]:
        """
        Get the content of a file in the RO-Crate.

        :param path: the path to the file
        :type path: Path

        :param binary_mode: if `True`, return the file as a `bytes` object; otherwise, return it as a `str`
        :type binary_mode: bool

        :return: the content of the file
        :rtype: Union[str, bytes]
        """
        pass

    @staticmethod
    def get_external_file_content(uri: str, binary_mode: bool = True) -> Union[str, bytes]:
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
    def get_external_file_size(uri: str) -> int:
        """
        Get the size of an external file.

        :param uri: the URI of the file
        :type uri: str

        :return: the size of the file
        :rtype: int

        :raises requests.HTTPError: if the request fails
        """
        response = HttpRequester().head(str(uri))
        response.raise_for_status()
        return int(response.headers.get('Content-Length'))

    @staticmethod
    def new_instance(uri: Union[str, Path, URI]) -> 'ROCrate':
        """
        Create a new instance of the RO-Crate based on the URI.

        :param uri: the URI of the RO-Crate
        :type uri: Union[str, Path, URI]

        :return: a new instance of the RO-Crate
        :rtype: ROCrate

        :raises ROCrateInvalidURIError: if the URI is invalid
        """
        # check if the URI is valid
        validate_rocrate_uri(uri, silent=False)
        # create a new instance based on the URI
        if not isinstance(uri, URI):
            uri = URI(uri)
        # check if the URI is a local directory
        if uri.is_local_directory():
            return ROCrateLocalFolder(uri)
        # check if the URI is a local zip file
        if uri.is_local_file():
            return ROCrateLocalZip(uri)
        # check if the URI is a remote zip file
        if uri.is_remote_resource():
            return ROCrateRemoteZip(uri)
        # if the URI is not supported, raise an error
        raise ROCrateInvalidURIError(uri=uri, message="Unsupported RO-Crate URI")


class ROCrateLocalFolder(ROCrate):

    def __init__(self, path: Union[str, Path, URI]):
        super().__init__(path)

        # cache the list of files
        self._files = None

        # check if the path is a directory
        if not self.has_directory(self.uri.as_path()):
            raise ROCrateInvalidURIError(uri=path)

    @property
    def size(self) -> int:
        return sum(f.stat().st_size for f in self.list_files() if f.is_file())

    def list_files(self) -> list[Path]:
        if not self._files:
            self._files = []
            base_path = self.uri.as_path()
            for file in base_path.rglob('*'):
                if file.is_file():
                    self._files.append(base_path / file)
        return self._files

    def get_file_size(self, path: Path) -> int:
        path = self.__parse_path__(path)
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        return path.stat().st_size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> Union[str, bytes]:
        path = self.__parse_path__(path)
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes() if binary_mode else path.read_text()


class ROCrateLocalZip(ROCrate):

    def __init__(self, path: Union[str, Path, URI], init_zip: bool = True):
        super().__init__(path)

        # initialize the zip reference
        self._zipref = None
        if init_zip:
            self.__init_zip_reference__()

        # cache the list of files
        self._files = None

    def __del__(self):
        if self._zipref and self._zipref.fp is not None:
            self._zipref.close()
            del self._zipref

    @property
    def size(self) -> int:
        return self.uri.as_path().stat().st_size

    def __init_zip_reference__(self):
        path = self.uri.as_path()
        # check if the path is a file
        if not self.uri.as_path().is_file():
            raise ROCrateInvalidURIError(uri=path)
        # check if the file is a zip file
        if not self.uri.as_path().suffix == '.zip':
            raise ROCrateInvalidURIError(uri=path)
        self._zipref = zipfile.ZipFile(path)
        logger.debug("Initialized zip reference: %s", self._zipref)

    def __get_file_info__(self, path: Path) -> zipfile.ZipInfo:
        return self._zipref.getinfo(str(path))

    def has_descriptor(self) -> bool:
        return ROCrateMetadata.METADATA_FILE_DESCRIPTOR in [str(_.name) for _ in self.list_files()]

    def has_file(self, path: Path) -> bool:
        if path in self.list_files():
            info = self.__get_file_info__(path)
            return not info.is_dir()
        return False

    def has_directory(self, path: Path) -> bool:
        if path in self.list_files():
            info = self.__get_file_info__(path)
            return info.is_dir()
        return False

    def list_files(self) -> list[Path]:
        if not self._files:
            self._files = []
            for file in self._zipref.namelist():
                self._files.append(Path(file))
        return self._files

    def list_entries(self) -> list[zipfile.ZipInfo]:
        self._zipref.infolist()

    def get_entry(self, path: Path) -> zipfile.ZipInfo:
        """
        Return the ZipInfo object for the specified path.
        """
        return self.__get_file_info__(path)

    def get_file_size(self, path: Path) -> int:
        return self._zipref.getinfo(str(path)).file_size

    def get_file_content(self, path: Path, binary_mode: bool = True) -> Union[str, bytes]:
        if not self.has_file(path):
            raise FileNotFoundError(f"File not found: {path}")
        data = self._zipref.read(str(path))
        return data if binary_mode else data.decode('utf-8')


class ROCrateRemoteZip(ROCrateLocalZip):

    def __init__(self, path: Union[str, Path, URI]):
        super().__init__(path, init_zip=False)

        logger.debug("Size: %s", self.size)

        # # initialize the zip reference
        self.__init_zip_reference__()

    def __init_zip_reference__(self):
        url = str(self.uri)

        # check if the URI is available
        if not self.uri.is_available():
            raise ROCrateInvalidURIError(uri=url, message="URI is not available")

        # Step 1: Fetch the last 22 bytes to find the EOCD record
        eocd_data = self.__fetch_range__(url, -22, '')

        # Step 2: Find the EOCD record
        eocd_offset = self.__find_eocd__(eocd_data)

        # Step 3: Fetch the EOCD and parse it
        eocd_full_data = self.__fetch_range__(url, -22 - eocd_offset, -1)
        central_directory_offset, central_directory_size = self.__parse_eocd__(eocd_full_data)

        # Step 4: Fetch the central directory
        central_directory_data = self.__fetch_range__(url, central_directory_offset,
                                                      central_directory_offset + central_directory_size - 1)
        # Step 5: Parse the central directory and return the zip file
        self._zipref = zipfile.ZipFile(io.BytesIO(central_directory_data))

    @property
    def size(self) -> int:
        response = HttpRequester().head(str(self.uri))
        response.raise_for_status()  # Check if the request was successful
        file_size = response.headers.get('Content-Length')
        if file_size is not None:
            return int(file_size)
        else:
            raise Exception("Could not determine the file size from the headers")

    @staticmethod
    def __fetch_range__(uri: str, start, end):
        headers = {'Range': f'bytes={start}-{end}'}
        response = HttpRequester().get(uri, headers=headers)
        response.raise_for_status()
        return response.content

    @staticmethod
    def __find_eocd__(data):
        eocd_signature = b'PK\x05\x06'
        eocd_offset = data.rfind(eocd_signature)
        if eocd_offset == -1:
            raise Exception("EOCD not found")
        return eocd_offset

    @staticmethod
    def __parse_eocd__(data):
        eocd_size = struct.calcsize('<4s4H2LH')
        eocd = struct.unpack('<4s4H2LH', data[-eocd_size:])
        central_directory_size = eocd[5]
        central_directory_offset = eocd[6]
        return central_directory_offset, central_directory_size
