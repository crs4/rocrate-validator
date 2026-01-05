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


def test_5src_disclosure_object_with_no_name():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?this schema:name ?name .
        }
        WHERE {
            ?this schema:additionalType shp:DisclosureCheck ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            "`DisclosureCheck` MUST have a name string of at least 10 characters."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_with_name_not_string():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name 123 .
        }
        WHERE {
            ?this schema:additionalType shp:DisclosureCheck ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            "`DisclosureCheck` MUST have a name string of at least 10 characters."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_with_not_long_enough_name():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name "Short" .
        }
        WHERE {
            ?this schema:additionalType shp:DisclosureCheck ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            "`DisclosureCheck` MUST have a name string of at least 10 characters."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_not_an_assess_action():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?this rdf:type schema:AssessAction .
        }
        INSERT {
            ?this rdf:type "Not an AssessAction type" .
        }
        WHERE {
            ?this rdf:type schema:AssessAction ;
                  schema:additionalType shp:DisclosureCheck .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            "`DisclosureCheck` MUST be a `schema:AssessAction`."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_with_no_proper_action_status():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        INSERT {
            ?s schema:actionStatus "This is not a proper actionStatus" .
        }
        WHERE {
            ?s schema:actionStatus ?o ;
               schema:additionalType shp:DisclosureCheck .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            (
                "`DisclosureCheck` MUST have an actionStatus with an allowed value "
                "(see https://schema.org/ActionStatusType)."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_has_no_properly_formatted_start_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:startTime ?time .
        }
        INSERT {
            ?s schema:startTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s schema:additionalType shp:DisclosureCheck ;
               schema:startTime ?time .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Timestamp Format"],
        expected_triggered_issues=[
            (
                "All `startTime` and `endTime` values MUST follow the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_has_no_properly_formatted_end_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:endTime ?time .
        }
        INSERT {
            ?s schema:endTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s schema:additionalType shp:DisclosureCheck ;
               schema:endTime ?time .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Timestamp Format"],
        expected_triggered_issues=[
            (
                "All `startTime` and `endTime` values MUST follow the RFC 3339 standard "
                "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_5src_disclosure_object_not_mentioned_by_root_data_entity():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o schema:additionalType shp:DisclosureCheck .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "`RootDataEntity` SHOULD mention a disclosure object."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_with_no_action_status():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        WHERE {
            ?s schema:additionalType shp:DisclosureCheck ;
               schema:actionStatus ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            "The `DisclosureCheck` SHOULD have `actionStatus` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_disclosure_object_has_no_end_time_if_ended():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:endTime ?o .
        }
        WHERE {
            ?s schema:additionalType shp:DisclosureCheck ;
               schema:endTime ?o ;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus"
                ))
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            (
                "`DisclosureCheck` SHOULD have the `endTime` property if `actionStatus` "
                "is either CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- MAY fails tests


def test_5src_disclosure_object_has_no_start_time_if_begun():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:startTime ?o .
        }
        WHERE {
            ?s schema:additionalType shp:DisclosureCheck ;
               schema:startTime ?o ;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus",
                    "http://schema.org/ActiveActionStatus"
                ))
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["DisclosureCheck"],
        expected_triggered_issues=[
            (
                "`DisclosureCheck` MAY have the `startTime` property if `actionStatus` "
                "is either ActiveActionStatus, CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
