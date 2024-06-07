"""
Library of shared functions for testing RO-Crate profiles
"""

import logging
from collections.abc import Collection
from pathlib import Path
from typing import Optional, TypeVar, Union

from rocrate_validator import models, services

logger = logging.getLogger(__name__)


T = TypeVar("T")


def first(c: Collection[T]) -> T:
    return next(iter(c))


def do_entity_test(
        rocrate_path: Union[Path, str],
        requirement_severity: models.Severity,
        expected_validation_result: bool,
        expected_triggered_requirements: Optional[list[str]] = None,
        expected_triggered_issues: Optional[list[str]] = None,
        abort_on_first: bool = True,
        profile_name: str = "ro-crate"
):
    """
    Shared function to test a RO-Crate entity
    """
    # declare variables
    failed_requirements = None
    detected_issues = None

    if not isinstance(rocrate_path, Path):
        rocrate_path = Path(rocrate_path)

    if expected_triggered_requirements is None:
        expected_triggered_requirements = []
    if expected_triggered_issues is None:
        expected_triggered_issues = []

    try:
        logger.debug("Testing RO-Crate @ path: %s", rocrate_path)
        logger.debug("Requirement severity: %s", requirement_severity)

        # set abort_on_first to False
        abort_on_first = False

        # validate RO-Crate
        result: models.ValidationResult = \
            services.validate(models.ValidationSettings(**{
                "data_path": rocrate_path,
                "requirement_severity": requirement_severity,
                "abort_on_first": abort_on_first,
                "profile_name": profile_name
            }))
        logger.debug("Expected validation result: %s", expected_validation_result)

        assert result.context is not None, "Validation context should not be None"
        f"Expected requirement severity to be {requirement_severity}, but got {result.context.requirement_severity}"
        assert result.passed() == expected_validation_result, \
            f"RO-Crate should be {'valid' if expected_validation_result else 'invalid'}"

        # check requirement
        failed_requirements = [_.name for _ in result.failed_requirements]
        # assert len(failed_requirements) == len(expected_triggered_requirements), \
        #     f"Expected {len(expected_triggered_requirements)} requirements to be "\
        #     f"triggered, but got {len(failed_requirements)}"

        # check that the expected requirements are triggered
        for expected_triggered_requirement in expected_triggered_requirements:
            if expected_triggered_requirement not in failed_requirements:
                assert False, f"The expected requirement " \
                    f"\"{expected_triggered_requirement}\" was not found in the failed requirements"

        # check requirement issues
        detected_issues = [issue.message for issue in result.get_issues(models.Severity.RECOMMENDED)
                           if issue.message is not None]
        logger.debug("Detected issues: %s", detected_issues)
        logger.debug("Expected issues: %s", expected_triggered_issues)
        for expected_issue in expected_triggered_issues:
            if not any(expected_issue in issue for issue in detected_issues):  # support partial match
                assert False, f"The expected issue \"{expected_issue}\" was not found in the detected issues"
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(e)
            logger.debug("Failed to validate RO-Crate @ path: %s", rocrate_path)
            logger.debug("Requirement severity: %s", requirement_severity)
            logger.debug("Expected validation result: %s", expected_validation_result)
            logger.debug("Expected triggered requirements: %s", expected_triggered_requirements)
            logger.debug("Expected triggered issues: %s", expected_triggered_issues)
            logger.debug("Failed requirements: %s", failed_requirements)
            logger.debug("Detected issues: %s", detected_issues)
        raise e
