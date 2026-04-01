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
from typing import Optional

from rdflib import Graph

from rocrate_validator import constants
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.paths import list_graph_paths

# set up logging
logger = logging.getLogger(__name__)


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
    graphs_paths = list_graph_paths(graphs_dir, serialization_format=serialization_format)
    for graph_path in graphs_paths:
        full_graph.parse(graph_path, format="turtle", publicID=publicID)
        logger.debug("Loaded triples from %s", graph_path)
    return full_graph


def extract_base_from_jsonld(json_data: dict) -> Optional[str]:
    """
    Extract the @base from the @context of a JSON-LD document.

    The @context can be:
    - A dictionary (e.g., {"@base": "http://example.org/"})
    - A list of contexts (e.g., [{"@base": "http://example.org/"}, "https://schema.org"])

    :param json_data: The JSON-LD data as a dictionary
    :return: The @base value if found, None otherwise
    """
    context = json_data.get('@context')

    if not context:
        return None

    # If @context is a dictionary, look for @base directly
    if isinstance(context, dict):
        return context.get('@base')

    # If @context is a list, look for @base in each context item
    if isinstance(context, list):
        for ctx in context:
            if isinstance(ctx, dict) and '@base' in ctx:
                return ctx['@base']

    return None
