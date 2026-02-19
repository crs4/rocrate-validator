# Copyright (c) 2026 DataPLANT
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

import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test, SPARQL_PREFIXES

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests


# WIP update these tests to actually do what the name/description say
def test_isa_study_no_identifier():
    """
    Test an ISA RO-Crate where a Study has no identifier.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:identifier ?id .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_identifier_not_string():
    """
    Test an ISA RO-Crate where a Study has an identifier that is not a string.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:identifier ?id .
        }
        INSERT {
            ?dataset schema:identifier 42 .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_name():
    """
    Test an ISA RO-Crate where a Study does not have a name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:name ?name .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:name ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_name_not_string():
    """
    Test an ISA RO-Crate where a Study has a name that is not a string.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:name ?id .
        }
        INSERT {
            ?dataset schema:name 42 .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity MUST have a non-empty name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_correctly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Study is referenced from the Investigation/Root Data Entity with wrong property.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset1 schema:hasPart ?dataset2 .
        }
        INSERT {
            ?dataset1 schema:mentions ?dataset2 .
        }
        WHERE {
            ?dataset1 a schema:Dataset .
            ?dataset2 a schema:Dataset .
            ?dataset2 schema:additionalType "Study" .
            ?dataset1 schema:hasPart ?dataset2 .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=[
            "Study MUST be directly referenced from Investigation (Root Data Entity)"
        ],
        expected_triggered_issues=[
            "Study MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_directly_referenced_from_investigation():
    """
    Test an ISA RO-Crate where a Study is not directly referenced from the Investigation/Root Data Entity.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset1 schema:hasPart ?dataset2 .
        }
        WHERE {
            ?dataset1 a schema:Dataset .
            ?dataset2 a schema:Dataset .
            ?dataset1 schema:additionalType "Investigation" .
            ?dataset2 schema:additionalType "Study" .
            ?dataset1 schema:hasPart ?dataset2 .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Study MUST be directly referenced from Investigation (Root Data Entity)"],
        expected_triggered_issues=[
            "Study MUST be directly referenced in hasPart on the Investigation (Root Data Entity)"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_no_shoulds():
    """
    Test an ISA RO-Crate where the study is missing should properties.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:datePublished ?dp .
            ?dataset schema:creator ?creator .
            ?dataset schema:hasPart ?hasPart .
            ?dataset schema:about ?about .
            ?dataset schema:description ?description .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:datePublished ?dp .
            ?dataset schema:creator ?creator .
            ?dataset schema:hasPart ?hasPart .
            ?dataset schema:about ?about .
            ?dataset schema:description ?description .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study entity SHOULD have a dateCreated",
            "Study entity SHOULD have a datePublished",
            "Study entity SHOULD have a creator",
            "Study entity SHOULD have hasPart",
            "Study entity SHOULD have about",
            "Study entity SHOULD have a non-empty description of type string",
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_study_shoulds_have_wrong_types():
    """
    Test an ISA RO-Crate where the study has should properties with wrong types.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:datePublished ?dp .
            ?dataset schema:creator ?creator .
            ?dataset schema:hasPart ?hasPart .
            ?dataset schema:about ?about .
            ?dataset schema:description ?description .
        }
        INSERT {
            ?dataset schema:dateCreated 42 .
            ?dataset schema:datePublished 42 .
            ?dataset schema:creator 42 .
            ?dataset schema:hasPart 42 .
            ?dataset schema:about 42 .
            ?dataset schema:description 42 .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Study" .
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:datePublished ?dp .
            ?dataset schema:creator ?creator .
            ?dataset schema:hasPart ?hasPart .
            ?dataset schema:about ?about .
            ?dataset schema:description ?description .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Study dateCreated MUST be a valid date literal",
            "Study datePublished MUST be a valid date literal",
            "Study creator MUST be of type Person",
            "Study hasPart MUST be of type Dataset or File",
            "Study about MUST be of type LabProcess",
            "Study description MUST be of type string",
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
