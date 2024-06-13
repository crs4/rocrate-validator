import logging

from rocrate_validator.models import Severity
from tests.ro_crates import WROCNoLicense
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


def test_wroc_no_license():
    """\
    Test a Workflow RO-Crate where the root data entity has no license.
    """
    do_entity_test(
        WROCNoLicense().wroc_no_license,
        Severity.REQUIRED,
        False,
        ["WROC Root Data Entity Required Properties"],
        ["The Crate (Root Data Entity) must specify a license, which should be a URL but can also be a string"],
        profile_name="workflow-ro-crate"
    )
