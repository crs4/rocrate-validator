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

from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, cast

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, SH

if TYPE_CHECKING:
    from rdflib.query import ResultRow

SCHEMA = Namespace("http://schema.org/")
DCT = Namespace("http://purl.org/dc/terms/")
RO_CRATE_1_1 = Namespace("https://github.com/crs4/rocrate-validator/profiles/ro-crate/")
RO_CRATE_1_2 = Namespace("https://github.com/crs4/rocrate-validator/profiles/ro-crate-1.2/")
PROFILE_1_1 = (
    Path(__file__).resolve().parents[4]
    / "rocrate_validator"
    / "profiles"
    / "ro-crate"
    / "1.1"
    / "must"
    / "4_data_entity_metadata.ttl"
)
PROFILE_1_2_SHOULD = (
    Path(__file__).resolve().parents[4]
    / "rocrate_validator"
    / "profiles"
    / "ro-crate"
    / "1.2"
    / "should"
    / "4_referenced_rocrate.ttl"
)


def _build_root_subquery_data_graph(entity_type, entity_count, about_count=249):
    """Build a data graph with entities and a root subquery pattern."""
    data_graph = Graph()
    root = URIRef("./")
    expected = set()
    for index in range(entity_count):
        entity = URIRef(f"entity-{index}.dat")
        expected.add(entity)
        data_graph.add((entity, RDF.type, entity_type))
    data_graph.add((URIRef("ro-crate-metadata.json"), SCHEMA.about, root))
    for index in range(about_count):
        about_entity = URIRef(f"about/entity-{index}")
        data_graph.add((about_entity, SCHEMA.about, root))
    return data_graph, expected, root


def test_file_data_entity_target_scales_without_cross_product():
    """The production target must pre-compute roots before joining entities."""
    shapes_graph = Graph().parse(PROFILE_1_1, format="turtle")
    target = shapes_graph.value(RO_CRATE_1_1.FileDataEntity, SH.target)
    query = str(shapes_graph.value(target, SH.select))

    # 500 entities + 250 about-entities + 1 descriptor = 501 triples.
    # Without the root subquery, rdflib would build a cross-product of
    # 500 x 250 = 125,000 intermediate rows before applying FILTERs.
    # With the subquery, the root is pre-computed to a single binding,
    # so the outer pattern processes only 500 combinations.
    data_graph, expected, _ = _build_root_subquery_data_graph(SCHEMA.MediaObject, 500)

    started_at = perf_counter()
    rows = data_graph.query(query, initNs={"schema": SCHEMA})
    actual = {cast("ResultRow", row).this for row in rows}
    duration = perf_counter() - started_at

    assert actual == expected
    assert duration < 3.0, f"FileDataEntity target took {duration:.2f}s; possible cross-product regression"


def test_directory_data_entity_target_scales_without_cross_product():
    """DirectoryDataEntity target must pre-compute roots before joining entities."""
    shapes_graph = Graph().parse(PROFILE_1_1, format="turtle")
    target = shapes_graph.value(RO_CRATE_1_1.DirectoryDataEntity, SH.target)
    query = str(shapes_graph.value(target, SH.select))

    # Same structure as FileDataEntity: 500 Dataset entities + 250 about-entities.
    # The root is excluded from results (FILTER ?this != ?root).
    data_graph, expected, root = _build_root_subquery_data_graph(SCHEMA.Dataset, 500)
    expected.discard(root)

    started_at = perf_counter()
    rows = data_graph.query(query, initNs={"schema": SCHEMA})
    actual = {cast("ResultRow", row).this for row in rows}
    duration = perf_counter() - started_at

    assert actual == expected
    assert duration < 3.0, f"DirectoryDataEntity target took {duration:.2f}s; possible cross-product regression"


def test_referenced_rocrate_data_entity_target_scales_without_cross_product():
    """ReferencedROCrateDataEntityTarget must pre-compute roots before joining."""
    shapes_graph = Graph().parse(PROFILE_1_2_SHOULD, format="turtle")
    query = str(shapes_graph.value(RO_CRATE_1_2.ReferencedROCrateDataEntityTarget, SH.select))

    # 500 Dataset entities with dct:conformsTo + 250 about-entities + 1 descriptor.
    # The target also filters by profile URI (STRSTARTS).
    data_graph, expected, root = _build_root_subquery_data_graph(SCHEMA.Dataset, 500)
    expected.discard(root)
    profile_uri = URIRef("https://w3id.org/ro/crate/1.1")
    for entity in expected:
        data_graph.add((entity, DCT.conformsTo, profile_uri))

    started_at = perf_counter()
    rows = data_graph.query(query, initNs={"schema": SCHEMA, "dct": DCT})
    actual = {cast("ResultRow", row).this for row in rows}
    duration = perf_counter() - started_at

    assert actual == expected
    assert duration < 3.0, f"ReferencedROCrateDataEntity target took {duration:.2f}s; possible cross-product regression"


def test_referenced_rocrate_metadata_descriptor_target_scales_without_cross_product():
    """ReferencedROCrateMetadataDescriptorTarget must pre-compute roots before joining."""
    shapes_graph = Graph().parse(PROFILE_1_2_SHOULD, format="turtle")
    query = str(shapes_graph.value(RO_CRATE_1_2.ReferencedROCrateMetadataDescriptorTarget, SH.select))

    # 1 crate with 500 subjectOf descriptors + 1 root descriptor.
    # Without the root subquery, the cross-product would be 500 x 1 = 500
    # (small here, but scales with multiple crates in real graphs).
    data_graph = Graph()
    root = URIRef("./")
    expected = set()
    crate = URIRef("referenced-crate/")
    profile_uri = URIRef("https://w3id.org/ro/crate/1.1")
    data_graph.add((crate, RDF.type, SCHEMA.Dataset))
    data_graph.add((crate, DCT.conformsTo, profile_uri))
    for index in range(500):
        descriptor = URIRef(f"descriptor-{index}")
        expected.add(descriptor)
        data_graph.add((crate, SCHEMA.subjectOf, descriptor))
    data_graph.add((URIRef("ro-crate-metadata.json"), SCHEMA.about, root))

    started_at = perf_counter()
    rows = data_graph.query(query, initNs={"schema": SCHEMA, "dct": DCT})
    actual = {cast("ResultRow", row).this for row in rows}
    duration = perf_counter() - started_at

    assert actual == expected
    assert duration < 3.0, (
        f"ReferencedROCrateMetadataDescriptor target took {duration:.2f}s; possible cross-product regression"
    )
