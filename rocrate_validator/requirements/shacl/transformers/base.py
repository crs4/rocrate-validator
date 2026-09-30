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
from typing import ClassVar

from rdflib import Graph, URIRef

TransformerFunction = Callable[[Graph], Graph]


class GraphTransformer(ABC):
    """
    Base class for automatically registered graph transformers.

    Concrete subclasses are registered as soon as their module is imported.
    Abstract intermediate classes remain unregistered.
    """

    identifier: ClassVar[URIRef | None] = None
    order: ClassVar[int] = 100
    annotation_predicates: ClassVar[frozenset[URIRef]] = frozenset()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not inspect.isabstract(cls):
            if cls.identifier is None:
                raise TypeError(f"Graph transformer {cls.__module__}.{cls.__qualname__} has no identifier")
            # Imported lazily to keep the abstract contract independent from
            # the registry module which stores concrete implementations.
            from rocrate_validator.requirements.shacl.transformers.registry import (  # noqa: PLC0415
                register_transformer,
            )

            register_transformer(cls, cls.identifier, cls.order, cls.annotation_predicates)

    @abstractmethod
    def transform(self, data_graph: Graph) -> Graph:
        """Transform and return the graph passed by the orchestration pipeline."""


__all__ = ["GraphTransformer", "TransformerFunction"]
