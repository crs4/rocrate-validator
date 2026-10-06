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

import re
from collections.abc import Iterable
from pathlib import Path
from posixpath import commonpath, relpath
from urllib.parse import urljoin, urlsplit, urlunsplit

from rdflib import Graph, URIRef
from rdflib.parser import create_input_source
from rdflib.plugins.parsers.notation3 import RDFSink, SinkParser
from rdflib.term import Node

from rocrate_validator import constants
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.paths import list_graph_paths

# set up logging
logger = logging.getLogger(__name__)


PREPARED_PROFILE_BASE = "https://example.invalid/rocrate-validator/prepared/crate/"
_PREFIX_DECLARATION = re.compile(r"@?prefix\b\s+([^:\s]*):\s*<([^>]*)>", re.IGNORECASE)


def _prefix_declaration(argstr: str, index: int) -> tuple[str, str] | None:
    directive_index = argstr[index:].lstrip() if index >= 0 else ""
    match = _PREFIX_DECLARATION.match(directive_index)
    if match is None:
        return None
    prefix, namespace = match.group(1), match.group(2)
    assert prefix is not None and namespace is not None
    return prefix, namespace


def _is_relative_iri(reference: str) -> bool:
    parts = urlsplit(reference)
    return not parts.scheme and not parts.netloc


class _TurtleProvenanceParser(SinkParser):
    """RDFLib Turtle parser that records URI terms originating in relative syntax."""

    def __init__(self, store: RDFSink, base_uri: str):
        super().__init__(store, baseURI=base_uri, turtle=True)
        self.relative_iris: set[Node] = set()
        self.relative_prefixes: set[str] = set()

    def _record_prefix_declaration(self, declaration: tuple[str, str] | None, parsed_at: int) -> None:
        if parsed_at < 0 or declaration is None:
            return
        prefix, namespace = declaration
        if _is_relative_iri(namespace):
            self.relative_prefixes.add(prefix)
        else:
            self.relative_prefixes.discard(prefix)

    def directive(self, argstr: str, index: int) -> int:
        declaration = _prefix_declaration(argstr, index)
        parsed_at = super().directive(argstr, index)
        self._record_prefix_declaration(declaration, parsed_at)
        return parsed_at

    def sparqlDirective(self, argstr: str, index: int) -> int:
        declaration = _prefix_declaration(argstr, index)
        parsed_at = super().sparqlDirective(argstr, index)
        self._record_prefix_declaration(declaration, parsed_at)
        return parsed_at

    def uri_ref2(self, argstr: str, index: int, result: list) -> int:
        qname: list = []
        self.qname(argstr, index, qname)
        relative_qname = bool(qname and qname[0][0] in self.relative_prefixes)
        start = self.skipSpace(argstr, index)
        relative_ref = start >= 0 and argstr[start] == "<"
        if relative_ref:
            end = argstr.find(">", start + 1)
            if end >= 0:
                relative_ref = _is_relative_iri(argstr[start + 1 : end])

        previous_length = len(result)
        parsed_at = super().uri_ref2(argstr, index, result)
        if parsed_at >= 0 and len(result) > previous_length and (relative_ref or relative_qname):
            value = result[-1]
            if isinstance(value, Node):
                self.relative_iris.add(value)
        return parsed_at


def parse_turtle_with_relative_iris(file_path: str | Path, public_id: str | None = None) -> tuple[Graph, set[Node]]:
    """Parse a Turtle file and retain URI terms written as relative references."""

    source = create_input_source(source=file_path, publicID=public_id)
    graph = Graph()
    try:
        base_uri = graph.absolutize(source.getPublicId() or source.getSystemId() or "")
        parser = _TurtleProvenanceParser(RDFSink(graph), base_uri)
        stream = source.getCharacterStream() or source.getByteStream()
        source_text = stream.read()
        if isinstance(source_text, bytes):
            source_text = source_text.decode("utf-8")
        source_text = source_text.removeprefix("\ufeff")

        from io import StringIO  # noqa: PLC0415

        parser.loadStream(StringIO(source_text))
        for prefix, namespace in parser._bindings.items():
            graph.bind(prefix, namespace)
        return graph, parser.relative_iris
    finally:
        source.close()


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

            # A root-relative identifier is anchored at the URI authority, not
            # at the crate directory. Preserve its absolute path while mapping
            # the URI scheme/authority to the current crate's URI space.
            if value_parts.path.startswith("/") and commonpath((source_parts.path, value_parts.path)) == "/":
                target_parts = urlsplit(target_base)
                return URIRef(
                    urlunsplit(
                        (
                            target_parts.scheme,
                            target_parts.netloc,
                            value_parts.path,
                            value_parts.query,
                            value_parts.fragment,
                        )
                    )
                )

            relative_path = relpath(value_parts.path, source_parts.path)
            if value_parts.path.endswith("/") and not relative_path.endswith("/"):
                relative_path += "/"
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
    rebase_nodes: Iterable[Node] | None = None,
) -> Graph:
    """
    Copy a graph while replacing selected URI bases.

    ``preserve_nodes`` keeps structural identifiers stable while their constraint
    values are rebased (for example SHACL shape identifiers versus target nodes).
    """

    mappings = tuple(base_mappings)
    preserved = frozenset(preserve_nodes)
    rebased_object_predicates = frozenset(rebase_objects_for)
    relative_nodes = None if rebase_nodes is None else frozenset(rebase_nodes)

    def transform(node: Node, *, force_rebase: bool = False) -> Node:
        if relative_nodes is not None and node not in relative_nodes:
            return node
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
