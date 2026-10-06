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

from urllib.parse import urljoin

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from rocrate_validator.utils.rdf import PREPARED_PROFILE_BASE, rebase_graph, rebase_node


def test_rebase_graph_maps_parent_relative_references_after_rdf_parsing():
    source_base = "https://example.org/a/b/crate/"
    prepared_base = "https://example.invalid/rocrate-validator/prepared/crate/"
    graph = Graph().parse(
        data="""
            @prefix ex: <../> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

            ex:target rdf:type ex:Entity .
            <https://outside.example/entity> rdf:type ex:Entity .
        """,
        format="turtle",
        publicID=source_base,
    )

    rebased = rebase_graph(graph, ((source_base, prepared_base),))

    assert (
        URIRef("https://example.invalid/rocrate-validator/prepared/target"),
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef("https://example.invalid/rocrate-validator/prepared/Entity"),
    ) in rebased
    assert (
        URIRef("https://outside.example/entity"),
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef("https://example.invalid/rocrate-validator/prepared/Entity"),
    ) in rebased


def test_rebase_graph_rebases_structural_node_when_used_as_target_class():
    prepared_base = "https://example.invalid/rocrate-validator/prepared/crate/"
    crate_base = "file:///tmp/crate/"
    sh = Namespace("http://www.w3.org/ns/shacl#")
    class_shape = URIRef(f"{prepared_base}Dataset")
    graph = Graph()
    graph.add((class_shape, RDF.type, sh.NodeShape))
    graph.add((class_shape, sh.targetClass, class_shape))

    rebased = rebase_graph(
        graph,
        ((prepared_base, crate_base),),
        preserve_nodes=(class_shape,),
        rebase_objects_for=(sh.targetClass,),
    )

    assert (class_shape, RDF.type, sh.NodeShape) in rebased
    assert (class_shape, sh.targetClass, URIRef("file:///tmp/crate/Dataset")) in rebased


def test_rebase_node_preserves_parent_relative_trailing_slash():
    target_base = "file:///data/team/project/crate/"
    source_uri = URIRef(urljoin(PREPARED_PROFILE_BASE, "../Dataset/"))

    rebased = rebase_node(source_uri, ((PREPARED_PROFILE_BASE, target_base),))

    assert rebased == URIRef("file:///data/team/project/Dataset/")


def test_rebase_node_preserves_root_relative_path():
    target_base = "file:///data/team/project/crate/"
    source_uri = URIRef("https://example.invalid/Dataset")

    rebased = rebase_node(source_uri, ((PREPARED_PROFILE_BASE, target_base),))

    assert rebased == URIRef("file:///Dataset")


def test_rebase_node_leaves_absolute_iri_on_another_authority_unchanged():
    absolute_iri = URIRef("https://schema.org/Dataset")

    rebased = rebase_node(absolute_iri, ((PREPARED_PROFILE_BASE, "file:///data/crate/"),))

    assert rebased == absolute_iri
