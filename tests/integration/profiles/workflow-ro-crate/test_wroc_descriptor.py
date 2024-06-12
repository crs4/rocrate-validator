import logging

from rocrate_validator.models import Severity
from tests.ro_crates import WROCInvalidConformsTo
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_wroc_descriptor_bad_conforms_to():
    """\
    Test a Workflow RO-Crate where the metadata file descriptor does not
    contain the required URIs.
    """
    do_entity_test(
        WROCInvalidConformsTo().wroc_descriptor_bad_conforms_to,
        Severity.RECOMMENDED,
        False,
        ["WROC Metadata File Descriptor properties"],
        ["The Metadata File Descriptor conformsTo SHOULD contain https://w3id.org/ro/crate/1.1 and https://w3id.org/workflowhub/workflow-ro-crate/1.0"],
        profile_name="workflow-ro-crate"
    )
