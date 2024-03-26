import logging

from pytest import fixture

from rocrate_validator import models
from tests.ro_crates import InvalidFileDescriptor
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


logger.debug(InvalidFileDescriptor.missing_file_descriptor)


@fixture(scope="module")
def paths():
    logger.debug("setup")
    cls = InvalidFileDescriptor()
    yield cls
    logger.debug("teardown")


def test_missing_file_descriptor(paths):
    """Test a RO-Crate without a file descriptor."""
    with paths.missing_file_descriptor as rocrate_path:
        do_entity_test(
            rocrate_path,
            models.RequirementLevels.MUST,
            False,
            "FileDescriptorExistence",
            []
        )


def test_not_valid_json_format(paths):
    """Test a RO-Crate with an invalid JSON file descriptor format."""
    do_entity_test(
        paths.invalid_json_format,
        models.RequirementLevels.MUST,
        False,
        "FileDescriptorJsonFormat",
        []
    )


def test_not_valid_jsonld_format_missing_context(paths):
    """Test a RO-Crate with an invalid JSON-LD file descriptor format."""
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_context",
        models.RequirementLevels.MUST,
        False,
        "FileDescriptorJsonLdFormat",
        []
    )


def test_not_valid_jsonld_format_missing_ids(paths):
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @id attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_id",
        models.RequirementLevels.MUST,
        False,
        "FileDescriptorJsonLdFormat",
        ["file descriptor does not contain the @id attribute"]
    )


def test_not_valid_jsonld_format_missing_types(paths):
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @type attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_type",
        models.RequirementLevels.MUST,
        False,
        "FileDescriptorJsonLdFormat",
        ["file descriptor does not contain the @type attribute"]
    )
