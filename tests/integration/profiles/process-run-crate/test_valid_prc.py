import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_process_run_crate_required():
    """Test a valid Process Run Crate."""
    do_entity_test(
        ValidROC().process_run_crate,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate"
    )
    do_entity_test(
        ValidROC().process_run_crate_collections,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate"
    )
    do_entity_test(
        ValidROC().process_run_crate_containerimage,
        Severity.REQUIRED,
        True,
        profile_identifier="process-run-crate"
    )
