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

from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urljoin


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
    """
    Find singleton arrays used for properties of flattened JSON-LD entities.

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


_COMPACTION_KEYWORDS = frozenset({"@id", "@type", "@context", "@value", "@language"})
_JSONLD_11 = 1.1
_URI_GEN_DELIMS = (":", "/", "?", "#", "[", "]", "@")


def resolve_compaction_context(
    context: object,
    load_remote: Callable[[str], object],
    *,
    base: str = "",
    remote_stack: tuple[str, ...] = (),
) -> dict[str, Any]:
    """
    Keep ordered term definitions instead of losing prefix mappings in a set.

    Remote retrieval belongs to the calling profile, preserving its HTTP,
    alternate-link and offline-cache behavior. Null contexts reset definitions;
    null term definitions remain present so they can disable an earlier mapping.
    """
    definitions: dict[str, Any] = {}

    def apply(source: object, source_base: str, stack: tuple[str, ...]) -> None:
        if source is None:
            definitions.clear()
        elif isinstance(source, list):
            for item in source:
                apply(item, source_base, stack)
        elif isinstance(source, str):
            uri = urljoin(source_base, source)
            if uri in stack:
                raise ValueError(f"Recursive JSON-LD context: {uri}")
            apply(load_remote(uri), uri, (*stack, uri))
        elif isinstance(source, dict):
            definitions.update(source)
            # Freeze namespace mappings when they are defined: redefining a
            # referenced prefix in a later context must not change earlier IRIs.
            for term, definition in source.items():
                iri = _mapped_iri(term, definitions)
                if iri is not None:
                    definitions[term] = {**definition, "@id": iri} if isinstance(definition, dict) else iri
        else:
            raise TypeError("JSON-LD context must be an object, URL, array or null")

    apply(context, base, remote_stack)
    return definitions


def _mapped_iri(term: str, definitions: Mapping[str, Any], seen: frozenset[str] = frozenset()) -> str | None:
    """Resolve a mapping expressed using another declared prefix, without cycles."""
    if term in seen:
        return None
    definition = definitions.get(term)
    iri = definition.get("@id") if isinstance(definition, dict) else definition
    if not isinstance(iri, str) or iri.startswith(("@", "_:")):
        return None
    prefix, separator, suffix = iri.partition(":")
    if separator and prefix in definitions and not suffix.startswith("//"):
        namespace = _mapped_iri(prefix, definitions, seen | {term})
        return namespace + suffix if namespace else None
    if not separator and iri in definitions:
        return _mapped_iri(iri, definitions, seen | {term})
    return iri if separator else None


def _is_compact_iri(key: str, definitions: Mapping[str, Any]) -> bool:
    prefix, separator, suffix = key.partition(":")
    if not separator or prefix == "_" or suffix.startswith("//"):
        return False
    iri = _mapped_iri(prefix, definitions)
    if iri is None:
        return False
    definition = definitions[prefix]
    # For this check, contexts without @version use the JSON-LD 1.0 policy,
    # matching the requirement for RO-Crate 1.1 and 1.2. This is a validator
    # policy; it does not infer the mode selected by a JSON-LD processor:
    # https://www.researchobject.org/ro-crate/specification/1.1/structure.html
    # https://www.researchobject.org/ro-crate/specification/1.2/structure.html
    # https://www.w3.org/TR/json-ld11/#json-ld-1-1-processing-mode
    if definitions.get("@version", 1.0) != _JSONLD_11:
        # In this check, a resolved mapping is enough to accept the key as a
        # compact IRI. JSON-LD 1.1's @prefix flag is handled explicitly below.
        return True
    # JSON-LD 1.1 distinguishes simple (string) and expanded (object) term
    # definitions when deciding whether a term can be used as a prefix:
    # https://www.w3.org/TR/json-ld11/#compact-iris
    if isinstance(definition, dict):
        # An object such as {"@id": "https://example.org/"} needs @prefix: true
        # to enable prefix use. Missing/false @prefix does not invalidate the
        # term definition itself; it only prevents using it as a prefix here.
        return definition.get("@prefix") is True
    # A simple mapping such as "ex": "https://example.org/" needs no @prefix,
    # but its IRI must end in a URI general delimiter (e.g. '/' or '#').
    return iri.endswith(_URI_GEN_DELIMS)


def find_unexpected_compaction_keys(entity: object, definitions: Mapping[str, Any]) -> dict[str, int]:
    """
    Count unmapped properties in the flat RO-Crate JSON-LD representation.

    Keep the existing explicit-term policy (including rejection of unmapped
    absolute IRI keys), but also accept eligible compact IRIs. Context and
    literal payloads are not node objects and must not be traversed as such.
    """
    unexpected: dict[str, int] = {}

    def visit(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                definition = definitions.get(key)
                defined = definition is not None and not (
                    isinstance(definition, dict) and "@id" in definition and definition["@id"] is None
                )
                if (
                    key not in _COMPACTION_KEYWORDS
                    and not defined
                    and (key in definitions or not _is_compact_iri(key, definitions))
                ):
                    unexpected[key] = unexpected.get(key, 0) + 1
                if key not in {"@context", "@value"}:
                    visit(item)

    visit(entity)
    return unexpected
