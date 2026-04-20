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

"""
Integration tests for SPARQL constraint handling in SHACL validation.

These tests verify that:
1. Violations from SPARQL constraints (where sourceShape is a BNode)
   are correctly resolved to their parent NodeShape/PropertyShape
2. The import cycle between utils.py and models.py is properly resolved
3. Error messages include appropriate context from the parent shape

The tests use a custom profile (sparql-test) that extends ro-crate
and includes a NodeShape with a sh:sparql constraint.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import pytest
from rdflib import BNode, Graph, Namespace, URIRef

from rocrate_validator import models, services
from rocrate_validator.models import Severity, ValidationResult
from rocrate_validator.requirements.shacl.models import Shape, ShapesRegistry
from rocrate_validator.requirements.shacl.utils import resolve_parent_shape
from tests.conftest import TEST_DATA_PATH


logger = logging.getLogger(__name__)

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

SPARQL_TEST_PROFILES_PATH = os.path.join(TEST_DATA_PATH, "profiles", "sparql_test")


@pytest.fixture
def sparql_test_profiles_path():
    """Path to the test profile with SPARQL constraints."""
    return SPARQL_TEST_PROFILES_PATH


@pytest.fixture
def sparql_test_rocrate():
    """Create a minimal valid RO-Crate for SPARQL constraint testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        rocrate_dir = Path(tmp_dir) / "sparql_test_crate"
        rocrate_dir.mkdir()

        metadata = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@graph": [
                {
                    "@id": "ro-crate-metadata.json",
                    "@type": "CreativeWork",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                    "about": {"@id": "./"},
                },
                {
                    "@id": "./",
                    "@type": "Dataset",
                    "name": "Test RO-Crate for SPARQL Constraints",
                    "description": "A minimal RO-Crate to test SPARQL constraint handling",
                    "datePublished": "2024-01-01",
                    "license": {"@id": "http://spdx.org/licenses/CC0-1.0"},
                },
            ],
        }

        with open(rocrate_dir / "ro-crate-metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        yield rocrate_dir


def test_sparql_profile_shape_loaded_correctly(sparql_test_profiles_path):
    """Test that the sparql-test profile loads the test shape with SPARQL constraint."""
    registry = ShapesRegistry()
    shape_file = os.path.join(
        sparql_test_profiles_path, "must", "agent_project_intersection.ttl"
    )

    shapes = registry.load_shapes(shape_file)

    assert len(shapes) > 0, "Should load at least one shape"

    # Find the test shape (AlwaysFailShape or similar name)
    test_shape = None
    for shape in shapes:
        if (
            "Always" in shape.name
            or "Test" in shape.name
            or "test" in shape.name.lower()
        ):
            test_shape = shape
            break

    assert test_shape is not None, "Should find the test SPARQL shape"
    assert test_shape.description is not None
    assert len(test_shape.description) > 0


def test_sparql_constraint_with_bnode_sourceShape(
    sparql_test_profiles_path, sparql_test_rocrate
):
    """
    Test that SPARQL constraint violations with BNode sourceShape
    are handled gracefully by the validation pipeline.

    Uses the sparql-test profile which includes AgentProjectIntersection
    shape with a sh:sparql constraint targeting ROCrateMetadataFileDescriptor.
    """
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=sparql_test_rocrate,
            requirement_severity=Severity.REQUIRED,
            profile_identifier="sparql-test",
            profiles_path=sparql_test_profiles_path,
        )
    )

    assert result is not None
    assert isinstance(result, ValidationResult)
    assert result.context is not None
    # The SPARQL constraint uses FILTER(true) so it should produce a violation
    issues = list(result.get_issues(Severity.REQUIRED))
    assert len(issues) > 0, "Expected issues from SPARQL constraint violation"
    assert issues[0].check is not None, "Issue should have an associated check"
    assert issues[0].check.description is not None, "Check should have a description"
    assert issues[0].message is not None, "Issue should have a message"
    assert len(issues[0].message) > 0, "Issue message should not be empty"
    assert (
        "SPARQL constraint violation" in issues[0].message
        or "SPARQL" in issues[0].check.description
    ), "Check description should reference parent shape"


def test_resolve_parent_shape_with_sparql_bnode():
    """
    Test resolve_parent_shape with a BNode representing a sh:sparql constraint.

    This simulates the scenario where pyshacl reports a violation with
    sourceShape being a BNode (the sh:SPARQLConstraint).
    """
    SHACL = Namespace("http://www.w3.org/ns/shacl#")

    registry = ShapesRegistry()
    profiles_path = "rocrate_validator/profiles/ro-crate/must"

    # Load shapes from profile
    for filename in os.listdir(profiles_path):
        if filename.endswith(".ttl"):
            registry.load_shapes(os.path.join(profiles_path, filename))

    g = Graph()

    # Simulate a NodeShape with a SPARQL constraint (BNode)
    node_shape_uri = URIRef("http://example.org/TestShape")
    sparql_bnode = BNode()

    g.add((node_shape_uri, SHACL.sparql, sparql_bnode))
    g.add((node_shape_uri, SHACL.targetClass, URIRef("http://example.org/TestClass")))

    # Create and register the shape
    shape = Shape(node_shape_uri, g)
    shape._name = "TestShape"
    shape._description = "Test shape for SPARQL constraint"
    registry.add_shape(shape)

    # Resolve the parent shape from the BNode
    result = resolve_parent_shape(g, sparql_bnode, registry)

    assert result is not None, "Should resolve parent shape for SPARQL BNode"
    assert result.key == shape.key, "Resolved shape key should match the original shape"
    assert result.name == "TestShape", "Resolved shape should have correct name"
