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

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union, cast

from rdflib import RDF, BNode, Graph, Namespace
from rdflib.term import Node

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.errors import BadSyntaxError
from rocrate_validator.models import Severity
from rocrate_validator.utils import log as logging

if TYPE_CHECKING:
    from rocrate_validator.requirements.shacl.models import Shape

# set up logging
logger = logging.getLogger(__name__)


def build_node_subgraph(graph: Graph, node: Node) -> Graph:
    """
    Build a subgraph with every triple reachable from ``node`` by following BNode objects.
    """
    subgraph = Graph()
    visited: set = set()
    stack: list = [node]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        for triple in graph.triples((current, None, None)):
            subgraph.add(triple)
            _, _, obj = triple
            if isinstance(obj, BNode) and obj not in visited:
                stack.append(obj)
    return subgraph


def map_severity(shacl_severity: str) -> Severity:
    """
    Map the SHACL severity term to our Severity enum values
    """
    if f"{SHACL_NS}Violation" == shacl_severity:
        return Severity.REQUIRED
    if f"{SHACL_NS}Warning" == shacl_severity:
        return Severity.RECOMMENDED
    if f"{SHACL_NS}Info" == shacl_severity:
        return Severity.OPTIONAL
    raise RuntimeError(f"Unrecognized SHACL severity term {shacl_severity}")


def make_uris_relative(text: str, ro_crate_path: Union[Path, str]) -> str:
    # globally replace the string "file://" with "./
    return text.replace(str(ro_crate_path), './')


def inject_attributes(obj: object, node_graph: Graph, node: Node, exclude: Optional[list] = None) -> object:
    # inject attributes of the shape property
    # logger.debug("Injecting attributes of node %s", node)
    skip_properties = ["node"] if exclude is None else exclude + ["node"]
    triples = node_graph.triples((node, None, None))
    for _node, p, o in triples:
        predicate_as_string = cast(Any, p).toPython()
        # logger.debug(f"Processing {predicate_as_string} of property graph {node}")
        if predicate_as_string.startswith(SHACL_NS):
            property_name = predicate_as_string.split("#")[-1]
            if property_name in skip_properties:
                continue
            try:
                setattr(obj, property_name, cast(Any, o).toPython())
            except AttributeError as e:
                logger.error(f"Error injecting attribute {property_name}: {e}")
            # logger.debug("Injected attribute %s: %s", property_name, o.toPython())
    # logger.debug("Injected attributes ig node %s: %s", node, len(list(triples)))
    # return the object
    return obj


def __compute_values__(g: Graph, s: Node) -> list[tuple]:
    """
    Compute the values of the triples in the graph (excluding BNodes)
    starting from the given subject node `s`.
    """

    # Collect the values of the triples in the graph (excluding BNodes)
    values = []
    # Assuming the list of triples values is stored in a variable called 'triples_values'
    triples_values = list([(_, x, _) for (_, x, _) in g.triples((s, None, None)) if x != RDF.type])

    for (s, p, o) in triples_values:
        if isinstance(o, BNode):
            values.extend(__compute_values__(g, o))
        else:
            values.append((s, p, o) if not isinstance(s, BNode) else (p, o))
    return values


def compute_hash(g: Graph, s: Node):
    """
    Compute the hash of the triples in the graph (including BNodes)
    starting from the given subject node `s`.
    """

    # Collect the values of the triples in the graph (excluding BNodes)
    triples_values = sorted(__compute_values__(g, s))
    # Convert the list of triples values to a string representation
    triples_string = str(triples_values)
    # Calculate and return the hash of the triples string
    return hashlib.sha256(triples_string.encode()).hexdigest()


def compute_key(g: Graph, s: Node) -> str:
    """
    Compute the key of the node `s` in the graph `g`.
    If the node is a URI, return the URI as a string.
    If the node is a BNode, return the hash of the triples in the graph starting from the BNode.
    """

    if isinstance(s, BNode):
        return compute_hash(g, s)
    return cast(Any, s).toPython()


class ShapesList:
    def __init__(self,
                 node_shapes: list[Node],
                 property_shapes: list[Node],
                 shapes_graphs: dict[Node, Graph],
                 shapes_graph: Graph):
        self._node_shapes = node_shapes
        self._property_shapes = property_shapes
        self._shapes_graph = shapes_graph
        self._shapes_graphs = shapes_graphs

    @property
    def node_shapes(self) -> list[Node]:
        """
        Get all the node shapes
        """
        return self._node_shapes.copy()

    @property
    def property_shapes(self) -> list[Node]:
        """
        Get all the property shapes
        """
        return self._property_shapes.copy()

    @property
    def shapes(self) -> list[Node]:
        """
        Get all the shapes
        """
        return self._node_shapes + self._property_shapes

    @property
    def shapes_graph(self) -> Graph:
        """
        Get the graph containing all the shapes
        """
        return self._shapes_graph

    def get_shape_graph(self, shape_node: Node) -> Graph:
        """
        Get the subgraph of the given shape node
        """
        return self._shapes_graphs[shape_node]

    def get_shape_property_graph(self, shape_node: Node, shape_property: Node) -> Graph:
        """
        Get the subgraph of a property shape nested inside a node shape.

        Includes only triples reachable from `shape_property` (its constraints
        and any RDF lists used by `sh:and`/`sh:or`/`sh:xone`), plus the link
        triple `(shape_node, sh:property, shape_property)`. Nothing reachable
        only via sibling properties is included, so subtracting this graph
        from the merged shapes graph cannot break sibling constructs.
        """
        node_graph = self.get_shape_graph(shape_node)
        assert node_graph is not None, "The shape graph cannot be None"

        property_graph = Graph()
        for s, p, o in __extract_related_triples__(node_graph, shape_property):
            property_graph.add((s, p, o))

        shacl_ns = Namespace(SHACL_NS)
        property_graph.add((shape_node, shacl_ns.property, shape_property))

        return property_graph

    @classmethod
    def load_from_file(cls, file_path: str, publicID: Optional[str] = None) -> ShapesList:
        """
        Load the shapes from the file

        :param file_path: the path to the file containing the shapes
        :param publicID: the public ID to use

        :return: the list of shapes
        """
        return load_shapes_from_file(file_path, publicID)

    @classmethod
    def load_from_graph(cls, graph: Graph) -> ShapesList:
        """
        Load the shapes from the graph

        :param graph: the graph containing the shapes
        :param target_node: the target node to extract the shapes from

        :return: the list of shapes
        """
        return load_shapes_from_graph(graph)


def __extract_related_triples__(graph, subject_node, processed_nodes=None):
    """
    Recursively extract all triples related to a given shape.
    """

    related_triples = []

    processed_nodes = processed_nodes if processed_nodes is not None else set()

    # Skip the current node if it has already been processed
    if subject_node in processed_nodes:
        return related_triples

    # Add the current node to the processed nodes
    processed_nodes.add(subject_node)

    # Directly related triples
    related_triples.extend((_, p, o) for (_, p, o) in graph.triples((subject_node, None, None)))

    # Recursively find triples related to nested shapes
    for _, _, object_node in related_triples:
        if isinstance(object_node, Node):
            related_triples.extend(__extract_related_triples__(graph, object_node, processed_nodes))

    return related_triples


def load_shapes_from_file(file_path: str, publicID: Optional[str] = None) -> ShapesList:
    try:
        # Check the file path is not None
        assert file_path is not None, "The file path cannot be None"
        # Load the graph from the file
        g = Graph()
        g.parse(file_path, format="turtle", publicID=publicID)
        # Extract the shapes from the graph
        return load_shapes_from_graph(g)
    except Exception as e:
        raise BadSyntaxError(str(e), file_path) from e


def load_shapes_from_graph(g: Graph) -> ShapesList:
    # define the SHACL namespace
    SHACL = Namespace(SHACL_NS)
    # find all NodeShapes
    node_shapes = [s for (s, _, _) in g.triples(
        (None, RDF.type, SHACL.NodeShape)) if not isinstance(s, BNode)]
    logger.debug("Loaded Node Shapes: %s", node_shapes)
    # find all PropertyShapes
    property_shapes = [s for (s, _, _) in g.triples((None, RDF.type, SHACL.PropertyShape))
                       if not isinstance(s, BNode)]
    logger.debug("Loaded Property Shapes: %s", property_shapes)
    # define the list of shapes to extract
    shapes = node_shapes + property_shapes

    # Split the graph into subgraphs for each shape
    subgraphs = {}
    count = 0
    for shape in shapes:
        count += 1
        subgraph = Graph()
        # Extract all related triples for the current shape
        related_triples = __extract_related_triples__(g, shape)
        for s, p, o in related_triples:
            subgraph.add((s, p, o))
        subgraphs[shape] = subgraph

    return ShapesList(node_shapes, property_shapes, subgraphs, g)


def resolve_parent_shape(
    shapes_graph: Graph, source_shape_node: Node, shapes_registry
) -> Optional[Shape]:
    """
    Try to resolve the parent NodeShape/PropertyShape for a BNode constraint node.

    When a SPARQL constraint (sh:sparql) or inline constraint BNode fires a violation,
    pyshacl reports the BNode as `sh:sourceShape`. That BNode is not registered
    in the ShapesRegistry directly; instead the containing NodeShape is.
    This helper walks up via sh:sparql and sh:property predicates to find it.
    """
    from rocrate_validator.requirements.shacl.models import Shape

    if not isinstance(source_shape_node, BNode):
        return None
    SHACL = Namespace(SHACL_NS)
    # Predicates via which a NodeShape/PropertyShape can own a constraint BNode
    parent_predicates = [SHACL.sparql, SHACL.property]
    for predicate in parent_predicates:
        for parent_node in shapes_graph.subjects(predicate, source_shape_node):
            try:
                parent_shape = shapes_registry.get_shape(
                    Shape.compute_key(shapes_graph, parent_node)
                )
                if parent_shape is not None:
                    logger.debug(
                        "Resolved parent shape %s for SPARQL/inline constraint BNode %s",
                        parent_shape.key,
                        source_shape_node,
                    )
                    return parent_shape
            except (ValueError, KeyError):
                continue
    return None
