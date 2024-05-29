import logging

import pytest

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
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Root Data Entity type"],
        ["The Root Data Entity MUST be a `Dataset` (as per `schema.org`)"]
    )


def test_invalid_root_data_entity_value():
    """Test a RO-Crate with an invalid root data entity value."""
    do_entity_test(
        paths.invalid_root_value,
        models.Severity.REQUIRED,
        False,
        ["RO-Crate Root Data Entity value restriction"],
        ["The Root Data Entity URI MUST end with `/`"]
    )


def test_invalid_root_date():
    """Test a RO-Crate with an invalid root data entity date."""
    do_entity_test(
        paths.invalid_root_date,
        models.Severity.RECOMMENDED,
        False,
        ["RO-Crate Root Data Entity RECOMMENDED properties"],
        ["The datePublished of the Root Data Entity MUST be a valid ISO 8601 date"]
    )


def test_missing_root_name():
    """Test a RO-Crate without a root data entity name."""
    do_entity_test(
        paths.missing_root_name,
        models.Severity.RECOMMENDED,
        False,
        ["RO-Crate Root Data Entity RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a schema_org:name"]
    )


def test_missing_root_description():
    """Test a RO-Crate without a root data entity description."""
    do_entity_test(
        paths.missing_root_description,
        models.Severity.RECOMMENDED,
        False,
        ["RO-Crate Root Data Entity RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a schema_org:description"]
    )


def test_missing_root_license():
    """Test a RO-Crate without a root data entity license."""
    do_entity_test(
        paths.missing_root_license,
        models.Severity.RECOMMENDED,
        False,
        ["RO-Crate Root Data Entity RECOMMENDED properties"],
        ["The Root Data Entity SHOULD have a link to a Contextual Entity representing the schema_org:license type"]
    )


def test_missing_root_license_name():
    """Test a RO-Crate without a root data entity license name."""
    do_entity_test(
        paths.missing_root_license_name,
        models.Severity.OPTIONAL,
        False,
        ["License definition"],
        ["Missing license name"]
    )


def test_missing_root_license_description():
    """Test a RO-Crate without a root data entity license description."""
    do_entity_test(
        paths.missing_root_license_description,
        models.Severity.OPTIONAL,
        False,
        ["License definition"],
        ["Missing license description"]
    )
