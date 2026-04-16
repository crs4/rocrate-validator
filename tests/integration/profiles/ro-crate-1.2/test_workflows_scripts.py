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

from rocrate_validator import models
from tests.ro_crates_1_2 import WorkflowsScripts
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)

__workflows_scripts_crates__ = WorkflowsScripts()

# General RECOMMENDED checks that fire on minimal test crates regardless of the
# workflow/script-specific property being tested.  These are skipped in the
# "valid" RECOMMENDED test cases so the assertion is only about the
# workflow-specific shape.
_GENERIC_RECOMMENDED_SKIP = [
    "ro-crate-1.2_40.0",   # RO-Crate Metadata Entity: RECOMMENDED properties (check 0)
    "ro-crate-1.2_40.1",   # RO-Crate Metadata Entity: RECOMMENDED properties (check 1)
    "ro-crate-1.2_47.1",   # Root Data Entity: recommended funder
    "ro-crate-1.2_54.1",   # Root Data Entity: recommended publisher
    "ro-crate-1.2_61.1",   # File Data Entity: RECOMMENDED contentSize
    "ro-crate-1.2_62.0",   # File: RECOMMENDED conformsTo profile
    "ro-crate-1.2_70.1",   # Contextual Entity Properties
    "ro-crate-1.2_71.1",   # Contextual Entity RECOMMENDED description
    "ro-crate-1.2_76.2",   # License entity: RECOMMENDED properties
]


# ---------------------------------------------------------------------------
# Script type checks (MUST)
# ---------------------------------------------------------------------------

def test_valid_script_type():
    """
    A Script entity with `File`, `SoftwareSourceCode` in @type and a `name`
    MUST pass REQUIRED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_script_type,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_script_type():
    """
    A Script entity missing `File` (schema:MediaObject) in its @type
    MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_script_type,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script: REQUIRED `File` type"],
        expected_triggered_issues=[
            "A Script MUST include `File` in its `@type`"
        ],
    )


# ---------------------------------------------------------------------------
# Script name checks (MUST)
# ---------------------------------------------------------------------------

def test_valid_script_name():
    """
    A Script entity with a `name` property MUST pass REQUIRED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_script_name,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_script_name():
    """
    A Script entity missing the `name` property MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_script_name,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script or Workflow: REQUIRED `name`"],
        expected_triggered_issues=[
            "Scripts and Workflows MUST have a human-readable `name` property"
        ],
    )


# ---------------------------------------------------------------------------
# Workflow type checks (MUST)
# ---------------------------------------------------------------------------

def test_valid_workflow_type():
    """
    A Workflow entity with `File`, `SoftwareSourceCode`, `ComputationalWorkflow`
    in @type and all required properties MUST pass REQUIRED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_workflow_type,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_workflow_type_missing_file():
    """
    A Workflow entity missing `File` (schema:MediaObject) in its @type
    MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_workflow_type_missing_file,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Workflow: REQUIRED `File` type"],
        expected_triggered_issues=[
            "A Workflow MUST include `File` in its `@type`"
        ],
    )


def test_invalid_workflow_type_missing_ssc():
    """
    A Workflow entity missing `SoftwareSourceCode` in its @type
    MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_workflow_type_missing_ssc,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Workflow: REQUIRED `SoftwareSourceCode` type"],
        expected_triggered_issues=[
            "A Workflow MUST include `SoftwareSourceCode` in its `@type`"
        ],
    )


# ---------------------------------------------------------------------------
# Workflow name checks (MUST)
# ---------------------------------------------------------------------------

def test_valid_workflow_name():
    """
    A Workflow entity with a `name` property MUST pass REQUIRED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_workflow_name,
        models.Severity.REQUIRED,
        True,
        profile_identifier="ro-crate-1.2",
    )


def test_invalid_workflow_name():
    """
    A Workflow entity missing the `name` property MUST trigger a REQUIRED violation.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_workflow_name,
        models.Severity.REQUIRED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script or Workflow: REQUIRED `name`"],
        expected_triggered_issues=[
            "Scripts and Workflows MUST have a human-readable `name` property"
        ],
    )


# ---------------------------------------------------------------------------
# programmingLanguage checks (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_programming_language():
    """
    A Script/Workflow with a `programmingLanguage` referencing a
    `ComputerLanguage` entity SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_programming_language,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_programming_language():
    """
    A Script/Workflow missing a `programmingLanguage` property
    SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_programming_language,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script or Workflow: RECOMMENDED `programmingLanguage`"],
        expected_triggered_issues=[
            "Scripts and Workflows SHOULD have a `programmingLanguage` property"
        ],
    )


# ---------------------------------------------------------------------------
# Workflow conformsTo checks (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_workflow_conformsTo():
    """
    A Workflow with `conformsTo` pointing to a versioned Bioschemas profile URI
    SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_workflow_conformsTo,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_workflow_conformsTo():
    """
    A Workflow missing `conformsTo` SHOULD trigger a RECOMMENDED warning.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_workflow_conformsTo,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Workflow: RECOMMENDED Bioschemas `conformsTo`"],
        expected_triggered_issues=[
            "Workflows SHOULD declare `conformsTo` referencing a versioned Bioschemas ComputationalWorkflow profile URI"
        ],
    )


# ---------------------------------------------------------------------------
# Image encodingFormat checks (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_image_encoding_format():
    """
    A Workflow image ImageObject with `encodingFormat` SHOULD pass
    RECOMMENDED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_image_encoding_format,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_image_encoding_format():
    """
    A Workflow image ImageObject missing `encodingFormat` SHOULD trigger
    a RECOMMENDED warning.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_image_encoding_format,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script/Workflow ImageObject: RECOMMENDED `encodingFormat`"],
        expected_triggered_issues=[
            "An ImageObject referenced via `image` from a Script or Workflow SHOULD have an `encodingFormat` property"
        ],
    )


# ---------------------------------------------------------------------------
# Image about checks (SHOULD)
# ---------------------------------------------------------------------------

def test_valid_image_about():
    """
    A Workflow image ImageObject with `about` referencing the workflow
    SHOULD pass RECOMMENDED validation.
    """
    do_entity_test(
        __workflows_scripts_crates__.valid_image_about,
        models.Severity.RECOMMENDED,
        True,
        profile_identifier="ro-crate-1.2",
        skip_checks=_GENERIC_RECOMMENDED_SKIP,
    )


def test_invalid_image_about():
    """
    A Workflow image ImageObject missing `about` SHOULD trigger a
    RECOMMENDED warning.
    """
    do_entity_test(
        __workflows_scripts_crates__.invalid_image_about,
        models.Severity.RECOMMENDED,
        False,
        profile_identifier="ro-crate-1.2",
        expected_triggered_requirements=["Script/Workflow ImageObject: RECOMMENDED `about` reference"],
        expected_triggered_issues=[
            "An ImageObject referenced via `image` from a Script or Workflow SHOULD have an `about` property referencing the script or workflow"
        ],
    )
