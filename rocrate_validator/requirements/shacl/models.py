from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from rdflib import Graph
from rdflib.term import Node

from ...constants import SHACL_NS

# set up logging
logger = logging.getLogger(__name__)


class ShapeProperty:
    def __init__(self,
                 shape: Shape,
                 name: str,
                 description: Optional[str] = None,
                 group: Optional[str] = None,
                 node: Optional[str] = None,
                 default: Optional[str] = None,
                 order: int = 0):
        self._name = name
        self._description = description
        self._shape = shape
        self._group = group
        self._node = node
        self._default = default
        self._order = order

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def shape(self):
        return self._shape

    @property
    def group(self):
        return self._group

    @property
    def node(self):
        return self._node

    @property
    def default(self):
        return self._default

    @property
    def order(self):
        return self._order

    def compare_shape(self, other_model):
        return self.shape == other_model.shape

    def compare_name(self, other_model):
        return self.name == other_model.name


class Shape:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.properties = []

    def add_property(self, name: str, description: str = None,
                     group: str = None, node: str = None, default: str = None, order: int = 0):
        self.properties.append(
            ShapeProperty(self,
                          name, description,
                          group, node, default, order))

    def get_properties(self) -> List[ShapeProperty]:
        return self.properties

    def get_property(self, name) -> ShapeProperty:
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def __str__(self):
        return f"{self.name}: {self.description}"

    def __repr__(self):
        return f"Shape({self.name})"

    def __eq__(self, other):
        if not isinstance(other, Shape):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def load(cls, shapes_path: Union[str, Path]) -> Dict[str, Shape]:
        """
        Load the shapes from the graph
        """
        shapes_graph = Graph()
        shapes_graph.parse(shapes_path, format="turtle")
        logger.debug("Shapes graph: %s" % shapes_graph)

        # query the graph for the shapes and shape properties
        query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT  ?shape ?shapeName ?shapeDescription 
                ?propertyName ?propertyDescription
                ?propertyPath ?propertyGroup ?propertyOrder
        WHERE {
            ?shape a sh:NodeShape ;
                    sh:name ?shapeName ;
                    sh:description ?shapeDescription ;
                    sh:property ?property .
            OPTIONAL {
                ?property sh:name ?propertyName ;
                        sh:description ?propertyDescription ;
                        sh:group ?propertyGroup ;
                        sh:order ?propertyOrder ;
                        sh:path ?propertyPath .
            }
        }
        """

        logger.debug("Performing query: %s" % query)
        results = shapes_graph.query(query)
        logger.debug("Query results: %s" % results)

        shapes: Dict[str, Shape] = {}
        for row in results:
            shape = shapes.get(row.shapeName, None)
            if shape is None:
                shape = Shape(row.shapeName, row.shapeDescription)
                shapes[row.shapeName] = shape

            # print("propertyName vs shapeName", row.propertyName, row.shapeName)
            shape.add_property(
                row.propertyName or row.shapeName,
                row.propertyDescription or row.shapeDescription,
                group=row.propertyGroup or None,
                # node=row.propertyNode or None,
                default=None,
                order=row.propertyOrder or 0
            )
        return shapes


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
            pass

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
