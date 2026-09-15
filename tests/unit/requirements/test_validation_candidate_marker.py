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

import pytest
from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import SH

from rocrate_validator.graph_transformers import (
    VALIDATION_CANDIDATE_PREDICATE,
    prepare_data_graph,
)
from rocrate_validator.requirements.shacl import SHACLValidator

SCHEMA = Namespace("http://schema.org/")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
EXAMPLE = Namespace("https://example.org/")


def _is_validation_candidate(graph: Graph, iri: URIRef) -> bool:
    return (iri, VALIDATION_CANDIDATE_PREDICATE, Literal(True)) in graph


@pytest.mark.parametrize(
    "predicate",
    [
        RDF.type,
        SCHEMA.propertyID,
        CSVW.propertyUrl,
        SCHEMA.inDefinedTermSet,
        SCHEMA.encodingFormat,
        DCTERMS.conformsTo,
    ],
)
def test_reference_objects_are_marked_cited_only(predicate: URIRef):
    data_graph = Graph()
    term = EXAMPLE["term"]
    data_graph.add((EXAMPLE.entity, predicate, term))

    validation_graph = prepare_data_graph(data_graph)

    assert not _is_validation_candidate(validation_graph, term)


@pytest.mark.parametrize("predicate", [SCHEMA.author, SCHEMA.hasPart])
def test_claimed_objects_remain_in_validation_scope(predicate: URIRef):
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, predicate, EXAMPLE.claimed))

    validation_graph = prepare_data_graph(data_graph)

    assert _is_validation_candidate(validation_graph, EXAMPLE.claimed)


def test_described_subject_remains_in_validation_scope():
    data_graph = Graph()
    data_graph.add((EXAMPLE.described, RDF.type, SCHEMA.Person))
    data_graph.add((EXAMPLE.described, SCHEMA.name, Literal("A person")))

    validation_graph = prepare_data_graph(data_graph)

    assert _is_validation_candidate(validation_graph, EXAMPLE.described)
    assert not _is_validation_candidate(validation_graph, SCHEMA.Person)


def test_claimed_vocabulary_term_is_a_validation_candidate():
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.author, EXAMPLE.ontology_term))

    validation_graph = prepare_data_graph(data_graph)

    assert _is_validation_candidate(validation_graph, EXAMPLE.ontology_term)


def test_node_absent_from_original_graph_is_not_a_validation_candidate():
    data_graph = Graph()

    validation_graph = prepare_data_graph(data_graph)

    assert not _is_validation_candidate(validation_graph, EXAMPLE.ontology_term)


def test_preparation_does_not_mutate_input_graphs():
    data_graph = Graph()
    term = EXAMPLE["term"]
    data_graph.add((EXAMPLE.entity, SCHEMA.propertyID, term))
    original_data_triples = set(data_graph)

    validation_graph = prepare_data_graph(data_graph)

    assert validation_graph is not data_graph
    assert set(data_graph) == original_data_triples
    assert len(validation_graph) > len(data_graph)


@pytest.mark.parametrize("serialized", [False, True])
def test_shacl_validator_prepares_graph_before_validation(serialized: bool):
    shape = EXAMPLE.marker_shape
    target = BNode()
    property_shape = BNode()
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, SH.target, target))
    shapes_graph.add(
        (
            target,
            SH.select,
            Literal(
                f"SELECT ?this WHERE {{ ?this a <{SCHEMA.Person}> . "
                f"FILTER EXISTS {{ ?this <{VALIDATION_CANDIDATE_PREDICATE}> true }} }}"
            ),
        )
    )
    shapes_graph.add((target, RDF.type, SH.SPARQLTarget))
    shapes_graph.add((shape, SH.property, property_shape))
    shapes_graph.add((property_shape, SH.path, SCHEMA.name))
    shapes_graph.add((property_shape, SH.minCount, Literal(1)))
    shapes_graph.add((property_shape, SH.message, Literal("A person needs a name")))

    person = EXAMPLE.person
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.author, person))
    data_graph.add((person, RDF.type, SCHEMA.Person))
    original_triples = set(data_graph)

    source = data_graph.serialize(format="turtle").encode() if serialized else data_graph
    result = SHACLValidator(shapes_graph=shapes_graph).validate(source)

    assert not result.conforms
    assert any(violation.focusNode == person for violation in result.violations)
    assert set(data_graph) == original_triples
