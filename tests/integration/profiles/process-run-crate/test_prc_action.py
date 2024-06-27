import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_prc_action_no_instrument():
    """\
    Test a Process Run Crate where the action does not have an instrument.
    """
    do_entity_test(
        InvalidProcRC().action_no_instrument,
        Severity.REQUIRED,
        False,
        ["Process Run Crate Action"],
        ["The Action MUST have an instrument property that references the executed tool"],
        profile_name="s_process-run-crate"
    )


def test_prc_action_instrument_bad_type():
    """\
    Test a Process Run Crate where the instrument does not point to a
    SoftwareApplication, SoftwareSourceCode or ComputationalWorkflow.
    """
    do_entity_test(
        InvalidProcRC().action_instrument_bad_type,
        Severity.REQUIRED,
        False,
        ["Process Run Crate Action"],
        ["The Action MUST have an instrument property that references the executed tool"],
        profile_name="s_process-run-crate"
    )


def test_prc_action_not_mentioned():
    """\
    Test a Process Run Crate where the action is not listed in the Root Data
    Entity's mentions.
    """
    do_entity_test(
        InvalidProcRC().action_not_mentioned,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD be referenced from the Root Data Entity via mentions"],
        profile_name="s_process-run-crate"
    )


def test_prc_action_no_name():
    """\
    Test a Process Run Crate where the action does not have an name.
    """
    do_entity_test(
        InvalidProcRC().action_no_name,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have a name"],
        profile_name="s_process-run-crate"
    )


def test_prc_action_no_description():
    """\
    Test a Process Run Crate where the action does not have a description.
    """
    do_entity_test(
        InvalidProcRC().action_no_description,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have a description"],
        profile_name="s_process-run-crate"
    )


def test_prc_action_no_endtime():
    """\
    Test a Process Run Crate where the action does not have an endTime.
    """
    do_entity_test(
        InvalidProcRC().action_no_endtime,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Action SHOULD"],
        ["The Action SHOULD have an endTime"],
        profile_name="s_process-run-crate"
    )
