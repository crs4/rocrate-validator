import logging
from pathlib import Path

from pytest import fixture

from rocrate_validator import models, services
from tests.ro_crates import InvalidFileDescriptor, InvalidRootDataEntity

logger = logging.getLogger(__name__)


logger.debug(InvalidFileDescriptor.missing_file_descriptor)


@fixture(scope="module")
def paths():
    logger.debug("setup")
    cls = InvalidRootDataEntity()
    yield cls
    logger.debug("teardown")


def test_missing_root_data_entity(paths):

    rocrate_path = paths.missing_root
    logger.debug(f"test_missing_file_descriptor: {rocrate_path}")

    result: models.ValidationResult = services.validate(rocrate_path,
                                                        requirement_level="MUST", abort_on_first=True)
    assert not result.passed(), "ro-crate should be invalid"

    # check requirement
    failed_requirements = result.failed_requirements
    for failed_requirement in failed_requirements:
        logger.debug(f"Failed requirement: {failed_requirement}")
    assert len(failed_requirements) == 1, "ro-crate should have 1 failed requirement"

    # set reference to failed requirement
    failed_requirement = failed_requirements[0]
    logger.debug(f"Failed requirement name: {failed_requirement.name}")

    # check if the failed requirement is the expected one
    assert failed_requirement.name == "RO-Crate Root Data Entity MUST exist", \
        "Unexpected failed requirement"

    for issue in result.get_issues():
        logger.debug(f"Detected issue {type(issue)}: {issue.message}")


