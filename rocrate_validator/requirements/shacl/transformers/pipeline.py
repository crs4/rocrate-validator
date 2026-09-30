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

"""Execution pipeline for registered graph transformers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import Dataset, Graph

from rocrate_validator.requirements.shacl.transformers.discovery import load_transformers
from rocrate_validator.requirements.shacl.transformers.registry import get_registered_transformers

if TYPE_CHECKING:
    from collections.abc import Collection

    from rdflib import URIRef


def _copy_data_graph(source: Graph) -> Graph:
    """Copy a data graph without flattening RDFLib dataset contexts."""
    if isinstance(source, Dataset):
        target: Graph = Dataset(
            default_union=source.default_union,
            default_graph_base=source.default_graph.base,
        )
    else:
        target = Graph(identifier=source.identifier, base=source.base)

    for prefix, namespace in source.namespaces():
        target.bind(prefix, namespace, replace=True)

    if isinstance(source, Dataset):
        assert isinstance(target, Dataset)
        for subject, predicate, obj, context in source.quads((None, None, None, None)):
            context_graph = (
                target.default_graph if context == source.default_graph.identifier else target.graph(context)
            )
            context_graph.add((subject, predicate, obj))
    else:
        for triple in source:
            target.add(triple)
    return target


def prepare_data_graph(
    data_graph: Graph,
    transformer_identifiers: Collection[URIRef] | None = None,
) -> Graph:
    """Run selected transformers on one transient copy of a data graph.

    Passing ``None`` preserves the low-level helper's original behaviour and
    runs every registered transformer. The caller-owned source graph is never
    passed to transformer code.
    """
    load_transformers()
    return run_registered_transformers(_copy_data_graph(data_graph), transformer_identifiers)


def run_registered_transformers(
    data_graph: Graph,
    identifiers: Collection[URIRef] | None = None,
) -> Graph:
    """Run the selected registered transformers sequentially."""
    transformed_graph = data_graph
    for registered in get_registered_transformers(identifiers):
        # Class transformers are deliberately instantiated without arguments;
        # persistent state must not leak between separate validation runs.
        implementation = registered.implementation
        if isinstance(implementation, type):
            transformed_graph = implementation().transform(transformed_graph)
        else:
            transformed_graph = implementation(transformed_graph)
        if not isinstance(transformed_graph, Graph):
            raise TypeError(f"Graph transformer {registered.name} did not return an RDFLib Graph")
    return transformed_graph


__all__ = ["prepare_data_graph", "run_registered_transformers"]
