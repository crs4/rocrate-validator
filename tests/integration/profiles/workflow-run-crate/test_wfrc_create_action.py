# Copyright (c) 2024-2026 CRS4
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

import pytest

from rocrate_validator.models import Severity
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

EXPECTED_ISSUE = "At least one CreateAction, ActivateAction or UpdateAction MUST reference the root data entity's mainEntity as its instrument."


def test_wfrc_no_supported_action_with_main_entity_as_instrument():
    """Supported actions referencing another tool cannot satisfy the execution check."""
    do_entity_test(
        ValidROC().workflow_run_crate,
        Severity.REQUIRED,
        False,
        expected_triggered_issues=[EXPECTED_ISSUE],
        profile_identifier="workflow-run-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_mod_sparql="""
            PREFIX schema: <http://schema.org/>
            DELETE { ?action schema:instrument ?workflow . }
            INSERT {
                ?action schema:instrument <https://example.org/other-tool> .
                <https://example.org/other-tool> a schema:SoftwareApplication ;
                    schema:name "Another tool" .
            }
            WHERE {
                ?root schema:mainEntity ?workflow .
                ?metadata schema:about ?root .
                FILTER(
                    STRENDS(STR(?metadata), "ro-crate-metadata.json") ||
                    STRENDS(STR(?metadata), "ro-crate-metadata.jsonld")
                )
                VALUES ?actionType { schema:CreateAction schema:ActivateAction schema:UpdateAction }
                ?action a ?actionType ;
                    schema:instrument ?workflow .
            }
        """,
    )


@pytest.mark.parametrize("action_type", ["CreateAction", "ActivateAction", "UpdateAction"])
def test_wfrc_no_action_with_main_entity_as_instrument(action_type):
    """A valid instrument pointing to another tool cannot satisfy main entity execution."""
    do_entity_test(
        ValidROC().workflow_run_crate,
        Severity.REQUIRED,
        False,
        expected_triggered_issues=[EXPECTED_ISSUE],
        profile_identifier="workflow-run-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_mod_sparql=f"""
            PREFIX schema: <http://schema.org/>
            DELETE {{ ?action a ?originalType . }}
            INSERT {{ ?action a schema:{action_type} . }}
            WHERE {{
                VALUES ?originalType {{ schema:CreateAction schema:ActivateAction schema:UpdateAction }}
                ?action a ?originalType .
            }} ;

            PREFIX schema: <http://schema.org/>
            DELETE {{ ?action schema:instrument ?workflow . }}
            INSERT {{
                ?action schema:instrument <https://example.org/other-tool> .
                <https://example.org/other-tool> a schema:SoftwareApplication ;
                    schema:name "Another tool" .
            }}
            WHERE {{
                ?root schema:mainEntity ?workflow .
                ?metadata schema:about ?root .
                FILTER(
                    STRENDS(STR(?metadata), "ro-crate-metadata.json") ||
                    STRENDS(STR(?metadata), "ro-crate-metadata.jsonld")
                )
                ?action a schema:{action_type} ;
                    schema:instrument ?workflow .
            }}
        """,
    )
