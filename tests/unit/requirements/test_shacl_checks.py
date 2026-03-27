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

import logging

from rdflib import BNode, Graph, Namespace, URIRef

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.requirements.shacl.models import Shape, ShapesRegistry
from rocrate_validator.requirements.shacl.utils import resolve_parent_shape

logger = logging.getLogger(__name__)


class MockRequirement:
    def __init__(self):
        self.profile = None
        self.requirement_level_from_path = None


class MockParentShape:
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description


def test_description_fallback_shape_with_description():
    """Test that description returns shape's description when available."""
    g = Graph()
    shape = Shape(URIRef("http://example.org/shape"), g)
    shape._name = "TestShape"
    shape._description = "Test Description"

    req = MockRequirement()
    check = SHACLCheck(req, shape)

    assert check.description == "Test Description"


def test_description_fallback_shape_without_description():
    """Test fallback description when shape has no description but has name."""
    g = Graph()
    shape = Shape(URIRef("http://example.org/shape"), g)
    shape._name = "TestShape"
    shape._description = None

    req = MockRequirement()
    check = SHACLCheck(req, shape)

    assert check.description == "Check for TestShape"


def test_description_fallback_parent_description():
    """Test fallback to parent description when shape has no description."""
    g = Graph()
    shape = Shape(URIRef("http://example.org/shape"), g)
    shape._name = "ChildShape"
    shape._description = None
    shape._parent = MockParentShape(
        name="ParentShape", description="Parent Description"
    )

    req = MockRequirement()
    check = SHACLCheck(req, shape)

    assert check.description == "Parent Description"


def test_description_fallback_no_name_no_description():
    """Test fallback when shape has no name and no description."""
    g = Graph()
    shape = Shape(BNode(), g)
    shape._name = None
    shape._description = None

    req = MockRequirement()
    check = SHACLCheck(req, shape)

    # BNode generates a name from node_name, so we check it starts with the fallback prefix
    assert check.description.startswith("Check for ")


def test_description_fallback_no_description_no_parent_description():
    """Test fallback when shape has no description but parent has no description either."""
    g = Graph()
    shape = Shape(BNode(), g)
    shape._name = "ChildShape"
    shape._description = None
    shape._parent = MockParentShape(name="ParentShape", description=None)

    req = MockRequirement()
    check = SHACLCheck(req, shape)

    assert check.description == "Check for ChildShape"


def test_property_shape_description_fallback():
    """Test description fallback for PropertyShape without explicit description."""
    from rocrate_validator.requirements.shacl.models import PropertyShape

    g = Graph()
    prop = PropertyShape(URIRef("http://example.org/property"), g)
    prop._name = "testProperty"
    prop._description = None
    prop._parent = MockParentShape(name="ParentShape", description="Parent Description")

    req = MockRequirement()
    check = SHACLCheck(req, prop)

    assert "testProperty" in check.description
    assert "ParentShape" in check.description


def test_resolve_parent_shape_function_callable():
    """Verify that resolve_parent_shape is callable without circular import."""
    result = resolve_parent_shape(Graph(), BNode(), ShapesRegistry())
    assert result is None


def test_resolve_parent_shape_via_sparql_predicate():
    """When sourceShape is a BNode SPARQL constraint, resolves the owning NodeShape."""
    SHACL = Namespace(SHACL_NS)
    g = Graph()
    node_shape_uri = URIRef("http://example.org/NodeShape")
    sparql_bnode = BNode()
    g.add((node_shape_uri, SHACL.sparql, sparql_bnode))
    g.add((node_shape_uri, SHACL.name, URIRef("http://example.org/name")))

    shape = Shape(node_shape_uri, g)
    registry = ShapesRegistry()
    registry.add_shape(shape)

    result = resolve_parent_shape(g, sparql_bnode, registry)
    assert result is not None
    assert result.key == shape.key


def test_resolve_parent_shape_via_property_predicate():
    """When sourceShape is a BNode property constraint, resolves the owning NodeShape."""
    SHACL = Namespace(SHACL_NS)
    g = Graph()
    node_shape_uri = URIRef("http://example.org/NodeShape2")
    prop_bnode = BNode()
    g.add((node_shape_uri, SHACL.property, prop_bnode))

    shape = Shape(node_shape_uri, g)
    registry = ShapesRegistry()
    registry.add_shape(shape)

    result = resolve_parent_shape(g, prop_bnode, registry)
    assert result is not None
    assert result.key == shape.key


def test_resolve_parent_shape_returns_none_for_uri_ref():
    """Returns None immediately when sourceShape is a URIRef (not a BNode)."""
    g = Graph()
    node_shape_uri = URIRef("http://example.org/NodeShape3")

    shape = Shape(node_shape_uri, g)
    registry = ShapesRegistry()
    registry.add_shape(shape)

    # URIRef — should not attempt parent lookup
    result = resolve_parent_shape(g, node_shape_uri, registry)
    assert result is None


def test_resolve_parent_shape_returns_none_when_no_parent_in_graph():
    """Returns None when the BNode has no parent in the shapes graph."""
    g = Graph()
    orphan_bnode = BNode()
    # nothing connects orphan_bnode to any shape in g

    registry = ShapesRegistry()

    result = resolve_parent_shape(g, orphan_bnode, registry)
    assert result is None


def test_resolve_parent_shape_with_property_bnode():
    """
    Test resolve_parent_shape with a BNode representing a sh:property constraint.

    This simulates the scenario where pyshacl reports a violation with
    sourceShape being a BNode (a sh:PropertyShape defined inline).
    """
    SHACL = Namespace("http://www.w3.org/ns/shacl#")

    registry = ShapesRegistry()

    g = Graph()

    # Simulate a NodeShape with a property constraint (BNode)
    node_shape_uri = URIRef("http://example.org/ParentShape")
    property_bnode = BNode()

    g.add((node_shape_uri, SHACL.property, property_bnode))
    g.add((node_shape_uri, SHACL.targetClass, URIRef("http://example.org/TestClass")))

    # Create and register the shape
    shape = Shape(node_shape_uri, g)
    shape._name = "ParentShape"
    registry.add_shape(shape)

    # Resolve the parent shape from the BNode
    result = resolve_parent_shape(g, property_bnode, registry)

    assert result is not None, "Should resolve parent shape for property BNode"
    assert result.key == shape.key
