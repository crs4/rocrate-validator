# Copyright (c) 2024 CRS4
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
from tests.ro_crates import InvalidWfRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_formalparam_no_inv_exampleofwork():
    """\
    Test a Workflow Run Crate where a FormalParameter is not referenced via
    exampleOfWork.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_inv_exampleofwork,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter SHOULD"],
        ["FormalParameter SHOULD be referenced from a data entity or PropertyValue via exampleOfWork"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_bad_inv_exampleofwork():
    """\
    Test a Workflow Run Crate where a FormalParameter is referenced via
    exampleOfWork by an entity that is not a data entity or PropertyValue.
    """
    do_entity_test(
        InvalidWfRC().formalparam_bad_inv_exampleofwork,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter SHOULD"],
        ["FormalParameter SHOULD be referenced from a data entity or PropertyValue via exampleOfWork"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_no_workexample():
    """\
    Test a Workflow Run Crate where a FormalParameter does not have a
    workExample property.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_workexample,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate FormalParameter MAY"],
        ["FormalParameter MAY have a workExample"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_bad_workexample():
    """\
    Test a Workflow Run Crate where a FormalParameter references via
    workExample an entity that is not a data entity or PropertyValue.
    """
    do_entity_test(
        InvalidWfRC().formalparam_bad_workexample,
        Severity.REQUIRED,
        False,
        ["Workflow Run Crate FormalParameter MUST"],
        ["FormalParameter MUST refer to a data entity or PropertyValue via workExample"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_no_additionaltype():
    """\
    Test a Workflow Run Crate where a FormalParameter does not have an
    additionalType.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_additionaltype,
        Severity.REQUIRED,
        False,
        ["Workflow Run Crate FormalParameter MUST"],
        ["FormalParameter MUST have an additionalType"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_maps_pv_bad_additionaltype():
    """\
    Test a Workflow Run Crate where a FormalParameter that maps to a
    PropertyValue does not have PropertyValue or a subclass of DataType as its
    additionalType.
    """
    do_entity_test(
        InvalidWfRC().formalparam_maps_pv_bad_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter that maps to a PropertyValue"],
        ["A FormalParameter that maps to a PropertyValue SHOULD have "
         "PropertyValue or a subclass of DataType as its additionalType"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_maps_file_bad_additionaltype():
    """\
    Test a Workflow Run Crate where a FormalParameter that maps to a File does
    not have File as its additionalType.
    """
    do_entity_test(
        InvalidWfRC().formalparam_maps_file_bad_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter that maps to a File"],
        ["A FormalParameter that maps to a File SHOULD have File as its additionalType"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_maps_dataset_bad_additionaltype():
    """\
    Test a Workflow Run Crate where a FormalParameter that maps to a Dataset
    does not have Dataset as its additionalType.
    """
    do_entity_test(
        InvalidWfRC().formalparam_maps_dataset_bad_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter that maps to a Dataset"],
        ["A FormalParameter that maps to a Dataset SHOULD have Dataset as its additionalType"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_maps_collection_bad_additionaltype():
    """\
    Test a Workflow Run Crate where a FormalParameter that maps to a Collection
    does not have Collection as its additionalType.
    """
    do_entity_test(
        InvalidWfRC().formalparam_maps_collection_bad_additionaltype,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter that maps to a Collection"],
        ["A FormalParameter that maps to a Collection SHOULD have Collection as its additionalType"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_no_name():
    """\
    Test a Workflow Run Crate where a FormalParameter does not have a
    name property.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_name,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter SHOULD"],
        ["FormalParameter SHOULD have a name"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_no_description():
    """\
    Test a Workflow Run Crate where a FormalParameter does not have a
    description property.
    """
    do_entity_test(
        InvalidWfRC().formalparam_no_description,
        Severity.OPTIONAL,
        False,
        ["Workflow Run Crate FormalParameter MAY"],
        ["FormalParameter MAY have a description"],
        profile_identifier="workflow-run-crate"
    )


def test_formalparam_env_bad_exampleofwork():
    """\
    Test a Workflow Run Crate where a FormalParameter referenced from a
    ComputationalWorkflow via environment is not referenced from a
    PropertyValue via exampleOfWork
    """
    do_entity_test(
        InvalidWfRC().formalparam_env_bad_exampleofwork,
        Severity.RECOMMENDED,
        False,
        ["Workflow Run Crate FormalParameter referenced from a ComputationalWorkflow environment"],
        ["A FormalParameter referenced from a ComputationalWorkflow via "
         "environment SHOULD be referenced from a PropertyValue via exampleOfWork"],
        profile_identifier="workflow-run-crate"
    )
