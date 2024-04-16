import inspect
import logging
import os
import re
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional

import toml
from rdflib import Graph

from . import constants, errors

# current directory
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


# set up logging
logger = logging.getLogger(__name__)

# Read the pyproject.toml file
config = toml.load(Path(CURRENT_DIR).parent / "pyproject.toml")


def get_version() -> str:
    """
    Get the version of the package

    :return: The version
    """
    return config["tool"]["poetry"]["version"]


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


def get_default_profiles_paths() -> list[Path]:
    """
    Get the paths to the profiles directory

    :return: The paths to the profiles directory
    """
    return [
        Path("rocrate_profiles"),
        Path.home() / ".config/rocrate-validator/rocrate_profiles",
        Path(CURRENT_DIR).parent / "rocrate_profiles"
    ]


def get_profiles_path(not_exist_ok: bool = True) -> Path:
    """
    Get the path to the profiles directory from the default paths

    :param not_exist_ok: If True, return the path even if it does not exist

    :return: The path to the profiles directory
    """
    profiles_path = None
    # Get the default profiles paths
    default_profiles_paths = get_default_profiles_paths()
    logger.debug("Default profiles paths: %r", default_profiles_paths)
    for path in default_profiles_paths:
        if path.exists():
            profiles_path = path
            break
    # Check if the profiles directory is found
    if not profiles_path:
        # If the profiles directory is not found, raise an error
        if not not_exist_ok:
            # Raise an error if the profiles directory provided with the package is not found
            raise errors.ProfilesDirectoryNotFound(profiles_path=str(default_profiles_paths[-1]))
        else:
            # Use the last path as the profiles directory, i.e., the one provided with the package
            profiles_path = default_profiles_paths[-1]
    # Return the profiles directory
    return profiles_path


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
