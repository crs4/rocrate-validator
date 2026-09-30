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

"""SHACL integration for graph-transformer-dependent validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from pyshacl.monkey import rdflib_bool_patch, rdflib_bool_unpatch
from pyshacl.rdfutil.load import load_from_source
from rdflib import RDF, BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.requirements.shacl.transformers.discovery import load_transformers
from rocrate_validator.requirements.shacl.transformers.pipeline import prepare_data_graph
from rocrate_validator.requirements.shacl.transformers.registry import get_registered_transformers
from rocrate_validator.requirements.shacl.transformers.vocabulary import (
    REQUIRES_GRAPH_TRANSFORMER_PREDICATE,
)

logger = logging.getLogger(__name__)

GraphSource = Graph | str | bytes
ShapesSource = GraphSource | None


class GraphTransformerCompatibilityError(ValueError):
    """Raised when pySHACL options cannot support requested transformers."""


@dataclass(frozen=True)
class PreparedValidationGraphs:
    """Data and shapes sources prepared for one pySHACL invocation."""

    data_graph: GraphSource
    shapes_graph: ShapesSource


def prepare_validation_graphs(
    data_graph: GraphSource,
    shapes_graph: ShapesSource,
    *,
    data_graph_format: str | None = None,
    shacl_graph_format: str | None = None,
    do_owl_imports: bool | int = False,
    inplace: bool = False,
    sparql_mode: bool = False,
) -> PreparedValidationGraphs:
    """Apply graph transformers explicitly requested by SHACL shapes.

    Shapes without a transformer declaration leave caller-owned graph objects
    untouched. Transformer-dependent validation receives private data and
    shapes copies suitable for a single pySHACL invocation.
    """
    inspected_shapes = _load_shapes_for_inspection(
        shapes_graph,
        rdf_format=shacl_graph_format,
        do_owl_imports=do_owl_imports,
    )
    if inspected_shapes is None:
        return PreparedValidationGraphs(data_graph, shapes_graph)

    required_transformers = _get_required_transformers(inspected_shapes)
    if not required_transformers:
        # Reuse an already parsed serialized source instead of asking pySHACL
        # to parse it a second time. Existing Graph inputs remain unchanged.
        return PreparedValidationGraphs(data_graph, inspected_shapes)

    _validate_options(required_transformers, inplace=inplace, sparql_mode=sparql_mode)
    annotation_predicates = _get_annotation_predicates(required_transformers)
    prepared_shapes = _copy_shapes_graph(inspected_shapes)
    _ignore_annotations_in_closed_shapes(prepared_shapes, annotation_predicates)
    prepared_data = _load_data_graph(data_graph, rdf_format=data_graph_format)
    prepared_data = prepare_data_graph(prepared_data, required_transformers)
    return PreparedValidationGraphs(prepared_data, prepared_shapes)


def _load_shapes_for_inspection(
    source: ShapesSource,
    *,
    rdf_format: str | None,
    do_owl_imports: bool | int,
) -> Graph | None:
    if source is None:
        return None
    if isinstance(source, Graph) and not do_owl_imports:
        return source

    load_source: GraphSource = _copy_shapes_graph(source) if isinstance(source, Graph) else source
    rdflib_bool_patch()
    try:
        return cast(
            "Graph",
            load_from_source(
                load_source,
                rdf_format=rdf_format,
                multigraph=True,
                do_owl_imports=do_owl_imports,
                logger=logger,
            ),
        )
    finally:
        rdflib_bool_unpatch()


def _load_data_graph(source: GraphSource, *, rdf_format: str | None) -> Graph:
    if isinstance(source, Graph):
        return source
    return cast(
        "Graph",
        load_from_source(
            source,
            rdf_format=rdf_format,
            multigraph=True,
            do_owl_imports=False,
            logger=logger,
        ),
    )


def _copy_shapes_graph(source: Graph) -> Graph:
    """Flatten a shapes source into an isolated graph for private changes."""
    identifier = source.default_graph.identifier if isinstance(source, Dataset) else source.identifier
    target = Graph(identifier=identifier, base=source.base)
    for prefix, namespace in source.namespaces():
        target.bind(prefix, namespace, replace=True)
    if isinstance(source, Dataset):
        for subject, predicate, obj, _ in source.quads((None, None, None, None)):
            target.add((subject, predicate, obj))
    else:
        for triple in source:
            target.add(triple)
    return target


def _get_required_transformers(shapes_graph: Graph) -> frozenset[URIRef]:
    identifiers: set[URIRef] = set()
    for identifier in shapes_graph.objects(None, REQUIRES_GRAPH_TRANSFORMER_PREDICATE):
        if not isinstance(identifier, URIRef):
            raise TypeError("Graph transformer identifiers declared by SHACL shapes must be IRIs")
        identifiers.add(identifier)
    return frozenset(identifiers)


def _get_annotation_predicates(transformer_identifiers: frozenset[URIRef]) -> frozenset[URIRef]:
    load_transformers()
    return frozenset(
        predicate
        for transformer in get_registered_transformers(transformer_identifiers)
        for predicate in transformer.annotation_predicates
    )


def _validate_options(
    required_transformers: frozenset[URIRef],
    *,
    inplace: bool,
    sparql_mode: bool,
) -> None:
    if not required_transformers:
        return
    if sparql_mode:
        raise GraphTransformerCompatibilityError(
            "sparql_mode cannot be used with graph-transformer-dependent SHACL shapes"
        )
    if inplace:
        raise GraphTransformerCompatibilityError(
            "inplace=True cannot be used when SHACL shapes require graph transformers"
        )


def _ignore_annotations_in_closed_shapes(
    shapes_graph: Graph,
    annotation_predicates: frozenset[URIRef],
) -> None:
    if not annotation_predicates:
        return

    shacl_ns = Namespace(SHACL_NS)
    for shape in shapes_graph.subjects(shacl_ns.closed, Literal(True)):
        list_head = shapes_graph.value(shape, shacl_ns.ignoredProperties)
        if list_head is None or list_head == RDF.nil:
            if list_head == RDF.nil:
                shapes_graph.remove((shape, shacl_ns.ignoredProperties, RDF.nil))
            list_head = BNode()
            shapes_graph.add((shape, shacl_ns.ignoredProperties, list_head))
        ignored_properties = Collection(shapes_graph, list_head)
        existing = set(ignored_properties)
        for predicate in sorted(annotation_predicates, key=str):
            if predicate not in existing:
                ignored_properties.append(predicate)


__all__ = [
    "GraphTransformerCompatibilityError",
    "PreparedValidationGraphs",
    "prepare_validation_graphs",
]
