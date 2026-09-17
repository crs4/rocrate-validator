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

import importlib
import pkgutil
from threading import Lock

from rdflib import Dataset, Graph

from rocrate_validator.requirements.shacl.transformers.base import (
    GraphTransformer,
    graph_transformer,
    run_registered_transformers,
)
from rocrate_validator.requirements.shacl.transformers.vocabulary import VALIDATION_CANDIDATE_PREDICATE

_DISCOVERY_LOCK = Lock()
_TRANSFORMERS_LOADED = False


def _load_concrete_transformers() -> None:
    """
    Import every transformer module in this package exactly once.

    Importing triggers function decorators and ``GraphTransformer`` subclass
    hooks. The lock prevents concurrent validations from observing a partially
    populated registry during first use.
    """
    global _TRANSFORMERS_LOADED  # noqa: PLW0603
    if _TRANSFORMERS_LOADED:
        return
    with _DISCOVERY_LOCK:
        if _TRANSFORMERS_LOADED:
            return
        package_prefix = f"{__name__}."
        for module in pkgutil.walk_packages(__path__, package_prefix):
            if module.name != f"{__name__}.base":
                importlib.import_module(module.name)
        _TRANSFORMERS_LOADED = True


def _copy_graph(source: Graph) -> Graph:
    """Return a validation-only copy, including namespace bindings."""
    identifier = source.default_graph.identifier if isinstance(source, Dataset) else source.identifier
    target = Graph(identifier=identifier)
    for prefix, namespace in source.namespaces():
        target.bind(prefix, namespace, replace=True)
    # Dataset iteration yields quads; copy the union view as triples so the
    # transient validation graph has the same shape for Graph and Dataset input.
    for triple in source.triples((None, None, None)):
        target.add(triple)
    return target


def prepare_data_graph(data_graph: Graph) -> Graph:
    """Discover and run all concrete transformers on a transient graph copy.

    The copy is created once for the complete pipeline. Each transformer sees
    the output of its predecessor, while the cached graph owned by the
    validation context remains untouched.
    """
    _load_concrete_transformers()
    return run_registered_transformers(_copy_graph(data_graph))


__all__ = [
    "VALIDATION_CANDIDATE_PREDICATE",
    "GraphTransformer",
    "graph_transformer",
    "prepare_data_graph",
]
