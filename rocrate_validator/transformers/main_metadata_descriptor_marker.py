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

from urllib.parse import urljoin

from rdflib import Graph, Literal, Namespace, URIRef

from rocrate_validator.requirements.shacl.transformers import graph_transformer

MARKER_NS = Namespace("https://github.com/crs4/rocrate-validator/graph-transformers/")
MAIN_METADATA_DESCRIPTOR_PREDICATE: URIRef = URIRef(MARKER_NS.mainMetadataDescriptor)
MAIN_METADATA_DESCRIPTOR_TRANSFORMER: URIRef = URIRef(MARKER_NS.mainMetadataDescriptorMarker)

_SCHEMA_ABOUT = URIRef("http://schema.org/about")
_DESCRIPTOR_FILENAMES = ("ro-crate-metadata.json", "ro-crate-metadata.jsonld")


@graph_transformer(
    identifier=MAIN_METADATA_DESCRIPTOR_TRANSFORMER,
    order=50,
    annotation_predicates=(MAIN_METADATA_DESCRIPTOR_PREDICATE,),
)
def mark_main_metadata_descriptor(data_graph: Graph) -> Graph:
    """
    Mark the primary ``ro-crate-metadata.json`` (or ``.jsonld``) entity in the
    transient validation graph.

    When ``data_graph.base`` is known, only the descriptor resolved against that
    base is marked. When ``data_graph.base`` is unset (standalone SHACL runs),
    fall back to matching ``schema:about`` subjects whose URI ends with a
    canonical descriptor filename.
    """
    if data_graph.base:
        for descriptor_name in _DESCRIPTOR_FILENAMES:
            descriptor_uri = URIRef(urljoin(data_graph.base, descriptor_name))
            if (descriptor_uri, None, None) in data_graph:
                data_graph.add((descriptor_uri, MAIN_METADATA_DESCRIPTOR_PREDICATE, Literal(True)))
        return data_graph

    for subject in set(data_graph.subjects(_SCHEMA_ABOUT, None)):
        if isinstance(subject, URIRef) and str(subject).endswith(
            tuple(f"/{name}" for name in _DESCRIPTOR_FILENAMES) + _DESCRIPTOR_FILENAMES
        ):
            data_graph.add((subject, MAIN_METADATA_DESCRIPTOR_PREDICATE, Literal(True)))

    return data_graph
