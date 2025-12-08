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

def test_5src_download_action_does_not_have_name():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?this schema:name ?name .
        }
        WHERE {
            ?this schema:name ?name ;
                  rdf:type schema:DownloadAction .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "DownloadAction MUST have a human readable name string of at least 10 characters."
            ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_name_not_a_string():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name 123 .
        }
        WHERE {
            ?this rdf:type schema:DownloadAction .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "DownloadAction MUST have a human readable name string of at least 10 characters."
            ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_name_not_long_enough():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name "Short" .
        }
        WHERE {
            ?this rdf:type schema:DownloadAction .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "DownloadAction MUST have a human readable name string of at least 10 characters."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_start_time_not_iso_standard():
    sparql = (SPARQL_PREFIXES + """
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
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[(
            "`DownloadAction` --> `startTime` MUST follows the RFC 3339 standard "
            "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
        )],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_check_value_end_time_not_iso_standard():
    sparql = (SPARQL_PREFIXES + """
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
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[(
            "`DownloadAction` --> `endTime` MUST follows the RFC 3339 standard "
            "(YYYY-MM-DD'T'hh:mm:ss[.fraction](Z | ±hh:mm))."
        )],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_has_action_status_with_not_allowed_value():
    sparql = (SPARQL_PREFIXES + """
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
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[(
            "`DownloadAction` --> `actionStatus` MUST have one of the allowed values "
            "(see https://schema.org/ActionStatusType)."
        )],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests

def test_5src_root_data_entity_does_not_mention_download_action_entity():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o rdf:type schema:DownloadAction ;
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "RootDataEntity SHOULD mention the DownloadAction object."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_end_time():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?c schema:endTime ?t .
        }
        WHERE {
            ?c rdf:type schema:DownloadAction ;
             schema:endTime ?t .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "`DownloadAction` SHOULD have the `endTime` property if it has ended."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_download_action_does_not_have_action_status_property():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:actionStatus ?o .
        }
        WHERE {
            ?s rdf:type schema:DownloadAction ;
               schema:actionStatus ?o .
        }
        """)

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

def test_5src_download_action_does_not_have_start_time():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?c schema:startTime ?t .
        }
        WHERE {
            ?c rdf:type schema:DownloadAction ;
               schema:startTime ?t .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["DownloadAction"],
        expected_triggered_issues=[
            "`DownloadAction` MAY have the `startTime` property if it has begun."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
