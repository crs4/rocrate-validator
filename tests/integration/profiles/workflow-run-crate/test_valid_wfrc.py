import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_workflow_run_crate_required():
    """Test a valid Workflow Run Crate."""
    do_entity_test(
        ValidROC().workflow_run_crate,
        Severity.REQUIRED,
        True,
        profile_identifier="workflow-run-crate"
    )
