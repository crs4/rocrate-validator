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


def test_5src_workflow_object_with_no_name():

    sparql = (
        SPARQL_PREFIXES + """
        DELETE {
            ?this schema:name ?name .
        }
        WHERE {
            ?this rdf:type schema:CreateAction ;
                    schema:name ?name .
            <./> schema:mentions ?this .
        }
    """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=["Workflow (CreateAction) MUST have a name string of at least 20 characters."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_name_not_string():
    sparql = (SPARQL_PREFIXES + """
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
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=["Workflow (CreateAction) MUST have a name string of at least 20 characters."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_not_long_enough_name():
    sparql = (SPARQL_PREFIXES + """
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
    """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=["Workflow (CreateAction) MUST have a name string of at least 20 characters."],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_properly_formatted_start_time():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:startTime ?time .
        }
        INSERT {
            ?s schema:startTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:startTime ?time .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[
            "The startTime of the workflow execution object MUST follow the RFC 3339 standard."
            ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_properly_formatted_end_time():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:endTime ?time .
        }
        INSERT {
            ?s schema:endTime "1st Dec '25 @ 10:00:00" .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:endTime ?time .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[
            "The endTime of the workflow execution object MUST follow the RFC 3339 standard."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_no_action_status():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?this schema:actionStatus ?o .
        }
        WHERE {
            ?this schema:actionStatus ?o ;
                  rdf:type schema:CreateAction .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[(
            "WorkflowExecution MUST have an actionStatus "
            "with an allowed value (see https://schema.org/ActionStatusType)."
        )],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_with_no_properly_valued_action_status():
    sparql = (SPARQL_PREFIXES + """
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
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.REQUIRED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[(
            "WorkflowExecution MUST have an actionStatus "
            "with an allowed value (see https://schema.org/ActionStatusType)."
        )],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ----- SHOULD fails tests


def test_5src_workflow_object_not_mentioned_by_root_data_entity():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            <./> schema:mentions ?o .
        }
        WHERE {
            ?o rdf:type schema:CreateAction .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["RootDataEntity"],
        expected_triggered_issues=[
            "RootDataEntity SHOULD mention workflow execution object (typed CreateAction)."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


def test_5src_workflow_object_has_no_end_time_if_ended():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:endTime ?time .
        }
        WHERE {
            ?s rdf:type schema:CreateAction ;
               schema:endTime ?time .
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.RECOMMENDED,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[
            "The workflow execution object SHOULD have an endTime property if it has ended."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )


# ------- MAY fail tests


def test_5src_workflow_object_has_no_start_time_if_begun():
    sparql = (SPARQL_PREFIXES + """
        DELETE {
            ?s schema:startTime ?time .
        }
        WHERE {
            ?s rdf:type schema:CreateAction;
               schema:startTime ?time
        }
        """)

    do_entity_test(
        rocrate_path=ValidROC().five_safes_crate_result,
        requirement_severity=Severity.OPTIONAL,
        expected_validation_result=False,
        expected_triggered_requirements=["WorkflowExecution"],
        expected_triggered_issues=[
            "The workflow execution object MAY have a startTime if execution was initiated."
        ],
        profile_identifier="five-safes-crate",
        rocrate_entity_mod_sparql=sparql,
    )
