# Copyright (c) 2024-2025 CRS4
# Copyright (c) 2025-2026 eScience Lab, The University of Manchester
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


def test_5src_download_action_does_not_have_name():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?this schema:name ?name .
        }
        WHERE {
            ?this schema:name ?name ;
                  rdf:type schema:DownloadAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "DownloadAction MUST have a human readable name string."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_name_not_a_string():
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
            ?this rdf:type schema:DownloadAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "DownloadAction MUST have a human readable name string."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_start_time_not_iso_standard():
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
            ?c rdf:type schema:DownloadAction ;
             schema:startTime ?t .
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


def test_5src_check_value_end_time_not_iso_standard():
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
            ?c rdf:type schema:DownloadAction ;
               schema:endTime ?t .
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


def test_5src_downloaded_workflow_same_as_is_not_the_same_as_root_data_entity_main_entity():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?wf schema:sameAs ?me .
        }
        INSERT {
            ?wf schema:sameAs "This is not the same as the main entity" .
        }
        WHERE {
            ?wf schema:sameAs ?me .
            <./> schema:mainEntity ?me .
            ?da schema:result ?wf ;
               rdf:type schema:DownloadAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Downloaded Workflow"],
        expected_triggered_issues=[
            (
                "The property `sameAs` of the entity representing the downloaded workflow "
                "MUST point to the same entity as `RootDataEntity` --> `mainEntity`."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_downloaded_workflow_distribution_is_not_the_same_as_download_action_object():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:object ?o .
        }
        INSERT {
            ?s schema:result "This is not the downloaded workflow entity" .
        }
        WHERE {
            ?s schema:object ?o ;
               rdf:type schema:DownloadAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["Downloaded Workflow"],
        expected_triggered_issues=[
            (
                "DownloadedWorkflow --> `distribution` MUST reference "
                "the same entity as `DownloadAction` --> `object`."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_has_action_status_with_not_allowed_value():
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
            ?s rdf:type schema:DownloadAction ;
               schema:actionStatus ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            (
                "The value of actionStatus MUST be one of the allowed values: "
                "PotentialActionStatus; ActiveActionStatus; CompletedActionStatus; FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_5src_download_action_is_not_present():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?da ?p ?o .
        }
        WHERE {
            ?da rdf:type schema:DownloadAction ;
                ?p ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=["An entity typed DownloadAction SHOULD exist."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_root_data_entity_does_not_mention_download_action_entity():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o rdf:type schema:DownloadAction ;
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "RootDataEntity SHOULD mention DownloadAction if this exists."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_end_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?c schema:endTime ?t .
        }
        WHERE {
            ?c rdf:type schema:DownloadAction ;
             schema:endTime ?t .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            (
                "`DownloadAction` SHOULD have the `endTime` property "
                "if `actionStatus` is either CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_action_status_property():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        WHERE {
            ?s rdf:type schema:DownloadAction ;
               schema:actionStatus ?o .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "`DownloadAction` SHOULD have `actionStatus` property."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- MAY fails tests


def test_5src_downloaded_workflow_is_not_represented_by_its_own_entity():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?wf ?p ?o .
        }
        WHERE {
            ?wf ?p ?o .
            ?da schema:result ?wf ;
               rdf:type schema:DownloadAction .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            (
                "The entity representing the downloaded workflow is not defined, "
                "OR is not referenced by `DownloadAction` --> `result`, "
                "OR is not of type `Dataset`."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_start_time():
    sparql = (
        SPARQL_PREFIXES
        + """
        DELETE {
            ?s schema:startTime ?time .
        }
        WHERE {
            ?s rdf:type schema:DownloadAction ;
               schema:startTime ?time .
        }
        """
    )

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            (
                "`DownloadAction` MAY have the `startTime` property if `actionStatus` "
                "is either ActiveActionStatus, CompletedActionStatus or FailedActionStatus."
            )
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
