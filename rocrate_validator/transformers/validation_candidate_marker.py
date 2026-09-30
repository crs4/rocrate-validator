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

from __future__ import annotations

import logging

from rdflib import RDF, BNode, Dataset, Graph, Literal, Namespace, URIRef

from rocrate_validator.requirements.shacl.transformers import graph_transformer

logger = logging.getLogger(__name__)

# Private terms owned by this implementation. They exist only in the transient
# graph passed to pySHACL and are never serialized back into the RO-Crate.
MARKER_NS = Namespace("https://github.com/crs4/rocrate-validator/graph-transformers/")
VALIDATION_CANDIDATE_PREDICATE: URIRef = URIRef(MARKER_NS.validationCandidate)
VALIDATION_CANDIDATE_TRANSFORMER: URIRef = URIRef(MARKER_NS.validationCandidateMarker)

# These predicates point to an identifier, format, or vocabulary term without
# claiming that the object is an entity which the crate needs to describe.
REFERENCE_PREDICATES: frozenset[URIRef] = frozenset(
    {
        RDF.type,
        URIRef("http://schema.org/propertyID"),
        URIRef("http://schema.org/additionalType"),
        URIRef("http://www.w3.org/ns/csvw#propertyUrl"),
        URIRef("http://schema.org/inDefinedTermSet"),
        URIRef("http://schema.org/encodingFormat"),
        URIRef("http://purl.org/dc/terms/conformsTo"),
    }
)


# The default-stage order leaves lower values available for transformers that
# must normalize or annotate the graph before candidate classification.
@graph_transformer(
    identifier=VALIDATION_CANDIDATE_TRANSFORMER,
    order=100,
    annotation_predicates=(VALIDATION_CANDIDATE_PREDICATE,),
)
def mark_validation_candidates(data_graph: Graph) -> Graph:
    """
    Mark validation candidates identified from the current data graph.

    Classification is based exclusively on assertions from the original
    RO-Crate graph, before pySHACL adds ontology and inferred triples. A node is
    kept in validation scope when the crate asserts any outgoing statement
    about it, or when another entity points to it through a predicate that
    claims it as an entity (for example ``schema:author`` or
    ``schema:hasPart``).

    A positive marker keeps the validation scope stable when pySHACL later adds
    ontology and inferred terms which were not visible in the original graph.
    The orchestration layer provides a transient graph copy, so the validation
    context's cached source graph is never mutated.
    """
    described_or_claimed: set[URIRef | BNode] = set()

    triples = (
        ((subject, predicate, obj) for subject, predicate, obj, _ in data_graph.quads())
        if isinstance(data_graph, Dataset)
        else iter(data_graph)
    )
    for subject, predicate, obj in triples:
        if isinstance(subject, (URIRef, BNode)):
            described_or_claimed.add(subject)
        if isinstance(obj, (URIRef, BNode)) and predicate not in REFERENCE_PREDICATES:
            described_or_claimed.add(obj)

    marker_value = Literal(True)
    target_graph = data_graph.default_graph if isinstance(data_graph, Dataset) else data_graph
    for node in described_or_claimed:
        target_graph.add((node, VALIDATION_CANDIDATE_PREDICATE, marker_value))

    logger.debug(
        "Prepared validation graph with %d validation-candidate markers",
        len(described_or_claimed),
    )
    return data_graph


__all__ = [
    "VALIDATION_CANDIDATE_PREDICATE",
    "VALIDATION_CANDIDATE_TRANSFORMER",
    "mark_validation_candidates",
]
