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


def test_provrc_controlaction_no_instrument():
    """\
    Test a Provenance Run Crate where a ControlAction has no instrument.
    """
    do_entity_test(
        InvalidProvRC().controlaction_no_instrument,
        Severity.REQUIRED,
        False,
        ["ProvRC ControlAction MUST"],
        ["A ControlAction must reference a HowToStep instance representing "
         "the corresponding workflow step via instrument"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_bad_instrument():
    """\
    Test a Provenance Run Crate where a ControlAction instrument does not
    point to a HowToStep.
    """
    do_entity_test(
        InvalidProvRC().controlaction_bad_instrument,
        Severity.REQUIRED,
        False,
        ["ProvRC ControlAction MUST"],
        ["A ControlAction must reference a HowToStep instance representing "
         "the corresponding workflow step via instrument"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_no_object():
    """\
    Test a Provenance Run Crate where a ControlAction has no object.
    """
    do_entity_test(
        InvalidProvRC().controlaction_no_object,
        Severity.REQUIRED,
        False,
        ["ProvRC ControlAction MUST"],
        ["A ControlAction must reference the action representing the corresponding tool run via object"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_bad_object():
    """\
    Test a Provenance Run Crate where a ControlAction object does not point to
    an action.
    """
    do_entity_test(
        InvalidProvRC().controlaction_bad_object,
        Severity.REQUIRED,
        False,
        ["ProvRC ControlAction MUST"],
        ["A ControlAction must reference the action representing the corresponding tool run via object"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_no_actionstatus():
    """\
    Test a Provenance Run Crate where a ControlAction has no actionStatus.
    """
    do_entity_test(
        InvalidProvRC().controlaction_no_actionstatus,
        Severity.OPTIONAL,
        False,
        ["ProvRC ControlAction and OrganizeAction MAY"],
        ["The Action MAY have an actionStatus"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_bad_actionstatus():
    """\
    Test a Provenance Run Crate where a ControlAction has an invalid
    actionStatus.
    """
    do_entity_test(
        InvalidProvRC().controlaction_bad_actionstatus,
        Severity.RECOMMENDED,
        False,
        ["ProvRC ControlAction and OrganizeAction SHOULD"],
        ["If the action has an actionStatus, it should be "
         "http://schema.org/CompletedActionStatus or "
         "http://schema.org/FailedActionStatus"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_no_error():
    """\
    Test a Provenance Run Crate where a ControlAction with an actionStatus
    set to FailedActionStatus has no error.
    """
    do_entity_test(
        InvalidProvRC().controlaction_no_error,
        Severity.OPTIONAL,
        False,
        ["ProvRC ControlAction and OrganizeAction error"],
        ["error MAY be specified if actionStatus is set to FailedActionStatus"],
        profile_identifier="provenance-run-crate"
    )


def test_provrc_controlaction_error_not_failed_status():
    """\
    Test a Provenance Run Crate where a ControlAction with an actionStatus
    different from FailedActionStatus sets the error property
    """
    do_entity_test(
        InvalidProvRC().controlaction_error_not_failed_status,
        Severity.RECOMMENDED,
        False,
        ["Provenance Run Crate ControlAction and OrganizeAction error"],
        ["error SHOULD NOT be specified unless actionStatus is set to FailedActionStatus"],
        profile_identifier="provenance-run-crate"
    )
