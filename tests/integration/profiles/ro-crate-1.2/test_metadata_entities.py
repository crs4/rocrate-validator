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

import json
import logging

from rdflib import Graph, Literal, URIRef

from rocrate_validator import models, services
from rocrate_validator.requirements.shacl.transformers import prepare_data_graph
from rocrate_validator.transformers.validation_candidate_marker import VALIDATION_CANDIDATE_PREDICATE
from tests.ro_crates_v1_2 import MetadataEntities
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


__metadata_entities__ = MetadataEntities()


def _validate_metadata(rocrate_path, metadata):
    return services.validate(
        models.ValidationSettings(
            rocrate_uri=models.URI(rocrate_path),
            requirement_severity=models.Severity.RECOMMENDED,
            profile_identifier="ro-crate-1.2",
            metadata_dict=metadata,
        )
    )


def test_valid_recommended_schema_type():
    """
    Test that the metadata document includes at least one Schema.org type.
    """
    do_entity_test(
        __metadata_entities__.valid_recommended_schema_type,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_schema_type_warning():
    """
    Test that a warning is triggered when the metadata document
    does not include at least one Schema.org type.
    """
    do_entity_test(
        __metadata_entities__.invalid_recommended_schema_type,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Metadata Entity: RECOMMENDED properties"],
        expected_triggered_issues=["RO-Crate Metadata Entity SHOULD include at least one Schema.org type"],
    )


def test_valid_recommended_entity_name():
    """
    Test that the metadata document includes a `name` property for at least one entity.
    """
    do_entity_test(
        __metadata_entities__.valid_recommended_name,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_recommended_entity_name_warning():
    """
    Test that a warning is triggered when the metadata document
    does not include a `name` property for at least one entity.
    """
    do_entity_test(
        __metadata_entities__.invalid_recommended_name,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["RO-Crate Metadata Entity: RECOMMENDED properties"],
        expected_triggered_issues=["Entities SHOULD have a human-readable name"],
    )


def test_orcid_scheme_reference_is_not_validated_as_an_entity():
    """An identifier scheme referenced through propertyID is only cited."""
    rocrate_path = __metadata_entities__.valid_recommended_schema_type
    metadata = json.loads((rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    root = next(entity for entity in metadata["@graph"] if entity["@id"] == "./")
    root["identifier"] = [root["identifier"], {"@id": "#orcid-reference"}]
    metadata["@graph"].append(
        {
            "@id": "#orcid-reference",
            "@type": "PropertyValue",
            "name": "ORCID identifier scheme",
            "propertyID": {"@id": "https://orcid.org"},
            "value": "ORCID",
        }
    )

    result = _validate_metadata(rocrate_path, metadata)

    assert result.passed()
    assert not any(issue.violatingEntity == "https://orcid.org" for issue in result.issues)


def test_orcid_person_claimed_as_author_remains_in_validation_scope():
    """A person under the same ORCID namespace is claimed, not merely cited."""
    rocrate_path = __metadata_entities__.valid_recommended_schema_type
    metadata = json.loads((rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    person_id = "https://orcid.org/0009-0000-5074-6239"
    root = next(entity for entity in metadata["@graph"] if entity["@id"] == "./")
    root["author"] = {"@id": person_id}
    metadata["@graph"].append({"@id": person_id, "@type": "Person"})

    result = _validate_metadata(rocrate_path, metadata)

    assert not result.passed()
    assert any(
        issue.violatingEntity == person_id and issue.message == "Entities SHOULD have a human-readable name"
        for issue in result.get_issues(models.Severity.RECOMMENDED)
    )


def test_type_only_blank_node_remains_in_contextual_entity_scope():
    """A blank node asserted by the crate is not an external vocabulary term."""
    rocrate_path = __metadata_entities__.valid_recommended_schema_type
    metadata = json.loads((rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    metadata["@graph"].append({"@id": "_:type-only-person", "@type": "Person"})

    result = _validate_metadata(rocrate_path, metadata)

    assert any(
        issue.violatingEntity == "type-only-person"
        and issue.message == "A Contextual Entity MUST have a `name` property"
        for issue in result.get_issues(models.Severity.RECOMMENDED)
    )
    assert any(
        issue.violatingEntity == "type-only-person"
        and issue.message == "Contextual entities SHOULD be referenced by other entities."
        for issue in result.get_issues(models.Severity.RECOMMENDED)
    )


def test_valid_preprocessing_candidates_fixture_keeps_citations_out_of_scope():
    """Cited-only vocabulary IRIs are ignored while described claims remain valid."""
    rocrate_path = __metadata_entities__.valid_preprocessing_candidates
    metadata = json.loads((rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))

    result = _validate_metadata(rocrate_path, metadata)

    assert result.passed()
    cited_only_ids = {
        "https://vocab.example.org/identifier-scheme",
        "https://vocab.example.org/identifier-vocabulary",
        "https://vocab.example.org/formats/uuid",
        "https://vocab.example.org/profiles/property-value",
        "https://vocab.example.org/properties/uuid",
        "https://vocab.example.org/types/CustomEntity",
    }
    assert not any(issue.violatingEntity in cited_only_ids for issue in result.issues)


def test_preprocessing_candidates_fixture_marks_claims_and_descriptions_only():
    """The fixture exercises both positive and cited-only preprocessing paths."""
    rocrate_path = __metadata_entities__.valid_preprocessing_candidates
    metadata = (rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8")
    graph = Graph().parse(
        data=metadata,
        format="json-ld",
        publicID="https://example.org/preprocessing-candidates/ro-crate-metadata.json",
    )
    prepared_graph = prepare_data_graph(graph)

    def is_marked(identifier: str) -> bool:
        return (
            URIRef(identifier),
            VALIDATION_CANDIDATE_PREDICATE,
            Literal(True),
        ) in prepared_graph

    assert is_marked("https://orcid.org/0009-0000-5074-6239")
    assert is_marked("https://vocab.example.org/entities/described")
    assert not is_marked("https://vocab.example.org/identifier-scheme")
    assert not is_marked("https://vocab.example.org/identifier-vocabulary")
    assert not is_marked("https://vocab.example.org/formats/uuid")
    assert not is_marked("https://vocab.example.org/profiles/property-value")
    assert not is_marked("https://vocab.example.org/properties/uuid")
    assert not is_marked("https://vocab.example.org/types/CustomEntity")
    assert not is_marked("https://vocab.example.org/property/customPredicate")


def test_invalid_preprocessing_candidates_fixture_keeps_incomplete_entities_in_scope():
    """Claimed and type-only entities remain subject to metadata checks."""
    rocrate_path = __metadata_entities__.invalid_preprocessing_candidates
    metadata = json.loads((rocrate_path / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    author_id = "https://orcid.org/0009-0000-5074-6239"

    result = _validate_metadata(rocrate_path, metadata)

    assert not result.passed()
    assert any(
        issue.violatingEntity == author_id and issue.message == "Entities SHOULD have a human-readable name"
        for issue in result.get_issues(models.Severity.RECOMMENDED)
    )
    assert any(
        issue.violatingEntity.endswith("#type-only-person")
        and issue.message == "Entities SHOULD have a human-readable name"
        for issue in result.get_issues(models.Severity.RECOMMENDED)
    )
    assert not any(issue.violatingEntity == "https://vocab.example.org/identifier-scheme" for issue in result.issues)
