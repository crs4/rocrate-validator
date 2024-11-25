# Copyright (c) 2024 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Library of shared functions for testing RO-Crate profiles
"""

import json
import logging
import shutil
import tempfile
from collections.abc import Collection
from pathlib import Path
from typing import Optional, TypeVar, Union

from rocrate_validator import models, services
from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER

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
        profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER,
        rocrate_entity_patch: Optional[dict] = None,
):
    """
    Shared function to test a RO-Crate entity
    """
    # declare variables
    failed_requirements = None
    detected_issues = None

    if not isinstance(rocrate_path, Path):
        rocrate_path = Path(rocrate_path)

    temp_rocrate_path = None
    if rocrate_entity_patch is not None and rocrate_path.is_dir():
        # create a temporary copy of the RO-Crate
        temp_rocrate_path = Path(tempfile.TemporaryDirectory().name)
        # copy the RO-Crate to the temporary path using shutil
        shutil.copytree(rocrate_path, temp_rocrate_path)
        # load the RO-Crate metadata as RO-Crate JSON-LD
        with open(temp_rocrate_path / "ro-crate-metadata.json", "r") as f:
            rocrate = json.load(f)
        # update the RO-Crate metadata with the patch
        for key, value in rocrate_entity_patch.items():
            for entity in rocrate["@graph"]:
                if entity["@id"] == key:
                    entity.update(value)
                    break
        # save the updated RO-Crate metadata
        with open(temp_rocrate_path / "ro-crate-metadata.json", "w") as f:
            json.dump(rocrate, f)
        rocrate_path = temp_rocrate_path

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
                "rocrate_uri": rocrate_path,
                "requirement_severity": requirement_severity,
                "abort_on_first": abort_on_first,
                "profile_identifier": profile_identifier
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
        detected_issues = [issue.message for issue in result.get_issues(requirement_severity)
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
    finally:
        # cleanup
        if temp_rocrate_path is not None:
            logger.debug("Cleaning up temporary RO-Crate @ path: %s", temp_rocrate_path)
            shutil.rmtree(temp_rocrate_path)
