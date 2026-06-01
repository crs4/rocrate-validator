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

"""
Unit tests for ``ShapesList.get_shape_property_graph``.

The method must return a subgraph that:
* contains every triple reachable from the property shape (its constraints
    and any RDF lists used by ``sh:and``/``sh:or``/``sh:xone``);
* contains the link triple ``(shape_node, sh:property, shape_property)``;
* does NOT contain triples that belong only to sibling property shapes
"""

import pytest
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.requirements.shacl.utils import load_shapes_from_graph

SH = Namespace(SHACL_NS)
EX = Namespace("http://example.org/")


def _build_two_property_shape() -> tuple[Graph, URIRef, URIRef, URIRef]:
    """
    Build a NodeShape with two sibling property shapes.

    Returns ``(graph, node_shape, prop_a, prop_b)``.

    Each property shape is a BNode owning its own ``sh:path``,
    ``sh:datatype``, ``sh:minCount`` constraints.
    """
    g = Graph()
    g.bind("sh", SH)
    g.bind("ex", EX)

    node_shape = EX.PersonShape
    g.add((node_shape, RDF.type, SH.NodeShape))
    g.add((node_shape, SH.targetClass, EX.Person))

    prop_a = BNode("propA")
    g.add((node_shape, SH.property, prop_a))
    g.add((prop_a, SH.path, EX.name))
    g.add((prop_a, SH.datatype, EX.stringType))
    g.add((prop_a, SH.minCount, Literal(1)))

    prop_b = BNode("propB")
    g.add((node_shape, SH.property, prop_b))
    g.add((prop_b, SH.path, EX.age))
    g.add((prop_b, SH.datatype, EX.intType))
    g.add((prop_b, SH.minCount, Literal(0)))

    return g, node_shape, prop_a, prop_b


def test_returns_link_triple_to_target_property():
    """The link ``(node_shape, sh:property, shape_property)`` must be present."""
    g, node_shape, prop_a, prop_b = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)

    # The link to the prop_a shape must be present
    assert (node_shape, SH.property, prop_a) in pg
    # but not the link to the prop_b shape.
    assert (node_shape, SH.property, prop_b) not in pg


def test_includes_all_constraints_of_target_property():
    """All triples whose subject is the target property shape must be included."""
    g, node_shape, prop_a, _ = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)

    assert (prop_a, SH.path, EX.name) in pg
    assert (prop_a, SH.datatype, EX.stringType) in pg
    assert (prop_a, SH.minCount, Literal(1)) in pg


def test_excludes_sibling_property_link_and_constraints():
    """
    Sibling property shapes and their link triples must not appear in the
    returned subgraph. This is the regression the new implementation fixes.
    """
    g, node_shape, prop_a, prop_b = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)

    # Sibling link triple must not be present.
    assert (node_shape, SH.property, prop_b) not in pg
    # Sibling constraints must not be present.
    assert (prop_b, SH.path, EX.age) not in pg
    assert (prop_b, SH.datatype, EX.intType) not in pg
    assert (prop_b, SH.minCount, Literal(0)) not in pg


def test_subtraction_preserves_sibling_property_link():
    """
    Subtracting the returned subgraph from the merged shapes graph must
    leave the sibling property's link to the parent NodeShape intact
    """
    g, node_shape, prop_a, prop_b = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)
    remaining = shapes_list.shapes_graph - pg

    # The sibling property is still linked to the NodeShape.
    assert (node_shape, SH.property, prop_b) in remaining
    # And so are its constraints.
    assert (prop_b, SH.path, EX.age) in remaining


def test_does_not_include_unrelated_node_shape_triples():
    """
    Triples on the parent NodeShape that are not the target link must
    not be pulled in (e.g. ``sh:targetClass``).
    """
    g, node_shape, prop_a, _ = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)

    assert (node_shape, SH.targetClass, EX.Person) not in pg
    assert (node_shape, RDF.type, SH.NodeShape) not in pg


def test_includes_rdf_list_triples_for_sh_or():
    """
    When the property shape uses ``sh:or`` (an RDF list), the list spine
    (``rdf:first``/``rdf:rest``) and every list member must be reachable
    in the returned subgraph.
    """
    g = Graph()
    node_shape = EX.SomeShape
    g.add((node_shape, RDF.type, SH.NodeShape))

    prop = BNode("prop")
    g.add((node_shape, SH.property, prop))
    g.add((prop, SH.path, EX.something))

    member_a = BNode("memberA")
    g.add((member_a, SH.datatype, EX.t1))
    member_b = BNode("memberB")
    g.add((member_b, SH.datatype, EX.t2))

    list_head = BNode("listHead")
    Collection(g, list_head, [member_a, member_b])
    g.add((prop, SH["or"], list_head))

    shapes_list = load_shapes_from_graph(g)
    pg = shapes_list.get_shape_property_graph(node_shape, prop)

    # The sh:or link is reachable from the property.
    assert (prop, SH["or"], list_head) in pg
    # Both list members and their constraints are reachable.
    assert (member_a, SH.datatype, EX.t1) in pg
    assert (member_b, SH.datatype, EX.t2) in pg
    # The RDF list spine is included so the list can be re-walked.
    list_spine_subjects = {s for s, _, _ in pg.triples((None, RDF.first, None))}
    assert list_head in list_spine_subjects


def test_only_target_link_present_when_node_has_multiple_properties():
    """
    The graph must contain exactly one ``sh:property`` triple originating
    from the parent NodeShape — the one pointing at the target property.
    """
    g, node_shape, prop_a, _ = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    pg = shapes_list.get_shape_property_graph(node_shape, prop_a)

    property_links = list(pg.triples((node_shape, SH.property, None)))
    assert len(property_links) == 1
    assert property_links[0] == (node_shape, SH.property, prop_a)


def test_unknown_shape_node_raises():
    """A shape node not in the registry should raise ``KeyError``."""
    g, _, prop_a, _ = _build_two_property_shape()
    shapes_list = load_shapes_from_graph(g)

    with pytest.raises(KeyError):
        shapes_list.get_shape_property_graph(EX.UnknownShape, prop_a)
