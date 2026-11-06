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

import pytest
from pyshacl import validate
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, SH

PROFILES_PATH = Path(__file__).parents[3] / "rocrate_validator/profiles"
PROFILE_NAMESPACE_PREFIX = "https://github.com/crs4/rocrate-validator/profiles/"
SCHEMA = Namespace("http://schema.org/")
EXAMPLE = Namespace("https://example.org/")


def _parse_graph(path: Path) -> Graph:
    return Graph().parse(path, format="turtle")


def _profile_paths_with(*relative_paths: str) -> list[Path]:
    return [
        ontology_path.parent
        for ontology_path in sorted(PROFILES_PATH.rglob("ontology.ttl"))
        if all((ontology_path.parent / relative_path).is_file() for relative_path in relative_paths)
    ]


def _profile_id(profile_path: Path) -> str:
    return str(profile_path.relative_to(PROFILES_PATH))


def _collect_profile_namespaces(graph: Graph) -> set[str]:
    """
    Return declared validator namespaces that occur in actual graph terms.

    Ignoring unused prefix declarations keeps the comparison focused on the
    vocabulary IRIs that the artifact really uses.
    """
    declared_namespaces = {
        str(namespace) for _, namespace in graph.namespaces() if str(namespace).startswith(PROFILE_NAMESPACE_PREFIX)
    }
    terms = [str(term) for triple in graph for term in triple if isinstance(term, URIRef)]
    return {namespace for namespace in declared_namespaces if any(term.startswith(namespace) for term in terms)}


def _profile_vocabulary_namespace(graph: Graph) -> str:
    """Return the namespace explicitly bound as the artifact's own vocabulary."""
    try:
        return str(next(namespace for prefix, namespace in graph.namespaces() if prefix == "ro-crate"))
    except StopIteration as exc:
        raise AssertionError("The graph must bind its profile vocabulary to the `ro-crate` prefix") from exc


def _parse_profile_artifacts(profile_path: Path, *, exclude: set[Path] | None = None) -> Graph:
    graph = Graph()
    excluded_paths = exclude or set()
    for artifact_path in sorted(profile_path.rglob("*.ttl")):
        if artifact_path not in excluded_paths:
            graph.parse(artifact_path, format="turtle")
    return graph


@pytest.mark.parametrize("profile_path", _profile_paths_with("ontology.ttl"), ids=_profile_id)
def test_profile_ontology_uses_the_namespace_of_its_shapes(profile_path: Path) -> None:
    """
    The ontology's own profile vocabulary must also occur in its SHACL artifacts.

    This is the general invariant behind issue 193: if the ontology and shapes
    use different namespaces, a derived profile can target an ontology class
    that the base shapes never emit or target. External profile namespaces used
    only by bridge axioms do not become part of the local vocabulary.
    """
    ontology_path = profile_path / "ontology.ttl"
    ontology = _parse_graph(ontology_path)
    artifacts = _parse_profile_artifacts(profile_path, exclude={ontology_path})

    ontology_namespace = _profile_vocabulary_namespace(ontology)
    artifact_namespaces = _collect_profile_namespaces(artifacts)

    assert ontology_namespace in artifact_namespaces, (
        f"{ontology_path} uses the profile vocabulary {ontology_namespace}, but the profile's shapes do not"
    )


@pytest.mark.parametrize("profile_path", _profile_paths_with("ontology.ttl", "prefixes.ttl"), ids=_profile_id)
def test_sparql_prefixes_use_the_profile_ontology_namespace(profile_path: Path) -> None:
    """
    The SPARQL prefix registry must use the ontology's vocabulary namespace.

    SPARQL constraints rely on this registry to expand prefixed class IRIs; a
    different namespace would make those constraints refer to other resources.
    """
    ontology = _parse_graph(profile_path / "ontology.ttl")
    prefixes = _parse_graph(profile_path / "prefixes.ttl")

    ontology_namespace = _profile_vocabulary_namespace(ontology)
    prefix_namespaces = _collect_profile_namespaces(prefixes)

    assert prefix_namespaces == {ontology_namespace}, (
        f"{profile_path} prefixes must use the ontology's own namespace: "
        f"expected {ontology_namespace}, got {prefix_namespaces}"
    )


def test_ro_crate_1_3_maps_the_inherited_descriptor_marker() -> None:
    """The native 1.3 target class must match the marker emitted by inherited 1.2 discovery."""
    ontology = _parse_graph(PROFILES_PATH / "ro-crate/1.3/ontology.ttl")
    ro_crate_1_2 = Namespace("https://github.com/crs4/rocrate-validator/profiles/ro-crate-1.2/")
    ro_crate_1_3 = Namespace("https://github.com/crs4/rocrate-validator/profiles/ro-crate-1.3/")

    assert (
        ro_crate_1_3.ROCrateMetadataFileDescriptor,
        OWL.equivalentClass,
        ro_crate_1_2.ROCrateMetadataFileDescriptor,
    ) in ontology


@pytest.mark.parametrize(
    "profile_path",
    _profile_paths_with("ontology.ttl", "must/2_root_data_entity_metadata.ttl"),
    ids=_profile_id,
)
def test_root_data_entity_iri_matches_between_ontology_and_shacl(profile_path: Path):
    """
    The root-identification rule must emit the exact class IRI declared by the ontology.

    The assertion compares complete URI terms, not just the local name
    ``RootDataEntity``. This catches a namespace mismatch at the point where
    the base profile assigns the class to the root node.
    """
    ontology = _parse_graph(profile_path / "ontology.ttl")
    root_shapes = _parse_graph(profile_path / "must/2_root_data_entity_metadata.ttl")

    ontology_class = next(
        node
        for node in ontology.subjects(RDF.type, OWL.Class)
        if isinstance(node, URIRef) and str(node).endswith("/RootDataEntity")
    )

    assert (None, SH.object, ontology_class) in root_shapes, (
        "SHACL root-identification rule must reference the same RootDataEntity IRI as the ontology"
    )


@pytest.mark.parametrize(
    "profile_path",
    _profile_paths_with("ontology.ttl", "must/2_root_data_entity_metadata.ttl"),
    ids=_profile_id,
)
def test_external_shape_receives_focus_node_not_vacuous_conformance(profile_path: Path):
    """
    An external shape targeting the ontology class must receive a focus node.

    The test adds a root node with the ontology-declared class and applies an
    external shape requiring a missing ``schema:name``. With matching
    namespaces, validation finds the node and fails; with the original mismatch,
    it finds no focus node and incorrectly passes vacuously.
    """
    ontology = _parse_graph(profile_path / "ontology.ttl")
    root_class = next(
        node
        for node in ontology.subjects(RDF.type, OWL.Class)
        if isinstance(node, URIRef) and str(node).endswith("/RootDataEntity")
    )

    data = Graph()
    data.add((EXAMPLE.root, RDF.type, root_class))

    external_shapes = Graph()
    external_shapes.add((EXAMPLE.RootShape, RDF.type, SH.NodeShape))
    external_shapes.add((EXAMPLE.RootShape, SH.targetClass, root_class))
    external_shapes.add((EXAMPLE.RootShape, SH.property, EXAMPLE.RequiredName))
    external_shapes.add((EXAMPLE.RequiredName, SH.path, SCHEMA.name))
    external_shapes.add((EXAMPLE.RequiredName, SH.minCount, Literal(1)))

    conforms, _, _ = validate(
        data,
        shacl_graph=external_shapes,
        ont_graph=ontology,
        inference="owlrl",
    )

    assert not conforms, (
        "external shape must fail validation (missing required property), not pass vacuously due to namespace mismatch"
    )
