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
    """Test a RO-Crate without a file descriptor entity."""
    do_entity_test(
        paths.missing_entity,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Metadata File Descriptor entity MUST exist",
        ["The root of the document MUST have an entity with @id `ro-crate-metadata.json`"]
    )


def test_invalid_entity_type(paths):
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.invalid_entity_type,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Metadata File Descriptor: recommended properties",
        ["The RO-Crate metadata file MUST be a CreativeWork, as per schema.org"]
    )


def test_missing_entity_about(paths):
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.missing_entity_about,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Metadata File Descriptor: recommended properties",
        ["The RO-Crate metadata file descriptor MUST have an `about` property"]
    )


def test_invalid_entity_about_type(paths):
    """Test a RO-Crate with an invalid file descriptor entity type."""
    do_entity_test(
        paths.invalid_entity_about_type,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Metadata File Descriptor: recommended properties",
        ["The RO-Crate metadata file descriptor MUST have an `about` property"]
    )
