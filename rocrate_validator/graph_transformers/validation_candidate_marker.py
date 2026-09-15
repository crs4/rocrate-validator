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

from rdflib import RDF, BNode, Graph, Literal, URIRef

from rocrate_validator.graph_transformers.base import graph_transformer
from rocrate_validator.graph_transformers.vocabulary import VALIDATION_CANDIDATE_PREDICATE

logger = logging.getLogger(__name__)

# These predicates point to an identifier, format, or vocabulary term without
# claiming that the object is an entity which the crate needs to describe.
REFERENCE_PREDICATES: frozenset[URIRef] = frozenset(
    {
        RDF.type,
        URIRef("http://schema.org/propertyID"),
        URIRef("http://www.w3.org/ns/csvw#propertyUrl"),
        URIRef("http://schema.org/inDefinedTermSet"),
        URIRef("http://schema.org/encodingFormat"),
        URIRef("http://purl.org/dc/terms/conformsTo"),
    }
)


# The default-stage order leaves lower values available for transformers that
# must normalize or annotate the graph before candidate classification.
@graph_transformer(order=100)
def mark_validation_candidates(data_graph: Graph) -> Graph:
    """
    Mark validation candidates identified from the current data graph.

    Classification is based exclusively on assertions from the original
    RO-Crate graph, before pySHACL adds ontology and inferred triples. An IRI is
    kept in validation scope when the crate describes it with a predicate other
    than ``rdf:type``, or when another entity points to it through a predicate
    that claims it as an entity (for example ``schema:author`` or
    ``schema:hasPart``).

    A positive marker keeps the validation scope stable when pySHACL later adds
    ontology and inferred terms which were not visible in the original graph.
    The orchestration layer provides a transient graph copy, so the validation
    context's cached source graph is never mutated.
    """
    described_or_claimed: set[URIRef | BNode] = set()

    for subject, predicate, obj in data_graph:
        if isinstance(subject, (URIRef, BNode)) and predicate != RDF.type:
            described_or_claimed.add(subject)
        if isinstance(obj, (URIRef, BNode)) and predicate not in REFERENCE_PREDICATES:
            described_or_claimed.add(obj)

    marker_value = Literal(True)
    for node in described_or_claimed:
        data_graph.add((node, VALIDATION_CANDIDATE_PREDICATE, marker_value))

    logger.debug(
        "Prepared validation graph with %d validation-candidate markers",
        len(described_or_claimed),
    )
    return data_graph
