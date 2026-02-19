# Copyright (c) 2026 DataPLANT
# Copyright (c) 2026 The University of Manchester
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
def test_isa_person_given_name():
    """
    Test an ISA RO-Crate where a person has no given name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:givenName "John" .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:givenName "John".
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity MUST have a non-empty given name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_given_name_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person given name has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:givenName ?name .
        }
        INSERT {
            ?person schema:givenName 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:givenName ?name .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity MUST have a non-empty given name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_family_name():
    """
    Test an ISA RO-Crate where a person has no family name.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:familyName "Doe" .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty family name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_family_name_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person family name has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:familyName "Doe" .
        }
        INSERT {
            ?person schema:familyName 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person family name MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_email():
    """
    Test an ISA RO-Crate where a person has no email.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:email "abc" .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:email "abc" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty email of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_email_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person email has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:email "abc" .
        }
        INSERT {
            ?person schema:email 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:email "abc" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person email MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_identifier():
    """
    Test an ISA RO-Crate where a person has no identifier.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:identifier ?id .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_identifier_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person identifier has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:identifier ?id .
        }
        INSERT {
            ?person schema:identifier 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person identifier MUST be of type string"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_affiliation():
    """
    Test an ISA RO-Crate where a person has no affiliation.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:affiliation ?a .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:affiliation ?a .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have at least one affiliation"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_affiliation_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person affiliation has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:affiliation ?a .
        }
        INSERT {
            ?person schema:affiliation 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:affiliation ?a .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person affiliation MUST be of type Organization"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_job_title():
    """
    Test an ISA RO-Crate where a person has no job title.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:jobTitle ?jt .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:jobTitle ?jt .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person entity SHOULD have at least one job title"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_person_job_title_of_incorrect_type():
    """
    Test an ISA RO-Crate where a person job title has wrong type.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?person schema:jobTitle ?jt .
        }
        INSERT {
            ?person schema:jobTitle 42 .
        }
        WHERE {
            ?person a schema:Person .
            ?person schema:familyName "Doe" .
            ?person schema:jobTitle ?jt .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=["Person job title MUST be of type DefinedTerm"],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
