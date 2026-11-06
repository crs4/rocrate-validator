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

from rdflib import RDF, BNode, Graph, Literal, Namespace
from rdflib.collection import Collection
from rdflib.namespace import SH

from rocrate_validator.requirements.shacl.transformers import REQUIRES_GRAPH_TRANSFORMER_PREDICATE
from rocrate_validator.requirements.shacl.transformers.preparation import prepare_validation_graphs
from rocrate_validator.transformers.validation_candidate_marker import (
    VALIDATION_CANDIDATE_PREDICATE,
    VALIDATION_CANDIDATE_TRANSFORMER,
)

EXAMPLE = Namespace("https://example.org/")
SCHEMA = Namespace("http://schema.org/")


def test_unrequested_transformers_do_not_copy_graph_objects():
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.name, Literal("Entity")))
    shapes_graph = Graph()
    shapes_graph.add((EXAMPLE.shape, RDF.type, SH.NodeShape))

    prepared = prepare_validation_graphs(data_graph, shapes_graph)

    assert prepared.data_graph is data_graph
    assert prepared.shapes_graph is shapes_graph


def test_requested_transformers_use_isolated_data_and_shapes_graphs():
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.name, Literal("Entity")))
    shapes_graph = Graph()
    shapes_graph.add((EXAMPLE.shape, RDF.type, SH.NodeShape))
    shapes_graph.add((EXAMPLE.shape, SH.closed, Literal(True)))
    target = BNode()
    shapes_graph.add((EXAMPLE.shape, SH.target, target))
    shapes_graph.add((target, RDF.type, SH.SPARQLTarget))
    shapes_graph.add((target, SH.select, Literal("SELECT ?this WHERE { ?this schema:name ?name }")))
    shapes_graph.add(
        (
            EXAMPLE.shape,
            REQUIRES_GRAPH_TRANSFORMER_PREDICATE,
            VALIDATION_CANDIDATE_TRANSFORMER,
        )
    )
    original_data = set(data_graph)
    original_shapes = set(shapes_graph)

    prepared = prepare_validation_graphs(data_graph, shapes_graph)

    assert prepared.data_graph is not data_graph
    assert prepared.shapes_graph is not shapes_graph
    assert (EXAMPLE.entity, VALIDATION_CANDIDATE_PREDICATE, Literal(True)) in prepared.data_graph
    assert (EXAMPLE.entity, VALIDATION_CANDIDATE_PREDICATE, None) not in data_graph
    assert (EXAMPLE.shape, SH.ignoredProperties, None) not in shapes_graph
    assert set(data_graph) == original_data
    assert set(shapes_graph) == original_shapes

    assert isinstance(prepared.shapes_graph, Graph)
    ignored_head = prepared.shapes_graph.value(EXAMPLE.shape, SH.ignoredProperties)
    assert isinstance(ignored_head, BNode)
    assert VALIDATION_CANDIDATE_PREDICATE in Collection(prepared.shapes_graph, ignored_head)
