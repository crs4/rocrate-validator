"""
Library of shared functions for testing RO-Crate profiles
"""

import logging
from pathlib import Path
from typing import List

from rocrate_validator import models, services

logger = logging.getLogger(__name__)


def do_entity_test(
        rocrate_path: Path,
        requirement_level: models.RequirementType,
        expected_validation_result: bool,
        expected_triggered_requirements: List[str],
        expected_triggered_issues: List[str],
        abort_on_first: bool = True
):
    """
    Shared function to test a RO-Crate entity
    """
    # declare variables
    failed_requirements = None
    detected_issues = None

    try:
        logger.debug("Testing RO-Crate @ path: %s", rocrate_path)
        logger.debug("Requirement level: %s", requirement_level)

        # set abort_on_first to False if there are multiple expected requirements or issues
        if len(expected_triggered_requirements) > 1 \
                or len(expected_triggered_issues) > 1:
            abort_on_first = False

        # validate RO-Crate
        result: models.ValidationResult = \
            services.validate(rocrate_path,
                              requirement_level=requirement_level,
                              abort_on_first=abort_on_first)
        logger.debug("Expected validation result: %s", expected_validation_result)
        assert result.passed() == expected_validation_result, \
            f"RO-Crate should be {'valid' if expected_validation_result else 'invalid'}"

        # check requirement
        failed_requirements = [_.name for _ in result.failed_requirements]
        assert len(failed_requirements) == len(expected_triggered_requirements), \
            f"Expected {len(expected_triggered_requirements)} requirements to be "\
            f"triggered, but got {len(failed_requirements)}"

        # check that the expected requirements are triggered
        for expected_triggered_requirement in expected_triggered_requirements:
            if expected_triggered_requirement not in failed_requirements:
                assert False, f"The expected requirement " \
                    f"\"{expected_triggered_requirement}\" was not found in the failed requirements"

        # check requirement issues
        detected_issues = [issue.message for issue in result.get_issues()]
        logger.debug("Detected issues: %s", detected_issues)
        logger.debug("Expected issues: %s", expected_triggered_issues)
        for expected_issue in expected_triggered_issues:
            if not any(expected_issue in issue for issue in detected_issues):  # support partial match
                assert False, f"The expected issue \"{expected_issue}\" was not found in the detected issues"
    except Exception as e:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception(e)
            logger.debug("Failed to validate RO-Crate @ path: %s", rocrate_path)
            logger.debug("Requirement level: %s", requirement_level)
            logger.debug("Expected validation result: %s", expected_validation_result)
            logger.debug("Expected triggered requirements: %s", expected_triggered_requirements)
            logger.debug("Expected triggered issues: %s", expected_triggered_issues)
            logger.debug("Failed requirements: %s", failed_requirements)
            logger.debug("Detected issues: %s", detected_issues)
        raise e
