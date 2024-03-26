import logging

from pytest import fixture

from rocrate_validator import models
from tests.ro_crates import InvalidFileDescriptor, InvalidRootDataEntity
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


logger.debug(InvalidFileDescriptor.missing_file_descriptor)


@fixture(scope="module")
def paths():
    logger.debug("setup")
    cls = InvalidRootDataEntity()
    yield cls
    logger.debug("teardown")


def test_missing_root_data_entity(paths):
    """Test a RO-Crate without a root data entity."""

    do_entity_test(
        paths.missing_root,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Root Data Entity MUST exist",
        ["RO-Crate Root Data Entity MUST exist"]
    )


def test_invalid_root_type(paths):
    """Test a RO-Crate with an invalid root data entity type."""
    do_entity_test(
        paths.invalid_root_type,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Root Data Entity MUST exist",
        ["The file descriptor MUST have a root data entity of type schema_org:Dataset and ending with /"]
    )


def test_invalid_root_date(paths):
    """Test a RO-Crate with an invalid root data entity date."""
    do_entity_test(
        paths.invalid_root_date,
        models.RequirementLevels.MUST,
        False,
        "RO-Crate Data Entity definition",
        ["The datePublished of the Root Data Entity MUST be a valid ISO 8601 date"]
    )


def test_missing_root_name(paths):
    """Test a RO-Crate without a root data entity name."""
    do_entity_test(
        paths.missing_root_name,
        models.RequirementLevels.SHOULD,
        False,
        "RO-Crate Data Entity definition: RECOMMENDED properties",
        ["The Root Data Entity SHOULD have a schema_org:name"]
    )


def test_missing_root_description(paths):
    """Test a RO-Crate without a root data entity description."""
    do_entity_test(
        paths.missing_root_description,
        models.RequirementLevels.SHOULD,
        False,
        "RO-Crate Data Entity definition: RECOMMENDED properties",
        ["The Root Data Entity SHOULD have a schema_org:description"]
    )


def test_missing_root_license(paths):
    """Test a RO-Crate without a root data entity license."""
    do_entity_test(
        paths.missing_root_license,
        models.RequirementLevels.SHOULD,
        False,
        "RO-Crate Data Entity definition: RECOMMENDED properties",
        ["The Root Data Entity SHOULD have a link"]
    )


def test_missing_root_license_name(paths):
    """Test a RO-Crate without a root data entity license name."""
    do_entity_test(
        paths.missing_root_license_name,
        models.RequirementLevels.MAY,
        False,
        "License definition",
        ["Missing license name"]
    )


def test_missing_root_license_description(paths):
    """Test a RO-Crate without a root data entity license description."""
    do_entity_test(
        paths.missing_root_license_description,
        models.RequirementLevels.MAY,
        False,
        "License definition",
        ["Missing license description"]
    )
