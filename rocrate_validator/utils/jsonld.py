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

from collections.abc import Mapping
from typing import Any


def _context_containers(context: object) -> dict[str, set[str]]:
    """Return explicit array-preserving containers for locally defined terms."""
    containers: dict[str, set[str]] = {}

    if isinstance(context, list):
        for item in context:
            containers.update(_context_containers(item))
    elif isinstance(context, dict):
        for term, definition in context.items():
            if not isinstance(term, str) or term.startswith("@"):
                continue
            if isinstance(definition, dict):
                raw_container = definition.get("@container")
                if isinstance(raw_container, str):
                    containers[term] = {raw_container}
                elif isinstance(raw_container, list):
                    containers[term] = {value for value in raw_container if isinstance(value, str)}
                else:
                    containers[term] = set()
            else:
                containers[term] = set()

    return containers


def find_singleton_property_arrays(metadata: Mapping[str, Any]) -> list[tuple[str | None, str]]:
    """Find singleton arrays used for properties of flattened JSON-LD entities.

    The RO-Crate ``@graph`` array and ``@context`` are structural JSON-LD
    arrays, not entity property values. JSON-LD keyword properties are also
    excluded. Explicit ``@set`` and ``@list`` containers preserve array
    semantics and must not be reported as non-compact property values.
    """
    graph = metadata.get("@graph")
    if not isinstance(graph, list):
        return []

    containers = _context_containers(metadata.get("@context"))
    findings: list[tuple[str | None, str]] = []
    for entity in graph:
        if not isinstance(entity, Mapping):
            continue
        entity_id = entity.get("@id")
        if entity_id is not None and not isinstance(entity_id, str):
            entity_id = str(entity_id)
        for property_name, value in entity.items():
            if not isinstance(property_name, str) or property_name.startswith("@"):
                continue
            if (
                isinstance(value, list)
                and len(value) == 1
                and not {"@set", "@list"}.intersection(containers.get(property_name, set()))
            ):
                findings.append((entity_id, property_name))
    return findings
