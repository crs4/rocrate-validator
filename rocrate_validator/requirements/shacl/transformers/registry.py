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

"""Registration metadata for SHACL graph transformers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from rdflib import URIRef

    from rocrate_validator.requirements.shacl.transformers.base import GraphTransformer, TransformerFunction


@dataclass(frozen=True)
class RegisteredTransformer:
    """A transformer definition together with its execution metadata."""

    identifier: URIRef
    name: str
    order: int
    annotation_predicates: frozenset[URIRef]
    implementation: TransformerFunction | type[GraphTransformer]


# Qualified names make registration idempotent when Python imports or reloads
# a transformer module more than once. A reload replaces the same definition
# instead of scheduling it twice.
_TRANSFORMERS: dict[str, RegisteredTransformer] = {}


def register_transformer(
    implementation: TransformerFunction | type[GraphTransformer],
    identifier: URIRef,
    order: int,
    annotation_predicates: Collection[URIRef] = (),
) -> None:
    """Register one implementation and reject identifier collisions."""
    name = f"{implementation.__module__}.{implementation.__qualname__}"
    duplicate = next(
        (
            transformer
            for registered_name, transformer in _TRANSFORMERS.items()
            if transformer.identifier == identifier and registered_name != name
        ),
        None,
    )
    if duplicate is not None:
        raise ValueError(f"Graph transformer identifier {identifier} is already registered by {duplicate.name}")
    _TRANSFORMERS[name] = RegisteredTransformer(
        identifier,
        name,
        order,
        frozenset(annotation_predicates),
        implementation,
    )


def graph_transformer(
    *,
    identifier: URIRef,
    order: int = 100,
    annotation_predicates: Collection[URIRef] = (),
) -> Callable[[TransformerFunction], TransformerFunction]:
    """Register a function as a graph transformer."""

    def decorator(function: TransformerFunction) -> TransformerFunction:
        register_transformer(function, identifier, order, annotation_predicates)
        return function

    return decorator


def get_registered_transformers(
    identifiers: Collection[URIRef] | None = None,
) -> tuple[RegisteredTransformer, ...]:
    """Return selected transformers in deterministic execution order."""
    transformers = tuple(_TRANSFORMERS.values())
    if identifiers is not None:
        requested = set(identifiers)
        registered = {item.identifier for item in transformers}
        unknown = requested - registered
        if unknown:
            unknown_list = ", ".join(sorted(map(str, unknown)))
            raise ValueError(f"Unknown graph transformer(s): {unknown_list}")
        transformers = tuple(item for item in transformers if item.identifier in requested)
    return tuple(sorted(transformers, key=lambda item: (item.order, item.name)))


__all__ = [
    "RegisteredTransformer",
    "get_registered_transformers",
    "graph_transformer",
    "register_transformer",
]
