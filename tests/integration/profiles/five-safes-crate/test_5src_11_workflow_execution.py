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
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


# ----- MUST fails tests


def test_5src_workflow_object_with_no_name():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?this schema:name ?name .
        }
        WHERE {
            ?this rdf:type schema:CreateAction ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_name_not_string():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name 123 .
        }
        WHERE {
            ?this rdf:type schema:CreateAction ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_not_long_enough_name():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?this schema:name ?name .
        }
        INSERT {
            ?this schema:name "Too short" .
        }
        WHERE {
            ?this rdf:type schema:CreateAction ;
                  schema:name ?name .
            <./> schema:mentions ?this .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_start_time_if_begun():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?s schema:startTime ?o .
        }
        WHERE {
            ?s rdf:type schema:CreateAction;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus",
                    "http://schema.org/ActiveActionStatus"
                ))
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_properly_formatted_start_time_if_begun():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?s schema:startTime ?o .
        }
        INSERT {
            ?s schema:startTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus",
                    "http://schema.org/ActiveActionStatus"
                ))
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_end_time_if_ended():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX shp:    <https://w3id.org/shp#>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?s schema:endTime ?o .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus"
                ))
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_properly_formatted_end_time_if_ended():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?s schema:endTime ?o .
        }
        INSERT {
            ?s schema:endTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:actionStatus ?status .
               FILTER(?status IN (
                    "http://schema.org/CompletedActionStatus",
                    "http://schema.org/FailedActionStatus"
                ))
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_no_action_status():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?this schema:actionStatus ?o .
        }
        WHERE {
            ?this schema:actionStatus ?o ;
                  rdf:type schema:CreateAction .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_no_properly_valued_action_status():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            ?this schema:actionStatus ?o .
        }
        INSERT {
            ?this schema:actionStatus "Not a proper actionStatus value" .
        }
        WHERE {
            ?this schema:actionStatus ?o ;
                  rdf:type schema:CreateAction .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_5src_workflow_object_not_mentioned_by_root_data_entity():
    sparql = """
        PREFIX schema: <http://schema.org/>
        PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o rdf:type schema:CreateAction .
        }
        """

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_request,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=None,
        expected_triggered_issues=None,
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
