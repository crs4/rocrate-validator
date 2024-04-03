import logging

from rocrate_validator import models
from tests.ro_crates import InvalidRootDataEntity
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidRootDataEntity()


def test_missing_root_data_entity():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.invalid_root_type,
        models.RequirementLevels.MUST,
        False,
        ["RO-Crate Root Data Entity MUST exist",
         "RO-Crate Metadata File Descriptor: recommended properties"],
        ["The file descriptor MUST have a root data entity of type schema_org:Dataset and ending with /"]
    )


def test_invalid_root_date():
    """Test a RO-Crate with an invalid root data entity date."""
    do_entity_test(
        paths.invalid_root_date,
        models.RequirementLevels.MUST,
        False,
        ["RO-Crate Data Entity definition"],
        ["The datePublished of the Root Data Entity MUST be a valid ISO 8601 date"]
    )


def test_missing_root_name():
    """Test a RO-Crate without a root data entity name."""
    do_entity_test(
        paths.missing_root_name,
        models.RequirementLevels.SHOULD,
        False,
        ["RO-Crate Data Entity definition: RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a schema_org:name"]
    )


def test_missing_root_description():
    """Test a RO-Crate without a root data entity description."""
    do_entity_test(
        paths.missing_root_description,
        models.RequirementLevels.SHOULD,
        False,
        ["RO-Crate Data Entity definition: RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a schema_org:description"]
    )


def test_missing_root_license():
    """Test a RO-Crate without a root data entity license."""
    do_entity_test(
        paths.missing_root_license,
        models.RequirementLevels.SHOULD,
        False,
        ["RO-Crate Data Entity definition: RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a link to a Contextual Entity representing the schema_org:license type"]
    )


def test_missing_root_license_name():
    """Test a RO-Crate without a root data entity license name."""
    do_entity_test(
        paths.missing_root_license_name,
        models.RequirementLevels.MAY,
        False,
        ["License definition"],
        ["Missing license name"]
    )


def test_missing_root_license_description():
    """Test a RO-Crate without a root data entity license description."""
    do_entity_test(
        paths.missing_root_license_description,
        models.RequirementLevels.MAY,
        False,
        ["License definition"],
        ["Missing license description"]
    )
