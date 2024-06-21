import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_workflow_roc_required():
    """Test a valid Process Run Crate."""
    do_entity_test(
        ValidROC().process_run_crate,
        Severity.REQUIRED,
        True,
        profile_name="s_process-run-crate"
    )
