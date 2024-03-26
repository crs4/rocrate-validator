import logging
from pathlib import Path
from typing import List

from rocrate_validator import models, services

logger = logging.getLogger(__name__)


def do_entity_test(
        rocrate_path: Path,
        requirement_level: models.RequirementType,
        expected_validation_result: bool,
        expected_triggered_requirement_name: str,
        expected_triggered_issues: List[str]
):
    logger.debug(f"Testing RO-Crate @ path: {rocrate_path}")
    logger.debug(f"Requirement level: {requirement_level}")

    result: models.ValidationResult = \
        services.validate(rocrate_path,
                          requirement_level=requirement_level, abort_on_first=True)
    logger.debug(f"Expected validation result: {expected_validation_result}")
    assert result.passed() == expected_validation_result, \
        f"RO-Crate should be {'valid' if expected_validation_result else 'invalid'}"

    # check requirement
    failed_requirements = result.failed_requirements
    for failed_requirement in failed_requirements:
        logger.debug(f"Failed requirement: {failed_requirement}")
    assert len(failed_requirements) == 1, "ro-crate should have 1 failed requirement"

    # set reference to failed requirement
    failed_requirement = failed_requirements[0]
    logger.debug(f"Failed requirement name: {failed_requirement.name}")

    # check if the failed requirement is the expected one
    logger.debug(f"Expected requirement name: {expected_triggered_requirement_name}")
    assert failed_requirement.name == expected_triggered_requirement_name, \
        f"Unexpected failed requirement: it MUST be {expected_triggered_requirement_name}"

    # check requirement issues
    logger.debug(f"Expected issues: {expected_triggered_issues}")
    for issue in result.get_issues():
        logger.debug(f"Detected issue {type(issue)}: {issue.message}")
