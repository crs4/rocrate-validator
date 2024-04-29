from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from rdflib import Graph, Namespace
from rdflib.term import Node

from ...constants import SHACL_NS
from .utils import ShapesList, compute_hash, inject_attributes

# set up logging
logger = logging.getLogger(__name__)


class Shape:

    # define default values
    name: str = None
    description: str = None

    def __init__(self, node: Node, graph: Graph):

        # store the shape node
        self._node = node
        # store the shapes graph
        self._graph = graph
        # cache the hash
        self._hash = None

        # inject attributes of the shape to the object
        inject_attributes(self, graph, node)

    @property
    def node(self):
        """Return the node of the shape"""
        return self._node

    @property
    def graph(self):
        """Return the subgraph of the shape"""
        return self._graph

    def __str__(self):
        class_name = self.__class__.__name__
        if self.name and self.description:
            return f"{class_name} - {self.name}: {self.description} ({hash(self)})"
        elif self.name:
            return f"{class_name} - {self.name} ({hash(self)})"
        elif self.description:
            return f"{class_name} - {self.description} ({hash(self)})"
        else:
            return f"{class_name} ({hash(self)})"

    def __repr__(self):
        return f"{ self.__class__.__name__}({hash(self)})"

    def __eq__(self, other):
        if not isinstance(other, Shape):
            return False
        return self._node == other._node

    def __hash__(self):
        if self._hash is None:
            shape_hash = compute_hash(self.graph, self.node)
            self._hash = hash(shape_hash)
        return self._hash


class PropertyShape(Shape):

    # define default values
    name: str = None
    description: str = None
    group: str = None
    defaultValue: str = None
    order: int = 0

    def __init__(self,
                 node: Node,
                 graph: Graph,
                 parent: Optional[Shape] = None):
        # call the parent constructor
        super().__init__(node, graph)
        # store the parent shape
        self._parent = parent

    @property
    def node(self) -> Node:
        """Return the node of the shape property"""
        return self._node

    @property
    def graph(self) -> Graph:
        """Return the graph of the shape property"""
        return self._graph

    @property
    def parent(self) -> Optional[Shape]:
        """Return the parent shape of the shape property"""
        return self._parent


class NodeShape(Shape):

    def __init__(self, node: Node, graph: Graph, properties: list[PropertyShape] = None):
        super().__init__(node, graph)
        # store the properties
        self._properties = properties if properties else []

    @property
    def properties(self) -> list[PropertyShape]:
        """Return the properties of the shape"""
        return self._properties.copy()

    def get_property(self, name) -> PropertyShape:
        """Return the property of the shape with the given name"""
        for prop in self._properties:
            if prop.name == name:
                return prop
        return None

    def add_property(self, property: PropertyShape):
        """Add a property to the shape"""
        self._properties.append(property)

    def remove_property(self, property: PropertyShape):
        """Remove a property from the shape"""
        self._properties.remove(property)


    def __repr__(self):
        return f"NodeShape({self.name})"


class ViolationShape:

    def __init__(self, shape_node: Node, graph: Graph) -> None:
        # check the input
        assert isinstance(shape_node, Node), "Invalid shape node"
        assert isinstance(graph, Graph), "Invalid graph"

        # store the input
        self._shape_node = shape_node
        self._graph = graph

        # create a graph for the shape
        shape_graph = Graph()
        shape_graph += graph.triples((shape_node, None, None))
        self.shape_graph = shape_graph

        # serialize the graph in json-ld
        shape_json = shape_graph.serialize(format="json-ld")
        shape_obj = json.loads(shape_json)
        logger.debug("Shape JSON: %s" % shape_obj)
        try:
            self.shape_json = shape_obj[0]
        except Exception as e:
            logger.error("Error parsing shape JSON: %s" % e)
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.exception(e)
            # raise e

    @property
    def node(self) -> Node:
        return self._shape_node

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def name(self):
        return self.shape_json[f'{SHACL_NS}name'][0]['@value']

    @property
    def description(self):
        return self.shape_json[f'{SHACL_NS}description'][0]['@value']

    @property
    def path(self):
        return self.shape_json[f'{SHACL_NS}path'][0]['@id']

    @property
    def nodeKind(self):
        nodeKind = self.shape_json.get(f'{SHACL_NS}nodeKind', None)
        if nodeKind:
            return nodeKind[0]['@id']
        return None


class ShapesRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._shapes = {}

    def add_shape(self, shape: Shape):
        self._shapes[str(shape)] = shape

    def get_shape(self, name: str) -> Optional[Shape]:
        return self._shapes.get(name, None)

    def get_shapes(self) -> dict[str, Shape]:
        return self._shapes.copy()

    def load_shapes(self, shapes_path: Union[str, Path], publicID: Optional[str] = None) -> list[Shape]:
        """
        Load the shapes from the graph
        """
        logger.debug(f"Loading shapes from: {shapes_path}")
        # load shapes (nodes and properties) from the shapes graph
        shapes_list: ShapesList = ShapesList.load_from_file(shapes_path, publicID)
        logger.debug(f"Shapes List: {shapes_list}")

        # list of instantiated shapes
        shapes = []

        # register Node Shapes
        for node_shape in shapes_list.node_shapes:
            # get the shape graph
            node_graph = shapes_list.get_shape_graph(node_shape)
            # create a node shape object
            shape = NodeShape(node_shape, node_graph)
            # load the nested properties
            shacl_ns = Namespace(SHACL_NS)
            nested_properties = node_graph.objects(subject=node_shape, predicate=shacl_ns.property)
            for property_shape in nested_properties:
                property_graph = shapes_list.get_shape_property_graph(node_shape, property_shape)
                p_shape = PropertyShape(
                    property_shape, property_graph, shape)
                shape.add_property(p_shape)
                self.add_shape(p_shape)
            # store the node shape
            self.add_shape(shape)
            shapes.append(shape)

        # register Property Shapes
        for property_shape in shapes_list.property_shapes:
            shape = PropertyShape(property_shape, shapes_list.get_shape_graph(property_shape))
            self.add_shape(shape)
            shapes.append(shape)

        return shapes

    def __str__(self):
        return f"ShapesRegistry: {self._shapes}"

    def __repr__(self):
        return f"ShapesRegistry({self._shapes})"

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
