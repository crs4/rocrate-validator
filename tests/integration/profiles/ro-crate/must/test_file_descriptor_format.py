import logging

from rocrate_validator import models
from tests.ro_crates import InvalidFileDescriptor
from tests.shared import do_entity_test

logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidFileDescriptor()


def test_missing_file_descriptor():
    """Test a RO-Crate without a file descriptor."""
    with paths.missing_file_descriptor as rocrate_path:
        do_entity_test(
            rocrate_path,
            models.Severity.REQUIRED,
            False,
            ["FileDescriptorExistence"],
            []
        )


def test_not_valid_json_format():
    """Test a RO-Crate with an invalid JSON file descriptor format."""
    do_entity_test(
        paths.invalid_json_format,
        models.Severity.REQUIRED,
        False,
        ["FileDescriptorJsonFormat"],
        []
    )


def test_not_valid_jsonld_format_missing_context():
    """Test a RO-Crate with an invalid JSON-LD file descriptor format."""
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_context",
        models.Severity.REQUIRED,
        False,
        ["FileDescriptorJsonLdFormat"],
        []
    )


def test_not_valid_jsonld_format_missing_ids():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @id attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_id",
        models.Severity.REQUIRED,
        False,
        ["FileDescriptorJsonLdFormat"],
        ["file descriptor does not contain the @id attribute"]
    )


def test_not_valid_jsonld_format_missing_types():
    """
    Test a RO-Crate with an invalid JSON-LD file descriptor format.
    One or more entities in the file descriptor do not contain the @type attribute.
    """
    do_entity_test(
        f"{paths.invalid_jsonld_format}/missing_type",
        models.Severity.REQUIRED,
        False,
        ["FileDescriptorJsonLdFormat"],
        ["file descriptor does not contain the @type attribute"]
    )
