import logging

import pytest

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


@pytest.mark.xfail(reason="Known problem with data validation in RO-Crate profile")
def test_valid_roc_required():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper,
        Severity.REQUIRED,
        True
    )


@pytest.mark.xfail(reason="Known problem with data validation in RO-Crate profile")
def test_valid_roc_recommended():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper,
        Severity.RECOMMENDED,
        True
    )


def test_valid_roc_required_with_long_datetime():
    """Test a valid RO-Crate."""
    do_entity_test(
        ValidROC().wrroc_paper_long_date,
        Severity.REQUIRED,
        True
    )
