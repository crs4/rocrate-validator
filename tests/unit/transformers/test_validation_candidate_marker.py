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
from rdflib import RDF, BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import SH

from rocrate_validator.requirements.shacl import SHACLValidator
from rocrate_validator.requirements.shacl.errors import SHACLValidationError
from rocrate_validator.requirements.shacl.transformers import (
    REQUIRES_GRAPH_TRANSFORMER_PREDICATE,
    prepare_data_graph,
)
from rocrate_validator.transformers.validation_candidate_marker import (
    VALIDATION_CANDIDATE_PREDICATE,
    VALIDATION_CANDIDATE_TRANSFORMER,
)

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
        SCHEMA.additionalType,
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


@pytest.mark.parametrize("subject", [EXAMPLE.type_only, BNode("type-only")])
def test_type_only_subject_remains_in_validation_scope(subject: URIRef | BNode):
    data_graph = Graph()
    data_graph.add((subject, RDF.type, SCHEMA.Person))

    validation_graph = prepare_data_graph(data_graph)

    assert _is_validation_candidate(validation_graph, subject)
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
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))
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


def test_serialized_shapes_can_request_graph_transformers():
    shape = EXAMPLE.marker_shape
    target = BNode()
    property_shape = BNode()
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))
    shapes_graph.add((shape, SH.target, target))
    shapes_graph.add((target, RDF.type, SH.SPARQLTarget))
    shapes_graph.add(
        (
            target,
            SH.select,
            Literal(f"SELECT ?this WHERE {{ ?this <{VALIDATION_CANDIDATE_PREDICATE}> true }}"),
        )
    )
    shapes_graph.add((shape, SH.property, property_shape))
    shapes_graph.add((property_shape, SH.path, SCHEMA.name))
    shapes_graph.add((property_shape, SH.minCount, Literal(1)))
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.author, EXAMPLE.person))

    result = SHACLValidator(shapes_graph=shapes_graph.serialize(format="turtle").encode()).validate(
        data_graph,
        shacl_graph_format="turtle",
    )

    assert not result.conforms
    assert any(violation.focusNode in {EXAMPLE.entity, EXAMPLE.person} for violation in result.violations)


def _closed_shape() -> Graph:
    shape = EXAMPLE.closed_shape
    property_shape = BNode()
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, SH.targetNode, EXAMPLE.entity))
    shapes_graph.add((shape, SH.closed, Literal(True)))
    shapes_graph.add((shape, SH.property, property_shape))
    shapes_graph.add((property_shape, SH.path, SCHEMA.name))
    return shapes_graph


def test_unrequested_transformers_do_not_change_closed_shapes():
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.name, Literal("Entity")))

    result = SHACLValidator(shapes_graph=_closed_shape()).validate(data_graph)

    assert result.conforms


def test_transformer_annotations_are_ignored_by_closed_shapes():
    data_graph = Graph()
    data_graph.add((EXAMPLE.entity, SCHEMA.name, Literal("Entity")))
    shapes_graph = _closed_shape()
    shapes_graph.add(
        (
            EXAMPLE.closed_shape,
            REQUIRES_GRAPH_TRANSFORMER_PREDICATE,
            VALIDATION_CANDIDATE_TRANSFORMER,
        )
    )

    result = SHACLValidator(shapes_graph=shapes_graph).validate(data_graph)

    assert result.conforms


def test_dataset_named_graphs_are_preserved_during_preparation():
    data_graph = Dataset()
    data_graph.graph(EXAMPLE.named_graph).add((EXAMPLE.entity, SCHEMA.name, Literal("Entity")))
    original_quads = set(data_graph.quads((None, None, None, None)))
    shape = EXAMPLE.dataset_shape
    property_shape = BNode()
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, SH.targetSubjectsOf, SCHEMA.name))
    shapes_graph.add((shape, SH.property, property_shape))
    shapes_graph.add((property_shape, SH.path, SCHEMA.description))
    shapes_graph.add((property_shape, SH.minCount, Literal(1)))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))

    result = SHACLValidator(shapes_graph=shapes_graph).validate(data_graph)

    assert not result.conforms
    assert any(violation.focusNode == EXAMPLE.entity for violation in result.violations)
    assert set(data_graph.quads((None, None, None, None))) == original_quads
    assert not data_graph.default_union


def test_serialized_parse_errors_keep_shacl_error_contract():
    shape = EXAMPLE.marker_shape
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))

    with pytest.raises(SHACLValidationError, match="BadSyntax") as exc_info:
        SHACLValidator(shapes_graph=shapes_graph).validate(
            b"@prefix broken",
            data_graph_format="turtle",
        )

    assert exc_info.value.__cause__ is not None


def test_inplace_remains_effective_without_requested_transformers():
    shape = EXAMPLE.rule_shape
    rule = BNode()
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, SH.targetNode, EXAMPLE.entity))
    shapes_graph.add((shape, SH.rule, rule))
    shapes_graph.add((rule, RDF.type, SH.TripleRule))
    shapes_graph.add((rule, SH.subject, SH.this))
    shapes_graph.add((rule, SH.predicate, EXAMPLE.generated))
    shapes_graph.add((rule, SH.object, Literal("yes")))
    data_graph = Graph()

    SHACLValidator(shapes_graph=shapes_graph).validate(data_graph, inplace=True)

    assert (EXAMPLE.entity, EXAMPLE.generated, Literal("yes")) in data_graph


def test_inplace_is_rejected_for_transformer_dependent_shapes():
    shape = EXAMPLE.marker_shape
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))

    with pytest.raises(ValueError, match="inplace=True"):
        SHACLValidator(shapes_graph=shapes_graph).validate(Graph(), inplace=True)


def test_sparql_mode_is_rejected_for_transformer_dependent_shapes():
    shape = EXAMPLE.marker_shape
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, VALIDATION_CANDIDATE_TRANSFORMER))

    with pytest.raises(ValueError, match="sparql_mode"):
        SHACLValidator(shapes_graph=shapes_graph).validate(
            "https://example.org/sparql",
            sparql_mode=True,
        )


def test_unknown_requested_transformer_fails_validation():
    shape = EXAMPLE.marker_shape
    shapes_graph = Graph()
    shapes_graph.add((shape, RDF.type, SH.NodeShape))
    shapes_graph.add((shape, REQUIRES_GRAPH_TRANSFORMER_PREDICATE, EXAMPLE.unknown_transformer))

    with pytest.raises(SHACLValidationError, match="Unknown graph transformer"):
        SHACLValidator(shapes_graph=shapes_graph).validate(Graph())
