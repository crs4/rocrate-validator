# Copyright (c) 2024 DataPLANT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC, InvalidISARC
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity MUST have a non-empty given name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity MUST have a non-empty given name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty family name of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person family name MUST be of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty email of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person email MUST be of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have a non-empty identifier of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person identifier MUST be of type string"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have at least one affiliation"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person affiliation MUST be of type Organization"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person entity SHOULD have at least one job title"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
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
        rocrate_path=ValidROC().isa_ro_crate_manual,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Study MUST have base properties"],
        expected_triggered_issues=[
            "Person job title MUST be of type DefinedTerm"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql
    )