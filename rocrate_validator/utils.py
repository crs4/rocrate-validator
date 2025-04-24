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

import atexit
import inspect
import os
import random
import re
import string
import sys
import threading
from importlib import import_module
from pathlib import Path
from typing import Optional, Union
from urllib.parse import ParseResult, parse_qsl, urlparse

import requests
import toml
from rdflib import Graph

import rocrate_validator.log as logging
from rocrate_validator import constants, errors

# current directory
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


# set up logging
logger = logging.getLogger(__name__)

# Read the pyproject.toml file
config = toml.load(Path(CURRENT_DIR).parent / "pyproject.toml")


def run_git_command(command: list[str]) -> Optional[str]:
    """
    Run a git command and return the output

    :param command: The git command
    :return: The output of the command
    """
    import subprocess

    try:
        output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode().strip()
        return output
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)
        return None


def get_git_commit() -> str:
    """
    Get the git commit hash

    :return: The git commit hash
    """
    return run_git_command(['git', 'rev-parse', '--short', 'HEAD'])


def is_release_tag(git_sha: str) -> bool:
    """
    Check whether a git sha corresponds to a release tag

    :param git_sha: The git sha
    :return: True if the sha corresponds to a release tag, False otherwise
    """
    tags = run_git_command(['git', 'tag', '--points-at', git_sha])
    return bool(tags)


def get_commit_distance(tag: Optional[str] = None) -> int:
    """
    Get the distance in commits between the current commit and the last tag

    :return: The distance in commits
    """
    if not tag:
        tag = get_last_tag()
    try:
        return int(run_git_command(['git', 'rev-list', '--count', f"{tag}..HEAD"]))
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(e)

    return 0


def get_last_tag() -> str:
    """
    Get the last tag in the git repository

    :return: The last tag
    """
    return run_git_command(['git', 'describe', '--tags', '--abbrev=0'])

# write  a function to checks whether the are any uncommitted changes in the repository


def has_uncommitted_changes() -> bool:
    """
    Check whether there are any uncommitted changes in the repository

    :return: True if there are uncommitted changes, False otherwise
    """
    return bool(run_git_command(['git', 'status', '--porcelain']))


def get_version() -> str:
    """
    Get the version of the package

    :return: The version
    """
    version = None
    declared_version = config["tool"]["poetry"]["version"]
    commit_sha = get_git_commit()
    is_release = is_release_tag(commit_sha)
    latest_tag = get_last_tag()
    if is_release:
        if declared_version != latest_tag:
            logger.warning("The declared version %s is different from the last tag %s", declared_version, latest_tag)
        version = latest_tag
    else:
        commit_distance = get_commit_distance(latest_tag)
        if commit_sha:
            version = f"{declared_version}_{commit_sha}+{commit_distance}"
        else:
            version = declared_version
    dirty = has_uncommitted_changes()
    return f"{version}-dirty" if dirty else version


def get_min_python_version() -> tuple[int, int, Optional[int]]:
    """
    Get the minimum Python version required by the package

    :return: The minimum Python version
    """
    min_version_str = config["tool"]["poetry"]["dependencies"]["python"]
    assert min_version_str, "The minimum Python version is required"
    # remove any non-digit characters
    min_version_str = re.sub(r'[^\d.]+', '', min_version_str)
    # convert the version string to a tuple
    min_version = tuple(map(int, min_version_str.split(".")))
    logger.debug(f"Minimum Python version: {min_version}")
    return min_version


def check_python_version() -> bool:
    """
    Check if the current Python version meets the minimum requirements
    """
    return sys.version_info >= get_min_python_version()


def get_config(property: Optional[str] = None) -> dict:
    """
    Get the configuration for the package or a specific property

    :param property_name: The property name
    :return: The configuration
    """
    if property:
        return config["tool"]["rocrate_validator"][property]
    return config["tool"]["rocrate_validator"]


def get_file_descriptor_path(rocrate_path: Path) -> Path:
    """
    Get the path to the metadata file in the RO-Crate

    :param rocrate_path: The path to the RO-Crate
    :return: The path to the metadata file
    """
    return Path(rocrate_path) / constants.ROCRATE_METADATA_FILE


def get_profiles_path() -> Path:
    """
    Get the path to the profiles directory from the default paths

    :param not_exist_ok: If True, return the path even if it does not exist

    :return: The path to the profiles directory
    """
    return Path(CURRENT_DIR) / constants.DEFAULT_PROFILES_PATH


def get_format_extension(serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES) -> str:
    """
    Get the file extension for the RDF serialization format

    :param format: The RDF serialization format
    :return: The file extension

    :raises InvalidSerializationFormat: If the format is not valid
    """
    try:
        return constants.RDF_SERIALIZATION_FILE_FORMAT_MAP[serialization_format]
    except KeyError as exc:
        logger.error("Invalid RDF serialization format: %s", serialization_format)
        raise errors.InvalidSerializationFormat(serialization_format) from exc


def get_all_files(
        directory: str = '.',
        serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle") -> list[str]:
    """
    Get all the files in the directory matching the format.

    :param directory: The directory to search
    :param format: The RDF serialization format
    :return: A list of file paths
    """
    # initialize an empty list to store the file paths
    file_paths = []

    # extension
    extension = get_format_extension(serialization_format)

    # iterate through the directory and subdirectories
    for root, _, files in os.walk(directory):
        # iterate through the files
        for file in files:
            # check if the file has a .ttl extension
            if file.endswith(extension):
                # append the file path to the list
                file_paths.append(os.path.join(root, file))
    # return the list of file paths
    return file_paths


def get_graphs_paths(graphs_dir: str = CURRENT_DIR,
                     serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle") -> list[str]:
    """
    Get the paths to all the graphs in the directory

    :param graphs_dir: The directory containing the graphs
    :param format: The RDF serialization format
    :return: A list of graph paths
    """
    return get_all_files(directory=graphs_dir, serialization_format=serialization_format)


def get_full_graph(
        graphs_dir: str,
        serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle",
        publicID: str = ".") -> Graph:
    """
    Get the full graph from the directory

    :param graphs_dir: The directory containing the graphs
    :param format: The RDF serialization format
    :param publicID: The public ID
    :return: The full graph
    """
    full_graph = Graph()
    graphs_paths = get_graphs_paths(graphs_dir, serialization_format=serialization_format)
    for graph_path in graphs_paths:
        full_graph.parse(graph_path, format="turtle", publicID=publicID)
        logger.debug("Loaded triples from %s", graph_path)
    return full_graph


def get_classes_from_file(file_path: Path,
                          filter_class: Optional[type] = None,
                          class_name_suffix: Optional[str] = None) -> dict[str, type]:
    """Get all classes in a Python file """
    # ensure the file path is a Path object
    assert file_path, "The file path is required"
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Check if the file is a Python file
    if not file_path.exists():
        raise ValueError("The file does not exist")

    # Check if the file is a Python file
    if file_path.suffix != ".py":
        raise ValueError("The file is not a Python file")

    # Get the module name from the file path
    module_name = file_path.stem
    logger.debug("Module: %r", module_name)

    # Add the directory containing the file to the system path
    sys.path.insert(0, os.path.dirname(file_path))

    # Import the module
    module = import_module(module_name)
    logger.debug("Module: %r", module)

    # Get all classes in the module that are subclasses of filter_class
    classes = {name: cls for name, cls in inspect.getmembers(module, inspect.isclass)
               if cls.__module__ == module_name
               and (not class_name_suffix or cls.__name__.endswith(class_name_suffix))
               and (not filter_class or (issubclass(cls, filter_class) and cls != filter_class))}

    return classes


def get_requirement_name_from_file(file: Path, check_name: Optional[str] = None) -> str:
    """
    Get the requirement name from the file

    :param file: The file
    :return: The requirement name
    """
    assert file, "The file is required"
    if not isinstance(file, Path):
        file = Path(file)
    base_name = to_camel_case(file.stem)
    if check_name:
        return f"{base_name}.{check_name.replace('Check', '')}"
    return base_name


def get_requirement_class_by_name(requirement_name: str) -> type:
    """
    Dynamically load the module of the class and return the class"""

    # Split the requirement name into module and class
    module_name, class_name = requirement_name.rsplit(".", 1)
    logger.debug("Module: %r", module_name)
    logger.debug("Class: %r", class_name)

    # convert the module name to a path
    module_path = module_name.replace(".", "/")
    # add the path to the system path
    sys.path.insert(0, os.path.dirname(module_path))

    # Import the module
    module = import_module(module_name)

    # Get the class from the module
    return getattr(module, class_name)


def to_camel_case(snake_str: str) -> str:
    """
    Convert a snake case string to camel case

    :param snake_str: The snake case string
    :return: The camel case string
    """
    components = re.split('_|-', snake_str)
    return components[0].capitalize() + ''.join(x.title() for x in components[1:])


class HttpRequester:
    """
    A singleton class to handle HTTP requests
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.debug(f"Creating instance of {cls.__name__}")
                    cls._instance = super(HttpRequester, cls).__new__(cls)
                    atexit.register(cls._instance.__del__)
                    logger.debug(f"Instance created: {cls._instance.__class__.__name__}")
        return cls._instance

    def __init__(self):
        # check if the instance is already initialized
        if not hasattr(self, "_initialized"):
            # check if the instance is already initialized
            with self._lock:
                if not getattr(self, "_initialized", False):
                    # set the initialized flag
                    self._initialized = False
                    # initialize the session
                    self.__initialize_session__()
                    # set the initialized flag
                    self._initialized = True
        else:
            logger.debug(f"Instance of {self} already initialized")

    def __initialize_session__(self):
        # initialize the session
        self.session = None
        logger.debug(f"Initializing instance of {self.__class__.__name__}")
        assert not self._initialized, "Session already initialized"
        # check if requests_cache is installed
        # and set up the cached session
        try:
            if constants.DEFAULT_HTTP_CACHE_TIMEOUT > 0:
                from requests_cache import CachedSession

                # Generate a random path for the cache
                # to avoid conflicts with other instances
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                # Initialize the session with a cache
                self.session = CachedSession(
                    # Cache name with random suffix
                    cache_name=f"{constants.DEFAULT_HTTP_CACHE_PATH_PREFIX}_{random_suffix}",
                    expire_after=constants.DEFAULT_HTTP_CACHE_TIMEOUT,  # Cache expiration time in seconds
                    backend='sqlite',  # Use SQLite backend
                    allowable_methods=('GET',),  # Cache GET
                    allowable_codes=(200, 302, 404)  # Cache responses with these status codes
                )
        except ImportError:
            logger.warning("requests_cache is not installed. Using requests instead.")
        except Exception as e:
            logger.error("Error initializing requests_cache: %s", e)
            logger.warning("Using requests instead of requests_cache")
        # if requests_cache is not installed or an error occurred, use requests
        # instead of requests_cache
        # and create a new session
        if not self.session:
            logger.debug("Using requests instead of requests_cache")
            self.session = requests.Session()

    def __del__(self):
        """
        Destructor to clean up the cache file used by CachedSession.
        """
        logger.debug(f"Deleting instance of {self.__class__.__name__}")
        if self.session and hasattr(self.session, 'cache') and self.session.cache:
            try:
                logger.debug(f"Deleting cache directory: {self.session.cache.cache_name}")
                cache_path = f"{self.session.cache.cache_name}.sqlite"
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    logger.debug(f"Deleted cache directory: {cache_path}")
            except Exception as e:
                logger.error(f"Error deleting cache directory: {e}")

    def __getattr__(self, name):
        """
        Delegate HTTP methods to the session object.

        :param name: The name of the method to call.
        :return: The method from the session object.
        """
        if name.upper() in {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"}:
            return getattr(self.session, name.lower())
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class URI:

    REMOTE_SUPPORTED_SCHEMA = ('http', 'https', 'ftp')

    def __init__(self, uri: Union[str, Path]):
        self._uri = uri = str(uri)
        try:
            # map local path to URI with file scheme
            if not re.match(r'^\w+://', uri):
                uri = f"file://{uri}"
            # parse the value to extract the scheme
            self._parse_result = urlparse(uri)
            assert self.scheme in self.REMOTE_SUPPORTED_SCHEMA + ('file',), "Invalid URI scheme"
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(e)
            raise ValueError("Invalid URI: %s" % uri)

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def base_uri(self) -> str:
        return f"{self.scheme}://{self._parse_result.netloc}{self._parse_result.path}"

    @property
    def parse_result(self) -> ParseResult:
        return self._parse_result

    @property
    def scheme(self) -> str:
        return self._parse_result.scheme

    @property
    def fragment(self) -> Optional[str]:
        fragment = self._parse_result.fragment
        return fragment if fragment else None

    def get_scheme(self) -> str:
        return self._parse_result.scheme

    def get_netloc(self) -> str:
        return self._parse_result.netloc

    def get_path(self) -> str:
        return self._parse_result.path

    def get_query_string(self) -> str:
        return self._parse_result.query

    def get_query_param(self, param: str) -> Optional[str]:
        query_params = dict(parse_qsl(self._parse_result.query))
        return query_params.get(param)

    def as_path(self) -> Path:
        if not self.is_local_resource():
            raise ValueError("URI is not a local resource")
        return Path(self._uri)

    def is_remote_resource(self) -> bool:
        return self.scheme in self.REMOTE_SUPPORTED_SCHEMA

    def is_local_resource(self) -> bool:
        return not self.is_remote_resource()

    def is_local_directory(self) -> bool:
        return self.is_local_resource() and self.as_path().is_dir()

    def is_local_file(self) -> bool:
        return self.is_local_resource() and self.as_path().is_file()

    def is_available(self) -> bool:
        """Check if the resource is available"""
        if self.is_remote_resource():
            try:
                response = HttpRequester().head(self._uri, allow_redirects=True)
                return response.status_code in (200, 302)
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(e)
                return False
        return Path(self._uri).exists()

    def __str__(self):
        return self._uri

    def __repr__(self):
        return f"URI(uri={self._uri})"

    def __eq__(self, other):
        if isinstance(other, URI):
            return self._uri == other.uri
        return False

    def __hash__(self):
        return hash(self._uri)


def validate_rocrate_uri(uri: Union[str, URI], silent: bool = False) -> bool:
    """
    Validate the RO-Crate URI

    :param uri: The RO-Crate URI
    :param silent: If True, do not raise an exception
    :return: True if the URI is valid, False otherwise
    """
    try:
        assert uri, "The RO-Crate URI is required"
        assert isinstance(uri, (str, URI)), "The RO-Crate URI must be a string or URI object"
        try:
            # parse the value to extract the scheme
            uri = URI(uri) if isinstance(uri, str) else uri
            # check if the URI is a remote resource or local directory or local file
            if not uri.is_remote_resource() and not uri.is_local_directory() and not uri.is_local_file():
                raise errors.ROCrateInvalidURIError(uri)
            # check if the local file is a ZIP file
            if uri.is_local_file() and uri.as_path().suffix != ".zip":
                raise errors.ROCrateInvalidURIError(uri)
            # check if the resource is available
            if not uri.is_available():
                raise errors.ROCrateInvalidURIError(uri, message=f"The RO-crate at the URI \"{uri}\" is not available")
            return True
        except ValueError as e:
            logger.error(e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            raise errors.ROCrateInvalidURIError(uri)
    except Exception as e:
        if not silent:
            raise e
        return False


class MapIndex:

    def __init__(self, name: str, unique: bool = False):
        self.name = name
        self.unique = unique


class MultiIndexMap:
    def __init__(self, key: str = "id", indexes: list[MapIndex] = None):
        self._key = key
        # initialize an empty dictionary to store the indexes
        self._indices: list[MapIndex] = {}
        if indexes:
            for index in indexes:
                self.add_index(index)
        # initialize an empty dictionary to store the data
        self._data = {}

    @property
    def key(self) -> str:
        return self._key

    @property
    def keys(self) -> list[str]:
        return list(self._data.keys())

    @property
    def indices(self) -> list[str]:
        return list(self._indices.keys())

    def add_index(self, index: MapIndex):
        self._indices[index.name] = {"__meta__": index}

    def remove_index(self, index_name: str):
        self._indices.pop(index_name)

    def get_index(self, index_name: str) -> MapIndex:
        return self._indices.get(index_name)["__meta__"]

    def add(self, key, obj, **indices):
        self._data[key] = obj
        for index_name, index_value in indices.items():
            index = self.get_index(index_name)
            assert isinstance(index, MapIndex), f"Index {index_name} does not exist"
            if index_name in self._indices:
                if index_value not in self._indices[index_name]:
                    self._indices[index_name][index_value] = set() if not index.unique else key
                if not index.unique:
                    self._indices[index_name][index_value].add(key)

    def remove(self, key):
        obj = self._data.pop(key)
        for index_name, index in self._indices.items():
            index_value = getattr(obj, index_name)
            if index_value in index:
                index[index_value].remove(key)

    def values(self):
        return self._data.values()

    def get_by_key(self, key):
        return self._data.get(key)

    def get_by_index(self, index_name, index_value):
        if index_name == self._key:
            return self._data.get(index_value)
        index = self.get_index(index_name)
        assert isinstance(index, MapIndex), f"Index {index_name} does not exist"
        if index.unique:
            key = self._indices.get(index_name, {}).get(index_value)
            return self._data.get(key)
        keys = self._indices.get(index_name, {}).get(index_value, set())
        return [self._data[key] for key in keys]
