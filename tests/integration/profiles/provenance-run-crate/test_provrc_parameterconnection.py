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
from tests.ro_crates import InvalidProvRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_parameterconnection_no_sourceparameter():
    """\
    Test a Provenance Run Crate where a ParameterConnection does not have a
    SourceParameter.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_no_sourceparameter,
        Severity.REQUIRED,
        False,
        ["ProvRC ParameterConnection MUST"],
        ["ParameterConnection must have a sourceParameter that references a FormalParameter"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_bad_sourceparameter():
    """\
    Test a Provenance Run Crate where a ParameterConnection has a
    SourceParameter that does not reference a FormalParameter.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_bad_sourceparameter,
        Severity.REQUIRED,
        False,
        ["ProvRC ParameterConnection MUST"],
        ["ParameterConnection must have a sourceParameter that references a FormalParameter"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_no_targetparameter():
    """\
    Test a Provenance Run Crate where a ParameterConnection does not have a
    TargetParameter.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_no_targetparameter,
        Severity.REQUIRED,
        False,
        ["ProvRC ParameterConnection MUST"],
        ["ParameterConnection must have a targetParameter that references a FormalParameter"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_bad_targetparameter():
    """\
    Test a Provenance Run Crate where a ParameterConnection has a
    TargetParameter that does not reference a FormalParameter.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_bad_targetparameter,
        Severity.REQUIRED,
        False,
        ["ProvRC ParameterConnection MUST"],
        ["ParameterConnection must have a targetParameter that references a FormalParameter"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_not_referenced():
    """\
    Test a Provenance Run Crate where a ParameterConnection is not referenced
    by any other entity through the connection property.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_not_referenced,
        Severity.RECOMMENDED,
        False,
        ["ParameterConnection references"],
        ["Missing `connection` to this `ParameterConnection` entity"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_not_workflow_referenced():
    """\
    Test a Provenance Run Crate where a ParameterConnection is not referenced
    by any Workflow through the connection property.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_not_workflow_referenced,
        Severity.RECOMMENDED,
        False,
        ["ParameterConnection references on computational workflows"],
        ["Missing `ComputationalWorkflow` connection to this `ParameterConnection` entity"],
        profile_identifier="provenance-run-crate"
    )


def test_parameterconnection_not_step_referenced():
    """\
    Test a Provenance Run Crate where a ParameterConnection is not referenced
    by any HowToStep through the connection property.
    """
    do_entity_test(
        InvalidProvRC().parameterconnection_not_step_referenced,
        Severity.RECOMMENDED,
        False,
        ["ParameterConnection references on HowToStep instances"],
        ["Missing `HowToStep` connection to this `ParameterConnection` entity"],
        profile_identifier="provenance-run-crate"
    )
