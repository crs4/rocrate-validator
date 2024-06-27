import logging

from rocrate_validator.models import Severity
from tests.ro_crates import WROCNoLicense
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_wroc_no_tests():
    """\
    Test a Workflow RO-Crate with no test/ Dataset.
    """
    do_entity_test(
        WROCNoLicense().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["test directory"],
        ["The test/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate"
    )


def test_wroc_no_examples():
    """\
    Test a Workflow RO-Crate with no examples/ Dataset.
    """
    do_entity_test(
        WROCNoLicense().wroc_no_license,
        Severity.OPTIONAL,
        False,
        ["examples directory"],
        ["The examples/ dir should be a Dataset"],
        profile_identifier="workflow-ro-crate"
    )
