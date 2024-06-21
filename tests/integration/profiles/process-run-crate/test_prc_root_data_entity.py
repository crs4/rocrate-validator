import logging

from rocrate_validator.models import Severity
from tests.ro_crates import ValidROC, InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_prc_no_conformsto():
    """\
    Test a Process Run Crate where the root data entity does not have a
    conformsTo.
    """
    do_entity_test(
        ValidROC().workflow_roc,
        Severity.REQUIRED,
        False,
        ["Root Data Entity Metadata"],
        ["The Root Data Entity MUST reference a CreativeWork entity with an @id URI that is consistent with the versioned permalink of the profile"],
        profile_name="s_process-run-crate"
    )


def test_prc_conformsto_bad_type():
    """\
    Test a Process Run Crate where the root data entity does not conformsTo a
    CreativeWork.
    """
    do_entity_test(
        InvalidProcRC().conformsto_bad_type,
        Severity.REQUIRED,
        False,
        ["Root Data Entity Metadata"],
        ["The Root Data Entity MUST reference a CreativeWork entity with an @id URI that is consistent with the versioned permalink of the profile"],
        profile_name="s_process-run-crate"
    )


def test_prc_conformsto_bad_profile():
    """\
    Test a Process Run Crate where the root data entity does not conformsTo a
    Process Run Crate profile.
    """
    do_entity_test(
        InvalidProcRC().conformsto_bad_profile,
        Severity.REQUIRED,
        False,
        ["Root Data Entity Metadata"],
        ["The Root Data Entity MUST reference a CreativeWork entity with an @id URI that is consistent with the versioned permalink of the profile"],
        profile_name="s_process-run-crate"
    )
