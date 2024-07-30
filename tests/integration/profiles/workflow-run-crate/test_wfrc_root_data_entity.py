import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidWfRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_procrc_conformsto_no_wfrc():
    """\
    Test a Workflow Run Crate where the root data entity does not conformsTo
    the Workflow Run Crate profile.
    """
    do_entity_test(
        InvalidWfRC().conformsto_no_wfrc,
        Severity.REQUIRED,
        False,
        ["Root Data Entity Metadata"],
        ["The Root Data Entity MUST reference a CreativeWork entity with an @id URI that is consistent with the versioned permalink of the Workflow Run Crate profile"],
        profile_identifier="workflow-run-crate"
    )


def test_procrc_conformsto_no_wroc():
    """\
    Test a Workflow Run Crate where the root data entity does not conformsTo
    the Workflow RO-Crate profile.
    """
    do_entity_test(
        InvalidWfRC().conformsto_no_wroc,
        Severity.RECOMMENDED,
        False,
        ["Root Data Entity Metadata SHOULD"],
        ["The Root Data Entity SHOULD reference CreativeWork entities corresponding to the Process Run Crate and Workflow RO-Crate profiles"],
        profile_identifier="workflow-run-crate"
    )
