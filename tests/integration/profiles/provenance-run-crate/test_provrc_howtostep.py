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


def test_provrc_howtostep_no_inv_step():
    """\
    Test a Provenance Run Crate where a HowToStep is not referred to via step.
    """
    do_entity_test(
        InvalidProvRC().howtostep_no_inv_step,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["A HowToStep must be referred to from a ComputationalWorkflow via step"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_bad_inv_step():
    """\
    Test a Provenance Run Crate where a HowToStep is not referred to from a
    ComputationalWorkflow via step.
    """
    do_entity_test(
        InvalidProvRC().howtostep_bad_inv_step,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["A HowToStep must be referred to from a ComputationalWorkflow via step"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_no_workexample():
    """\
    Test a Provenance Run Crate where a HowToStep has no workExample.
    """
    do_entity_test(
        InvalidProvRC().howtostep_no_workexample,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["A HowToStep must refer to its corresponding tool via workExample"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_bad_workexample():
    """\
    Test a Provenance Run Crate where a HowToStep does not refer to a tool via
    workExample.
    """
    do_entity_test(
        InvalidProvRC().howtostep_bad_workexample,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["A HowToStep must refer to its corresponding tool via workExample"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_no_position():
    """\
    Test a Provenance Run Crate where a HowToStep has no position.
    """
    do_entity_test(
        InvalidProvRC().howtostep_no_position,
        Severity.OPTIONAL,
        False,
        ["ProvRC HowToStep MAY"],
        ["A HowToStep may indicate its position in the execution order via position"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_bad_position():
    """\
    Test a Provenance Run Crate where a HowToStep has a position that is not
    a string representing an integer.
    """
    do_entity_test(
        InvalidProvRC().howtostep_bad_position,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["If specified, position must be a string representing an integer"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_no_connection():
    """\
    Test a Provenance Run Crate where a HowToStep has no connection.
    """
    do_entity_test(
        InvalidProvRC().howtostep_no_connection,
        Severity.OPTIONAL,
        False,
        ["ProvRC HowToStep MAY"],
        ["HowToStep may have a connection property"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_bad_connection():
    """\
    Test a Provenance Run Crate where a HowToStep has a connection that does
    not point to a ParameterConnection.
    """
    do_entity_test(
        InvalidProvRC().howtostep_bad_connection,
        Severity.REQUIRED,
        False,
        ["ProvRC HowToStep MUST"],
        ["If the HowToStep has a connection, it must point to a ParameterConnection"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_no_buildinstructions():
    """\
    Test a Provenance Run Crate where a HowToStep has no buildInstructions.
    """
    do_entity_test(
        InvalidProvRC().howtostep_no_buildinstructions,
        Severity.OPTIONAL,
        False,
        ["ProvRC HowToStep MAY"],
        ["A HowToStep MAY have a buildInstructions pointing to a File"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_howtostep_bad_buildinstructions():
    """\
    Test a Provenance Run Crate where a HowToStep has a buildInstructions
    that does not point to a File.
    """
    do_entity_test(
        InvalidProvRC().howtostep_bad_buildinstructions,
        Severity.OPTIONAL,
        False,
        ["ProvRC HowToStep MAY"],
        ["A HowToStep MAY have a buildInstructions pointing to a File"],
        profile_identifier="provenance-run-crate"
    )
