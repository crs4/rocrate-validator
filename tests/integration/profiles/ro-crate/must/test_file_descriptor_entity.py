import logging

from pytest import fixture

from rocrate_validator import models
from tests.ro_crates import InvalidFileDescriptorEntity
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


@fixture(scope="module")
def paths():
    logger.debug("setup")
    cls = InvalidFileDescriptorEntity()
    yield cls
    logger.debug("teardown")


def test_missing_entity(paths):
    do_entity_test(
        paths.missing_entity,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Metadata File Descriptor entity MUST exist",
        ["RO-Crate Metadata File Descriptor entity MUST exist"]
    )
