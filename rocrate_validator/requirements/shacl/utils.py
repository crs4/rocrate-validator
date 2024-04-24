from __future__ import annotations

import logging

from rdflib import RDF, BNode, Graph, Namespace
from rdflib.term import Node

from rocrate_validator.constants import RDF_SYNTAX_NS, SHACL_NS

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


def inject_attributes(obj: object, node_graph: Graph, node: Node) -> object:
    # inject attributes of the shape property
    for node, p, o in node_graph.triples((node, None, None)):
        predicate_as_string = p.toPython()
        logger.debug(f"Processing {predicate_as_string} of property graph {node}")
        if predicate_as_string.startswith(SHACL_NS):
            property_name = predicate_as_string.split("#")[-1]
            setattr(obj, property_name, o.toPython())
            logger.debug("Injecting attribute %s: %s", property_name, o.toPython())

    # return the object
    return obj


class ShapesList:
    def __init__(self,
                 node_shapes: list[Node],
                 property_shapes: list[Node],
                 shapes_graphs: dict[Node, Graph]):
        self._shapes_graphs = shapes_graphs
        self._node_shapes = node_shapes
        self._property_shapes = property_shapes

    @property
    def node_shapes(self) -> list[Node]:
        return self._node_shapes.copy()

    @property
    def property_shapes(self) -> list[Node]:
        return self._property_shapes.copy()

    @property
    def shapes(self) -> list[Node]:
        return self._node_shapes + self._property_shapes

    def get_shape_graph(self, shape_node: Node) -> Graph:
        return self._shapes_graphs[shape_node]

    def get_shape_property_graph(self, shape_node: Node, shape_property: Node) -> Graph:
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


def __extract_related_triples__(graph, subject_node):
    """
    Recursively extract all triples related to a given shape.
    """
    related_triples = []
    # Directly related triples
    related_triples.extend((_, p, o) for (_, p, o) in graph.triples((subject_node, None, None)))

    # Recursively find triples related to nested shapes
    for _, _, object_node in related_triples:
        if isinstance(object_node, Node):
            related_triples.extend(__extract_related_triples__(graph, object_node))

    return related_triples


def load_shapes_from_file(file_path: str, publicID: str = None) -> ShapesList:
    # Check the file path is not None
    assert file_path is not None, "The file path cannot be None"
    # Load the graph from the file
    g = Graph()
    g.parse(file_path, format="turtle", publicID=publicID)
    # Extract the shapes from the graph
    return load_shapes_from_graph(g)


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

    return ShapesList(node_shapes, property_shapes, subgraphs)
