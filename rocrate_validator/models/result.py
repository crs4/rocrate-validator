# Copyright (c) 2024-2026 CRS4
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

from __future__ import annotations

import bisect
import json
from functools import total_ordering
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rocrate_validator import __version__
from rocrate_validator.constants import JSON_OUTPUT_FORMAT_VERSION
from rocrate_validator.models._logging import logger
from rocrate_validator.models.requirement import (
    Requirement,
    RequirementCheck,
)
from rocrate_validator.models.severity import (
    RequirementLevel,
    Severity,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from rocrate_validator.models.settings import ValidationSettings
    from rocrate_validator.models.statistics import ValidationStatistics
    from rocrate_validator.models.validation import ValidationContext


@total_ordering
class CheckIssue:
    """
    Represents an issue with a check that has been executed
    during the validation process.
    """

    def __init__(
        self,
        check: RequirementCheck,
        message: str | None = None,
        violatingProperty: str | None = None,
        violatingEntity: str | None = None,
        value: str | None = None,
    ):
        self._message = message
        self._check: RequirementCheck = check
        self._violatingProperty = violatingProperty
        self._violatingEntity = violatingEntity
        self._propertyValue = value

    @property
    def message(self) -> str | None:
        """The message associated with the issue"""
        return self._message

    @property
    def level(self) -> RequirementLevel:
        """The level of the issue"""
        return self._check.level

    @property
    def severity(self) -> Severity:
        """Severity of the RequirementLevel associated with this check."""
        return self._check.severity

    @property
    def level_name(self) -> str:
        return self.level.name

    @property
    def check(self) -> RequirementCheck:
        """The check that generated the issue"""
        return self._check

    @property
    def violatingEntity(self) -> str | None:
        """
        It represents the specific element being evaluated that fails
        to meet the defined rules or constraints within a validation process.
        Also referred to as `focusNode` in SHACL terminology
        in the context of an RDF graph, it is the subject of a triple
        that violates a given constraint on the subject's property/predicate,
        represented by the violatingProperty.
        """
        return self._violatingEntity

    @property
    def violatingProperty(self) -> str | None:
        """
        It refers to the specific property or relationship within an item
        that leads to a validation failure.
        It identifies the part of the data structure that is causing the issue.
        Also referred to as `resultPath` in SHACL terminology,
        in the context of an RDF graph, it is the predicate of a triple
        that violates a given constraint on the subject's property/predicate,
        represented by the violatingProperty.
        """
        return self._violatingProperty

    @property
    def violatingPropertyValue(self) -> str | None:
        """
        It represents the value of the violatingProperty
        that leads to a validation failure.
        """
        return self._propertyValue

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CheckIssue) and self._check == other._check and self._message == other._message

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CheckIssue):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return (self._check, self._message) < (other._check, other._message)

    def __hash__(self) -> int:
        return hash((self._check, self._message))

    def __repr__(self) -> str:
        return f"CheckIssue(severity={self.severity}, check={self.check}, message={self.message})"

    def __str__(self) -> str:
        return f'Issue of severity {self.severity.name} with check "{self.check.identifier}": {self.message}'

    def to_dict(
        self,
        with_check: bool = True,
        with_requirement: bool = True,
        with_profile: bool = True,
    ) -> dict:
        result: dict[str, Any] = {
            "severity": self.severity.name,
            "message": self.message,
            "violatingEntity": self.violatingEntity,
            "violatingProperty": self.violatingProperty,
            "violatingPropertyValue": self.violatingPropertyValue,
        }
        if with_check:
            result["check"] = self.check.to_dict(with_requirement=with_requirement, with_profile=with_profile)
        return result

    def to_json(
        self,
        with_checks: bool = True,
        with_requirements: bool = True,
        with_profile: bool = True,
    ) -> str:
        return json.dumps(
            self.to_dict(
                with_check=with_checks,
                with_requirement=with_requirements,
                with_profile=with_profile,
            ),
            indent=4,
            cls=CustomEncoder,
        )


class ValidationResult:
    """
    Represents the result of a validation.

    :param context: The validation context
    :type context: ValidationContext
    :param rocrate_uri: The URI of the RO-Crate
    :type rocrate_uri: str
    :param validation_settings: The validation settings
    :type validation_settings: ValidationSettings
    :param issues: The issues found during the validation
    :type issues: list[CheckIssue]
    """

    def __init__(self, context: ValidationContext):
        from rocrate_validator.models.statistics import ValidationStatistics  # noqa: PLC0415

        # reference to the validation context
        self._context = context
        # reference to the ro-crate URI
        self._rocrate_uri = context.rocrate_uri
        # reference to the validation settings
        self._validation_settings: ValidationSettings = context.settings
        # keep track of the issues found during the validation
        self._issues: list[CheckIssue] = []
        # keep track of the checks that have been executed
        self._executed_checks: set[RequirementCheck] = set()
        self._executed_checks_results: dict[str, bool] = {}
        # keep track of the checks that have been skipped
        self._skipped_checks: set[RequirementCheck] = set()
        # initialize the statistics
        self._statistics = ValidationStatistics(context.settings)

    @property
    def context(self) -> ValidationContext:
        """
        The validation context
        """
        return self._context

    @property
    def rocrate_uri(self):
        """
        The URI of the RO-Crate
        """
        return self._rocrate_uri

    @property
    def validation_settings(self):
        """
        The validation settings
        """
        return self._validation_settings

    @property
    def statistics(self) -> ValidationStatistics:
        """
        The validation statistics
        """
        return self._statistics

    # --- Checks ---

    @property
    def executed_checks(self) -> set[RequirementCheck]:
        """
        The checks that have been executed
        """
        return self._executed_checks

    def _add_executed_check(self, check: RequirementCheck, result: bool):
        """
        Internal method to add a check to the executed checks
        """
        self._executed_checks.add(check)
        self._executed_checks_results[check.identifier] = result
        # remove the check from the skipped checks if it was skipped
        if check in self._skipped_checks:
            self._skipped_checks.remove(check)
            logger.debug("Removing check '%s' from skipped checks", check.name)

    def get_executed_check_result(self, check: RequirementCheck) -> bool | None:
        """
        Get the result of an executed check
        """
        return self._executed_checks_results.get(check.identifier)

    @property
    def skipped_checks(self) -> set[RequirementCheck]:
        """
        The checks that have been skipped
        """
        return self._skipped_checks

    def _add_skipped_check(self, check: RequirementCheck):
        """
        Internal method to add a check to the skipped checks
        """
        self._skipped_checks.add(check)

    def _remove_skipped_check(self, check: RequirementCheck):
        """
        Internal method to remove a check from the skipped checks
        """
        self._skipped_checks.remove(check)

    #  --- Issues ---
    @property
    def issues(self) -> list[CheckIssue]:
        """
        The issues found during the validation
        """
        return self._issues.copy()

    def get_issues(self, min_severity: Severity | None = None) -> list[CheckIssue]:
        """
        Get the issues found during the validation with a severity greater than or equal to `min_severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.severity >= min_severity]

    def get_issues_by_check(self, check: RequirementCheck, min_severity: Severity | None = None) -> list[CheckIssue]:
        """
        Get the issues found during the validation for a specific check
        with a severity greater than or equal to `min_severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.check == check and issue.severity >= min_severity]

    def has_issues(self, min_severity: Severity | None = None) -> bool:
        """
        Check if there are issues with a severity greater than or equal to the given `severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return any(issue.severity >= min_severity for issue in self._issues)

    def passed(self, min_severity: Severity | None = None) -> bool:
        """
        Check if all checks passed with a severity greater than or equal to the given `severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return not any(issue.severity >= min_severity for issue in self._issues)

    def add_issue(
        self,
        message: str,
        check: RequirementCheck,
        violatingEntity: str | None = None,
        violatingProperty: str | None = None,
        violatingPropertyValue: str | None = None,
    ) -> CheckIssue:
        """
        Add an issue to the validation result

        Parameters:
            message(str): The message of the issue
            check(RequirementCheck): The check that generated the issue
            violatingEntity(Optional[str]): The entity that caused the issue (if any)
            violatingProperty(Optional[str]): The property that caused the issue (if any)
            violatingPropertyValue(Optional[str]): The value of the violatingProperty (if any)
        """
        c = CheckIssue(
            check,
            message,
            violatingProperty=violatingProperty,
            violatingEntity=violatingEntity,
            value=violatingPropertyValue,
        )
        bisect.insort(self._issues, c)
        return c

    #  --- Requirements ---
    @property
    def failed_requirements(self) -> Collection[Requirement]:
        """
        Get the requirements that failed at or above the configured `requirement_severity`.
        """
        min_severity = self.context.requirement_severity
        return {issue.check.requirement for issue in self._issues if issue.severity >= min_severity}

    #  --- Checks ---
    @property
    def failed_checks(self) -> Collection[RequirementCheck]:
        """
        Get the checks that failed at or above the configured `requirement_severity`.
        """
        min_severity = self.context.requirement_severity
        return {issue.check for issue in self._issues if issue.severity >= min_severity}

    def get_failed_checks_by_requirement(self, requirement: Requirement) -> Collection[RequirementCheck]:
        """
        Get the checks that failed for a specific requirement
        """
        return [check for check in self.failed_checks if check.requirement == requirement]

    def get_failed_checks_by_requirement_and_severity(
        self, requirement: Requirement, severity: Severity
    ) -> Collection[RequirementCheck]:
        """
        Get the checks that failed for a specific requirement and severity
        """
        return [
            check for check in self.failed_checks if check.requirement == requirement and check.severity == severity
        ]

    def __str__(self) -> str:
        return f"Validation result: passed={len(self.failed_checks) == 0}, {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(passed={len(self.failed_checks) == 0},issues={self._issues})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationResult):
            raise TypeError(f"Cannot compare ValidationResult with {type(other)}")
        return self._issues == other._issues

    # Equality is based on the mutable list of issues, so instances are
    # intentionally unhashable (a content-based hash would be unstable).
    __hash__ = None  # type: ignore[assignment]

    def to_dict(self) -> dict:
        """
        Convert the ValidationResult to a dictionary
        """
        allowed_properties = [
            "profile_identifier",
            "enable_profile_inheritance",
            "requirement_severity",
            "abort_on_first",
        ]
        validation_settings = {
            key: value for key, value in self.validation_settings.to_dict().items() if key in allowed_properties
        }
        result: dict[str, Any] = {
            "meta": {"version": JSON_OUTPUT_FORMAT_VERSION},
            "validation_settings": validation_settings,
            "passed": self.passed(cast("Severity", self.context.settings.requirement_severity)),
            "issues": [issue.to_dict() for issue in self.issues],
        }
        # add validator version to the settings
        result["validation_settings"]["rocrate_validator_version"] = __version__
        return result

    def to_json(self, path: Path | None = None) -> str:
        """
        Convert the ValidationResult to a JSON string
        """
        result = json.dumps(self.to_dict(), indent=4, cls=CustomEncoder)
        if path:
            with path.open("w", encoding="utf-8") as f:
                f.write(result)
        return result


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, CheckIssue):
            return o.__dict__
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, (RequirementCheck, Requirement)):
            return o.identifier
        if isinstance(o, (Severity, RequirementLevel)):
            return o.name
        return super().default(o)
