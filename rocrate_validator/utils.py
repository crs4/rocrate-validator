import logging
import os
from pathlib import Path
from typing import List

from rdflib import Graph

from . import constants, errors

# current directory
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


# set up logging
logger = logging.getLogger(__name__)


def get_file_descriptor_path(rocrate_path: Path) -> Path:
    """
    Get the path to the metadata file in the RO-Crate

    :param rocrate_path: The path to the RO-Crate
    :return: The path to the metadata file
    """
    return Path(rocrate_path) / constants.ROCRATE_METADATA_FILE


def get_format_extension(format: constants.RDF_SERIALIZATION_FORMATS_TYPES) -> str:
    """
    Get the file extension for the RDF serialization format

    :param format: The RDF serialization format
    :return: The file extension

    :raises InvalidSerializationFormat: If the format is not valid
    """
    try:
        return constants.RDF_SERIALIZATION_FILE_FORMAT_MAP[format]
    except KeyError:
        logger.error("Invalid RDF serialization format: %s", format)
        raise errors.InvalidSerializationFormat(format)


def get_all_files(
        directory: str = '.',
        format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle") -> List[str]:
    """
    Get all the files in the directory matching the format.

    :param directory: The directory to search
    :param format: The RDF serialization format
    :return: A list of file paths
    """
    # initialize an empty list to store the file paths
    file_paths = []

    # extension
    extension = get_format_extension(format)

    # iterate through the directory and subdirectories
    for root, dirs, files in os.walk(directory):
        # iterate through the files
        for file in files:
            # check if the file has a .ttl extension
            if file.endswith(extension):
                # append the file path to the list
                file_paths.append(os.path.join(root, file))
    # return the list of file paths
    return file_paths


def get_graphs_paths(
        graphs_dir: str = CURRENT_DIR, format="turtle") -> List[str]:
    """
    Get the paths to all the graphs in the directory

    :param graphs_dir: The directory containing the graphs
    :param format: The RDF serialization format
    :return: A list of graph paths
    """
    return get_all_files(directory=graphs_dir, format=format)


def get_full_graph(
        graphs_dir: str,
        format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle",
        publicID: str = ".") -> Graph:
    """
    Get the full graph from the directory

    :param graphs_dir: The directory containing the graphs
    :param format: The RDF serialization format
    :param publicID: The public ID
    :return: The full graph
    """
    full_graph = Graph()
    graphs_paths = get_graphs_paths(graphs_dir, format=format)
    for graph_path in graphs_paths:
        full_graph.parse(graph_path, format="turtle", publicID=publicID)
        logger.debug("Loaded triples from %s", graph_path)
    return full_graph
