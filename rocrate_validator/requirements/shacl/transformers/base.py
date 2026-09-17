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

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from rdflib import Graph

TransformerFunction = Callable[[Graph], Graph]


@dataclass(frozen=True)
class RegisteredTransformer:
    """A transformer definition together with its execution metadata."""

    name: str
    order: int
    implementation: TransformerFunction | type[GraphTransformer]


# Qualified names make registration idempotent when Python imports or reloads
# a transformer module more than once. A reload replaces the same definition
# instead of scheduling it twice.
_TRANSFORMERS: dict[str, RegisteredTransformer] = {}


def _register(
    implementation: TransformerFunction | type[GraphTransformer],
    order: int,
) -> None:
    name = f"{implementation.__module__}.{implementation.__qualname__}"
    _TRANSFORMERS[name] = RegisteredTransformer(name, order, implementation)


class GraphTransformer(ABC):
    """
    Base class for automatically registered graph transformers.

    Concrete subclasses are registered as soon as their module is imported.
    Abstract intermediate classes remain unregistered.
    """

    order: ClassVar[int] = 100

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not inspect.isabstract(cls):
            _register(cls, cls.order)

    @abstractmethod
    def transform(self, data_graph: Graph) -> Graph:
        """Transform and return the graph passed by the orchestration pipeline."""


def graph_transformer(*, order: int = 100) -> Callable[[TransformerFunction], TransformerFunction]:
    """Register a function as a graph transformer."""

    def decorator(function: TransformerFunction) -> TransformerFunction:
        _register(function, order)
        return function

    return decorator


def get_registered_transformers() -> tuple[RegisteredTransformer, ...]:
    """Return registered transformers in deterministic execution order."""
    # Lower values run first. The qualified name is a deterministic tie-breaker
    # so execution never depends on filesystem or import iteration order.
    return tuple(sorted(_TRANSFORMERS.values(), key=lambda item: (item.order, item.name)))


def run_registered_transformers(data_graph: Graph) -> Graph:
    """Run every registered transformer sequentially on the same graph."""
    transformed_graph = data_graph
    for registered in get_registered_transformers():
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
