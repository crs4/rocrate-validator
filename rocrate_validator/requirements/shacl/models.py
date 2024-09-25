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

from pathlib import Path
from typing import Optional, Union

from rdflib import Graph, Namespace, URIRef
from rdflib.term import Node

from rocrate_validator.constants import SHACL_NS
import rocrate_validator.log as logging
from rocrate_validator.models import LevelCollection, RequirementLevel, Severity
from rocrate_validator.requirements.shacl.utils import (ShapesList,
                                                        compute_key,
                                                        inject_attributes)

# set up logging
logger = logging.getLogger(__name__)


class SHACLNode:

    # define default values
    _name: str = None
    _description: str = None
    severity: str = None

    def __init__(self, node: Node, graph: Graph, parent: Optional[SHACLNode] = None):

        # store the shape key
        self._key = None
        # store the shape node
        self._node = node
        # store the shapes graph
        self._graph = graph
        # cache the hash
        self._hash = None
        # store the parent shape
        self._parent = parent

        # inject attributes of the shape to the object
        inject_attributes(self, graph, node)

    @property
    def name(self) -> str:
        """Return the name of the shape"""
        if not self._name:
            self._name = self._node.split("#")[-1] if "#" in self.node else self._node.split("/")[-1]
        return self._name or self._node.split("/")[-1]

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def description(self) -> str:
        """Return the description of the shape"""
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value

    @property
    def key(self) -> str:
        """Return the key of the shape"""
        if self._key is None:
            return compute_key(self.graph, self.node)
        return self._key

    @property
    def node(self):
        """Return the node of the shape"""
        return self._node

    @property
    def graph(self):
        """Return the subgraph of the shape"""
        return self._graph

    @property
    def parent(self) -> Optional[SHACLNode]:
        """Return the parent shape of the shape"""
        return self._parent

    @property
    def level(self) -> RequirementLevel:
        """Return the requirement level of the shape"""
        return self.get_declared_level() or LevelCollection.REQUIRED

    def get_declared_level(self) -> Optional[RequirementLevel]:
        """Return the declared level of the shape"""
        severity = self.get_declared_severity()
        if severity:
            try:
                return LevelCollection.get(severity.name)
            except ValueError:
                pass
        return None

    def get_declared_severity(self) -> Optional[Severity]:
        """Return the declared severity of the shape"""
        severity = getattr(self, "severity", None)
        if severity == f"{SHACL_NS}Violation":
            return Severity.REQUIRED
        elif severity == f"{SHACL_NS}Warning":
            return Severity.RECOMMENDED
        elif severity == f"{SHACL_NS}Info":
            return Severity.OPTIONAL
        return None

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
            self._hash = hash(self.key)
        return self._hash

    @staticmethod
    def compute_key(graph: Graph, node: Node) -> str:
        return compute_key(graph, node)

    @staticmethod
    def compute_hash(graph: Graph, node: Node) -> int:
        return hash(compute_key(graph, node))


class SHACLNodeCollection(SHACLNode):

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

    def get_property_index(self, name) -> int:
        """Return the index of the property with the given name"""
        for i, prop in enumerate(self._properties):
            if prop.name == name:
                return i
        return -1

    def add_property(self, property: PropertyShape):
        """Add a property to the shape"""
        self._properties.append(property)

    def remove_property(self, property: PropertyShape):
        """Remove a property from the shape"""
        self._properties.remove(property)


class Shape(SHACLNode):
    pass


class PropertyGroup(SHACLNodeCollection):
    pass


class PropertyShape(Shape):

    # define default values
    _name: str = None
    _short_name: str = None
    _description: str = None
    group: str = None
    defaultValue: str = None
    order: int = 0
    # store the reference to the property group
    _property_group: PropertyGroup = None

    def __init__(self,
                 node: Node,
                 graph: Graph,
                 parent: Optional[Shape] = None):
        # call the parent constructor
        super().__init__(node, graph)
        # store the parent shape
        self._parent = parent

    @property
    def name(self) -> str:
        """Return the name of the shape property"""
        if not self._name:
            # get the object of the predicate sh:path
            shacl_ns = Namespace(SHACL_NS)
            path = self.graph.value(subject=self.node, predicate=shacl_ns.path)
            if path:
                self._short_name = path.split("#")[-1] if "#" in path else path.split("/")[-1]
                if self.parent:
                    self._name = f"{self._short_name} of {self.parent.name}"
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def description(self) -> str:
        """Return the description of the shape property"""
        if not self._description:
            # get the object of the predicate sh:description
            if not self._description:
                property_name = self.name
                if self._short_name:
                    property_name = self._short_name
                self._description = f"Check the property \"**{property_name}**\""
                if self.parent and self.parent.name not in property_name:
                    self._description += f" of the entity \"**{self.parent.name}**\""
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value

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

    @property
    def propertyGroup(self) -> PropertyGroup:
        """Return the group of the shape property"""
        return self._property_group


class NodeShape(Shape, SHACLNodeCollection):

    @property
    def property_groups(self) -> list[PropertyGroup]:
        """Return the property groups of the shape"""
        groups = set()
        for prop in self.properties:
            if prop.propertyGroup:
                groups.add(prop.propertyGroup)
        return list(groups)

    @property
    def grouped_properties(self) -> list[PropertyShape]:
        """Return the properties that are in a group"""
        return [prop for prop in self.properties if prop.propertyGroup]

    @property
    def ungrouped_properties(self) -> list[PropertyShape]:
        """Return the properties that are not in a group"""
        return [prop for prop in self.properties if not prop.propertyGroup]


class ShapesRegistry:

    def __init__(self):
        self._shapes = {}
        self._shapes_graph: Graph = Graph()

    def add_shape(self, shape: Shape):
        assert isinstance(shape, Shape), "Invalid shape"
        self._shapes[shape.key] = shape

    def remove_shape(self, shape: Shape):
        assert isinstance(shape, Shape), "Invalid shape"
        self._shapes.pop(shape.key, None)
        self._shapes_graph -= shape.graph

    def get_shape(self, shape_key: str) -> Optional[Shape]:
        logger.debug("Searching for shape %s in the registry: %s", shape_key, self._shapes)
        result = self._shapes.get(shape_key, None)
        if not result:
            logger.debug(f"Shape {shape_key} not found in the registry")
            raise ValueError(f"Shape not found in the registry: {shape_key}")
        return result

    def extend(self, shapes: dict[str, Shape], graph: Graph) -> None:
        self._shapes.update(shapes)
        self._shapes_graph += graph

    def get_shape_by_name(self, name: str) -> Optional[Shape]:
        for shape in self._shapes.values():
            if shape.name == name:
                return shape
        return None

    def get_shapes(self) -> dict[str, Shape]:
        return self._shapes.copy()

    @property
    def shapes_graph(self) -> Graph:
        g = Graph()
        g += self._shapes_graph
        return g

    def load_shapes(self, shapes_path: Union[str, Path], publicID: Optional[str] = None) -> list[Shape]:
        """
        Load the shapes from the graph
        """
        logger.debug(f"Loading shapes from: {shapes_path}")
        # load shapes (nodes and properties) from the shapes graph
        shapes_list: ShapesList = ShapesList.load_from_file(shapes_path, publicID)
        logger.debug(f"Shapes List: {shapes_list}")

        # append the partial shapes graph to the global shapes graph
        self._shapes_graph += shapes_list.shapes_graph

        # list of instantiated shapes
        shapes = []

        # list of property groups
        property_groups = {}

        # register Node Shapes
        for node_shape in shapes_list.node_shapes:
            # flag to check if the nested properties are in a group
            grouped = False
            # list of properties ungrouped
            ungrouped_properties = []
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
                group = __process_property_group__(property_groups, p_shape)
                if group and group not in shapes:
                    grouped = True
                    shapes.append(group)
                if not group:
                    ungrouped_properties.append(p_shape)

                # store the property shape in the registry
                self.add_shape(p_shape)
            # store the node shape in the registry
            self.add_shape(shape)

            #  store the node in the list of shapes
            if not grouped:
                shapes.append(shape)
            else:
                for prop in ungrouped_properties:
                    shapes.append(prop)

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

    def clear(self):
        self._shapes.clear()
        self._shapes_graph = Graph()

    @classmethod
    def get_instance(cls, ctx: object):
        instance = getattr(ctx, "_shapes_registry_instance", None)
        if not instance:
            instance = cls()
            setattr(ctx, "_shapes_registry_instance", instance)
        return instance


def __process_property_group__(groups: dict[str, PropertyGroup], property_shape: PropertyShape) -> PropertyGroup:
    group_name = property_shape.group
    if group_name:
        if group_name not in groups:
            groups[group_name] = PropertyGroup(URIRef(property_shape.group), property_shape.graph)
        property_shape.graph.serialize("logs/property_shape.ttl", format="turtle")
        groups[group_name].add_property(property_shape)
        property_shape._property_group = groups[group_name]
        return groups[group_name]
    return None
