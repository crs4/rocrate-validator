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

from collections.abc import Iterable
from posixpath import relpath
from urllib.parse import urljoin, urlsplit, urlunsplit

from rdflib import Graph, URIRef
from rdflib.term import Node

from rocrate_validator import constants
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.paths import list_graph_paths

# set up logging
logger = logging.getLogger(__name__)


PREPARED_PROFILE_BASE = "https://example.invalid/rocrate-validator/prepared/crate/"


def rebase_node(node: Node, base_mappings: Iterable[tuple[str, str]]) -> Node:
    """
    Return ``node`` with the first matching URI base replaced.

    Mappings must be ordered from the most specific source base to the least
    specific one. Blank nodes and literals are unchanged.
    """

    if isinstance(node, URIRef):
        value = str(node)
        for source_base, target_base in base_mappings:
            if value.startswith(source_base):
                return URIRef(f"{target_base}{value[len(source_base) :]}")

        # Parsing resolves parent-relative references (for example
        # ``../target``) against their source base, so the resulting URI no
        # longer starts with that base. Preserve the reference's relative path
        # when moving it to the prepared base. Restrict this fallback to the
        # same URI authority; unrelated hosts are never affected.
        value_parts = urlsplit(value)
        for source_base, target_base in base_mappings:
            source_parts = urlsplit(source_base)
            if (value_parts.scheme, value_parts.netloc) != (source_parts.scheme, source_parts.netloc):
                continue
            relative_path = relpath(value_parts.path, source_parts.path)
            rebased = urlsplit(urljoin(target_base, relative_path))
            return URIRef(
                urlunsplit((rebased.scheme, rebased.netloc, rebased.path, value_parts.query, value_parts.fragment))
            )
        return node
    return node


def rebase_graph(
    graph: Graph,
    base_mappings: Iterable[tuple[str, str]],
    *,
    preserve_nodes: Iterable[Node] = (),
    rebase_objects_for: Iterable[Node] = (),
) -> Graph:
    """
    Copy a graph while replacing selected URI bases.

    ``preserve_nodes`` keeps structural identifiers stable while their constraint
    values are rebased (for example SHACL shape identifiers versus target nodes).
    """

    mappings = tuple(base_mappings)
    preserved = frozenset(preserve_nodes)
    rebased_object_predicates = frozenset(rebase_objects_for)

    def transform(node: Node, *, force_rebase: bool = False) -> Node:
        return node if node in preserved and not force_rebase else rebase_node(node, mappings)

    rebased = Graph()
    for prefix, namespace in graph.namespaces():
        rebased.bind(prefix, namespace)
    for subject, predicate, object_ in graph:
        rebased.add(
            (
                transform(subject),
                transform(predicate),
                transform(object_, force_rebase=predicate in rebased_object_predicates),
            )
        )
    return rebased


def get_full_graph(
    graphs_dir: str, serialization_format: constants.RDF_SERIALIZATION_FORMATS_TYPES = "turtle", publicID: str = "."
) -> Graph:
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


def extract_base_from_jsonld(json_data: dict) -> str | None:
    """
    Extract the @base from the @context of a JSON-LD document.

    The @context can be:
    - A dictionary (e.g., {"@base": "http://example.org/"})
    - A list of contexts (e.g., [{"@base": "http://example.org/"}, "https://schema.org"])

    :param json_data: The JSON-LD data as a dictionary
    :return: The @base value if found, None otherwise
    """
    context = json_data.get("@context")

    if not context:
        return None

    # If @context is a dictionary, look for @base directly
    if isinstance(context, dict):
        return context.get("@base")

    # If @context is a list, look for @base in each context item
    if isinstance(context, list):
        for ctx in context:
            if isinstance(ctx, dict) and "@base" in ctx:
                return ctx["@base"]

    return None
