import logging

from rocrate_validator.models import Severity
from tests.ro_crates import InvalidProcRC
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


def test_procrc_collection_not_mentioned():
    """\
    Test a Process Run Crate where the collection is not listed in the Root
    Data Entity's mentions.
    """
    do_entity_test(
        InvalidProcRC().collection_not_mentioned,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD be referenced from the Root Data Entity via mentions"],
        profile_identifier="process-run-crate"
    )


def test_procrc_collection_no_haspart():
    """\
    Test a Process Run Crate where the collection does not have a hasPart.
    """
    do_entity_test(
        InvalidProcRC().collection_no_haspart,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD have a hasPart"],
        profile_identifier="process-run-crate"
    )


def test_procrc_collection_no_mainentity():
    """\
    Test a Process Run Crate where the collection does not have a mainEntity.
    """
    do_entity_test(
        InvalidProcRC().collection_no_mainentity,
        Severity.RECOMMENDED,
        False,
        ["Process Run Crate Collection SHOULD"],
        ["The Collection SHOULD have a mainEntity"],
        profile_identifier="process-run-crate"
    )
