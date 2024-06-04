import logging

from rocrate_validator import models
from tests.ro_crates import InvalidDataEntity
from tests.shared import do_entity_test

# set up logging
logger = logging.getLogger(__name__)


#  Global set up the paths
paths = InvalidDataEntity()


def test_missing_data_entity_reference():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.missing_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        False,
        ["Data Entity: REQUIRED properties"],
        ["sort-and-change-case.ga", "foo/xxx"]
    )


def test_data_entity_must_be_directly_linked():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.direct_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        True
    )


def test_data_entity_must_be_indirectly_linked():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.indirect_hasPart_data_entity_reference,
        models.Severity.REQUIRED,
        True
    )


def test_directory_data_entity_wo_trailing_slash():
    """Test a RO-Crate without a root data entity."""
    do_entity_test(
        paths.directory_data_entity_wo_trailing_slash,
        models.Severity.REQUIRED,
        False,
        ["Directory Data Entity: REQUIRED value restriction"],
        ["Every Data Entity Directory URI MUST end with `/`"]
    )
