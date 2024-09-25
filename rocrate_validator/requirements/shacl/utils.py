# Copyright (c) 2024 CRS4
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
from typing import Optional, Union

from rdflib import RDF, BNode, Graph, Namespace
from rdflib.term import Node

import rocrate_validator.log as logging
from rocrate_validator.constants import RDF_SYNTAX_NS, SHACL_NS
from rocrate_validator.errors import BadSyntaxError
from rocrate_validator.models import Severity

# set up logging
logger = logging.getLogger(__name__)


def build_node_subgraph(graph: Graph, node: Node) -> Graph:
    shape_graph = Graph()
    shape_graph += graph.triples((node, None, None))

    # add BNodes
    for _, _, o in shape_graph:
        shape_graph += graph.triples((o, None, None))

    # Use the triples method to get all triples that are part of a list
    RDF = Namespace(RDF_SYNTAX_NS)
    first_predicate = RDF.first
    rest_predicate = RDF.rest
    shape_graph += graph.triples((None, first_predicate, None))
    shape_graph += graph.triples((None, rest_predicate, None))
    for _, _, object in shape_graph:
        shape_graph += graph.triples((object, None, None))

    # return the subgraph
    return shape_graph


def map_severity(shacl_severity: str) -> Severity:
    """
    Map the SHACL severity term to our Severity enum values
    """
    if f"{SHACL_NS}Violation" == shacl_severity:
        return Severity.REQUIRED
    elif f"{SHACL_NS}Warning" == shacl_severity:
        return Severity.RECOMMENDED
    elif f"{SHACL_NS}Info" == shacl_severity:
        return Severity.OPTIONAL
    else:
        raise RuntimeError(f"Unrecognized SHACL severity term {shacl_severity}")


def make_uris_relative(text: str, ro_crate_path: Union[Path, str]) -> str:
    # globally replace the string "file://" with "./
    return text.replace(str(ro_crate_path), './')


def inject_attributes(obj: object, node_graph: Graph, node: Node, exclude: Optional[list] = None) -> object:
    # inject attributes of the shape property
    # logger.debug("Injecting attributes of node %s", node)
    skip_properties = ["node"] if exclude is None else exclude + ["node"]
    triples = node_graph.triples((node, None, None))
    for node, p, o in triples:
        predicate_as_string = p.toPython()
        # logger.debug(f"Processing {predicate_as_string} of property graph {node}")
        if predicate_as_string.startswith(SHACL_NS):
            property_name = predicate_as_string.split("#")[-1]
            if property_name in skip_properties:
                continue
            try:
                setattr(obj, property_name, o.toPython())
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
    # Calculate the hash of the triples string
    hash_value = hashlib.sha256(triples_string.encode()).hexdigest()
    # Return the hash value
    return hash_value


def compute_key(g: Graph, s: Node) -> str:
    """
    Compute the key of the node `s` in the graph `g`.
    If the node is a URI, return the URI as a string.
    If the node is a BNode, return the hash of the triples in the graph starting from the BNode.
    """

    if isinstance(s, BNode):
        return compute_hash(g, s)
    else:
        return s.toPython()


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
        Get the subgraph of the given shape node excluding the given property
        """
        node_graph = self.get_shape_graph(shape_node)
        assert node_graph is not None, "The shape graph cannot be None"

        property_graph = Graph()
        shacl_ns = Namespace(SHACL_NS)
        nested_properties_to_exclude = [o for (_, _, o) in node_graph.triples(
            (shape_node, shacl_ns.property, None)) if o != shape_property]
        triples_to_exclude = [(s, _, o) for (s, _, o) in node_graph.triples((None, None, None))
                              if s in nested_properties_to_exclude
                              or o in nested_properties_to_exclude]

        property_graph += node_graph - triples_to_exclude

        return property_graph

    @classmethod
    def load_from_file(cls, file_path: str, publicID: str = None) -> ShapesList:
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


def load_shapes_from_file(file_path: str, publicID: str = None) -> ShapesList:
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
