# Copyright (c) 2024-2025 CRS4
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

# TO BE CHECKED AGAIN
def test_5src_validation_check_not_of_type_assess_action():
    sparql = (
        SPARQL_PREFIXES + """
        DELETE {
            ?this rdf:type schema:AssessAction .
        }
        INSERT {
            ?this rdf:type <something_wrong> .
        }
        WHERE {
            ?this rdf:type schema:AssessAction ;
                  schema:additionalType shp:ValidationCheck .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=["ValidationCheck MUST be a `schema:AssessAction`."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_name_not_a_string():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name 123 .
        }
        WHERE {
            ?this schema:additionalType shp:ValidationCheck .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=["ValidationCheck MUST have a human readable name string."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_has_action_status_with_not_allowed_value():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        INSERT {
            ?s schema:actionStatus "Not a good action status" .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
               schema:actionStatus ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            (
                "The value of actionStatus MUST be one of the allowed "
                "values: PotentialActionStatus; ActiveActionStatus; CompletedActionStatus; FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_start_time_not_iso_standard():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?c schema:startTime ?t .
        }
        INSERT {
            ?c schema:startTime "1st of Jan 2021" .
        }
        WHERE {
            ?c schema:additionalType shp:ValidationCheck ;
               schema:startTime ?t .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            (
                "ValidationCheck --> `startTime` MUST follows the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_end_time_not_iso_standard():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?c schema:endTime ?t .
        }
        INSERT {
            ?c schema:endTime "1st of Jan 2021" .
        }
        WHERE {
            ?c schema:additionalType shp:ValidationCheck ;
               schema:endTime ?t .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            (
                "ValidationCheck --> `endTime` MUST follows the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests

def test_5src_root_data_entity_does_not_mention_validation_check_entity():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o schema:additionalType shp:ValidationCheck ;
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=["RootDataEntity SHOULD mention a ValidationCheck object."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_object_does_not_point_to_root_data_entity():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:object <./> .
        }
        INSERT {
            ?s schema:object "not the RootDataEntity" .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=["`ValidationCheck` --> `object` SHOULD point to the root of the RO-Crate"],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_validation_check_instrument_does_not_point_to_5scrate_0p4():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:instrument <https://w3id.org/5s-crate/0.4> .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
                schema:instrument <https://w3id.org/5s-crate/0.4> .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            "`ValidationCheck` --> `instrument` SHOULD point to an entity with @id https://w3id.org/5s-crate/0.4"
            ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_Validation_check_does_not_have_action_status_property():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
               schema:actionStatus ?o .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=["ValidationCheck SHOULD have actionStatus property."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_end_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:endTime ?time .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
               schema:endTime ?time .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            (
                "ValidationCheck SHOULD have the `endTime` property if `actionStatus` "
                "is either CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- MAY fails tests

def test_5src_download_action_does_not_have_start_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:startTime ?time .
        }
        WHERE {
            ?s schema:additionalType shp:ValidationCheck ;
               schema:startTime ?time .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["ValidationCheck"],
        expected_triggered_issues=[
            (
                "ValidationCheck MAY have the `startTime` property if `actionStatus` "
                "is either ActiveActionStatus, CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
