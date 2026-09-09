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

import logging

import pytest

from rocrate_validator.models import Severity
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import InvalidMainWorkflow, ValidROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_main_workflow_bad_type():
    """
    Test a Workflow RO-Crate where the main workflow has an incorrect type.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_bad_type,
        Severity.REQUIRED,
        False,
        ["Main Workflow definition"],
        ["The Main Workflow must have types File, SoftwareSourceCode, ComputationalWorkflow"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_no_lang():
    """
    Test a Workflow RO-Crate where the main workflow does not have a
    programmingLanguage property.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_lang,
        Severity.REQUIRED,
        False,
        ["Main Workflow definition"],
        ["The Main Workflow must refer to its language via programmingLanguage"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_no_image():
    """
    Test a Workflow RO-Crate where the main workflow does not have an
    image property.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_image,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The Crate MAY contain a Main Workflow Diagram; if present it MUST be referred to via 'image'"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_no_cwl_desc():
    """
    Test a Workflow RO-Crate where the main workflow does not have an
    CWL description.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_cwl_desc,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The Crate MAY contain a Main Workflow CWL Description; if present it MUST be referred to via 'subjectOf'"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_cwl_desc_bad_type():
    """
    Test a Workflow RO-Crate where the main workflow has a CWL description
    but of the wrong type.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_cwl_desc_bad_type,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The CWL Description type must be File, SoftwareSourceCode, HowTo"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_cwl_desc_no_lang():
    """
    Test a Workflow RO-Crate where the main workflow has a CWL description
    but the description has no programmingLanguage.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_cwl_desc_no_lang,
        Severity.OPTIONAL,
        False,
        ["Main Workflow optional properties"],
        ["The CWL Description SHOULD have a language of https://w3id.org/workflowhub/workflow-ro-crate#cwl"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_file_existence():
    """
    Test a Workflow RO-Crate where the main workflow file is not in the crate.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_files,
        Severity.REQUIRED,
        False,
        ["Main Workflow file existence"],
        ["Main Workflow", "not found in crate"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_singleton_array():
    """A singleton-array mainEntity is JSON-LD-equivalent and passes REQUIRED checks."""
    do_entity_test(
        ValidROC().workflow_roc,
        Severity.REQUIRED,
        True,
        profile_identifier="workflow-ro-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_patch={"./": {"mainEntity": [{"@id": "sort-and-change-case.ga"}]}},
    )


def test_main_workflow_singleton_array_should_be_unpacked():
    """RO-Crate 1.1 recommends unpacking a singleton array in compacted JSON-LD."""
    do_entity_test(
        ValidROC().workflow_roc,
        Severity.RECOMMENDED,
        False,
        ["Entity properties compact representation"],
        ['property "mainEntity" SHOULD be represented as a single value'],
        profile_identifier="workflow-ro-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_patch={"./": {"mainEntity": [{"@id": "sort-and-change-case.ga"}]}},
    )


def test_main_workflow_singleton_array_file_existence():
    """A missing workflow in a singleton array produces the normal validation issue."""
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_files,
        Severity.REQUIRED,
        False,
        ["Main Workflow file existence"],
        ["Main Workflow", "not found in crate"],
        profile_identifier="workflow-ro-crate",
        rocrate_entity_patch={"./": {"mainEntity": [{"@id": "sort-and-change-case.ga"}]}},
    )


@pytest.mark.parametrize(
    "main_entity",
    [
        [],
        [{"@id": "sort-and-change-case.ga"}, {"@id": "other-workflow.ga"}],
        "sort-and-change-case.ga",
        {"name": "sort-and-change-case.ga"},
        {"@id": 42},
    ],
)
def test_main_workflow_invalid_main_entity_is_reported(main_entity):
    """Malformed mainEntity values fail validation without an unexpected exception."""
    do_entity_test(
        ValidROC().workflow_roc,
        Severity.REQUIRED,
        False,
        ["Main Workflow file existence"],
        ["mainEntity"],
        profile_identifier="workflow-ro-crate",
        skip_checks=[SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER],
        rocrate_entity_patch={"./": {"mainEntity": main_entity}},
    )


def test_workflow_diagram_file_existence():
    """
    Test a Workflow RO-Crate where the workflow diagram file is not in the
    crate.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_files,
        Severity.OPTIONAL,
        False,
        ["Workflow-related files existence"],
        ["Workflow diagram", "not found in crate"],
        profile_identifier="workflow-ro-crate",
    )


def test_workflow_description_file_existence():
    """
    Test a Workflow RO-Crate where the workflow CWL description file is not in
    the crate.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_no_files,
        Severity.OPTIONAL,
        False,
        ["Workflow-related files existence"],
        ["Workflow CWL description", "not found in crate"],
        profile_identifier="workflow-ro-crate",
    )


def test_main_workflow_bad_conformsto():
    """
    Test a Workflow RO-Crate where the main workflow does not conform to the
    bioschemas computational workflow 1.0 or later.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_bad_conformsto,
        Severity.RECOMMENDED,
        False,
        ["Main Workflow recommended properties"],
        ["The Main Workflow SHOULD comply with Bioschemas ComputationalWorkflow profile version 1.0 or later"],
        profile_identifier="workflow-ro-crate",
    )
