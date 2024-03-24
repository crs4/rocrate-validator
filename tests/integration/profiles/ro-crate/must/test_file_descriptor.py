import logging
from pathlib import Path

from pytest import fixture

from rocrate_validator import models, services
from tests.ro_crates import InvalidFileDescriptor

logger = logging.getLogger(__name__)


logger.debug(InvalidFileDescriptor.missing_file_descriptor)


@fixture(scope="module")
def paths():
    logger.debug("setup")
    cls = InvalidFileDescriptor()
    yield cls
    logger.debug("teardown")


def test_path_initialization(paths):
    logger.debug(f"test_path_initialization: {paths.missing_file_descriptor}")
    assert paths.missing_file_descriptor, "missing_file_descriptor should be initialized"
    assert Path(paths.missing_file_descriptor).exists(), "missing_file_descriptor should exist"


def test_missing_file_descriptor(paths):

    with paths.missing_file_descriptor as rocrate_path:
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
        assert failed_requirement.name == "FileDescriptorExistence", \
            "Unexpected failed requirement"

        for issue in result.get_issues():
            logger.debug(f"Detected issue {type(issue)}: {issue.message}")


def test_not_valid_json_format(paths):

    rocrate_path = paths.invalid_json_format
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
    assert failed_requirement.name == "FileDescriptorJsonFormat", \
        "Unexpected failed requirement"

    for issue in result.get_issues():
        logger.debug(f"Detected issue {type(issue)}: {issue.message}")


def test_not_valid_jsonld_format_missing_context(paths):

    rocrate_path = f"{paths.invalid_jsonld_format}/missing_context"
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
    assert failed_requirement.name == "FileDescriptorJsonLdFormat", \
        "Unexpected failed requirement"

    for issue in result.get_issues():
        logger.debug(f"Detected issue {type(issue)}: {issue.message}")


def test_not_valid_jsonld_format_missing_ids(paths):

    rocrate_path = f"{paths.invalid_jsonld_format}/missing_id"
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
    assert failed_requirement.name == "FileDescriptorJsonLdFormat", \
        "Unexpected failed requirement"

    for issue in result.get_issues():
        logger.debug(f"Detected issue {type(issue)}: {issue.message}")


