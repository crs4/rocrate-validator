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


def test_isa_additionaltype_not_investigation():
    """
    Test an ISA RO-Crate where no Dataset has `additionalType` of "Investigation".
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:additionalType "Investigation" .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Root Data Entity must be Investigation"],
        expected_triggered_issues=[
            "The root data entity must have additionalType of `Investigation`"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_investigation_no_identifier():
    """
    Test an ISA RO-Crate where the investigation has no identifier.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:identifier ?id .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
            ?dataset schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "The root data entity must have a non-empty identifier"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_investigation_identifier_not_string():
    """
    Test an ISA RO-Crate where the investigation has an identifier that is not a string.
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
            ?dataset schema:additionalType "Investigation" .
            ?dataset schema:identifier ?id .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "The root data entity must have a non-empty identifier"
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_investigation_no_shoulds():
    """
    Test an ISA RO-Crate where the investigation is missing should properties.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:creator ?creator .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
            ?creator a schema:Person .
            ?creator schema:familyName "Doe" .
            ?dataset schema:dateCreated ?dc .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "Investigation entity SHOULD have a dateCreated",
            "Investigation entity SHOULD have a creator",
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_isa_investigation_shoulds_have_wrong_types():
    """
    Test an ISA RO-Crate where the investigation's should properties have wrong types.
    """
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:creator ?creator .
        }
        INSERT {
            ?dataset schema:dateCreated 42 .
            ?dataset schema:creator 42 .
        }
        WHERE {
            ?dataset a schema:Dataset .
            ?dataset schema:additionalType "Investigation" .
            ?dataset schema:dateCreated ?dc .
            ?dataset schema:creator ?creator .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().isa_ro_crate,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        # expected_triggered_requirements=["Investigation MUST have base properties"],
        expected_triggered_issues=[
            "Investigation dateCreated MUST be a valid ISO 8601 date",
            "Investigation creator MUST be of type Person",
        ],
        profile_identifier="isa-ro-crate",
        rocrate_entity_mod_sparql=sparql,
    )
