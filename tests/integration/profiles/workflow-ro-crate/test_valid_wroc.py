import logging
import pytest

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_valid_workflow_roc_required():
    """Test a valid Workflow RO-Crate."""
    do_entity_test(
        ValidROC().workflow_roc,
        Severity.REQUIRED,
        True,
        profile_identifier="workflow-ro-crate"
    )
    do_entity_test(
        ValidROC().workflow_roc_string_license,
        Severity.REQUIRED,
        True,
        profile_identifier="workflow-ro-crate"
    )
