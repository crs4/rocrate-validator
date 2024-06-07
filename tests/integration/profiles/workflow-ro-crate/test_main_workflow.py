import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidMainWorkflow
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_main_workflow_bad_type():
    """\
    Test a Workflow RO-Crate where the main workflow has an incorrect type.
    """
    do_entity_test(
        InvalidMainWorkflow().main_workflow_bad_type,
        Severity.REQUIRED,
        False,
        ["Main Workflow definition"],
        ["The Main Workflow must have types File, SoftwareSourceCode, ComputationalWorfklow"],
        profile_name="workflow-ro-crate"
    )
