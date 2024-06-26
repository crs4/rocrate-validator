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
