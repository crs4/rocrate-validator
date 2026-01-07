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

import os
from pathlib import Path

from rocrate_validator import constants, errors
from rocrate_validator.utils import log as logging

# current directory
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


# set up logging
logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """
    Get the path to the default configuration file

    :return: The path to the configuration file
    """
    return Path(CURRENT_DIR).parent.parent / "pyproject.toml"


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
    return Path(CURRENT_DIR).parent / constants.DEFAULT_PROFILES_PATH


def list_matching_file_paths(
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


def list_graph_paths(graphs_dir: str = CURRENT_DIR,
                     serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle") -> list[str]:
    """
    Get the paths to all the graphs in the directory

    :param graphs_dir: The directory containing the graphs
    :param format: The RDF serialization format
    :return: A list of graph paths
    """
    return list_matching_file_paths(directory=graphs_dir, serialization_format=serialization_format)


def shorten_path(p: Path) -> str:
    """"
    Shorten the path to a relative path if possible, otherwise return the absolute path.

    :param p: The path to shorten
    :return: The shortened path
    :raises ValueError: If the path is not a valid Path object
    """
    if not isinstance(p, Path):
        raise ValueError("The path must be a Path or ParseResult object")

    try:
        cwd = Path.cwd()
        rel = p.relative_to(cwd)
        # Use relative path only if it's shorter than absolute
        return str(rel) if len(str(rel)) < len(str(p)) else str(p)
    except Exception:
        return str(p)
