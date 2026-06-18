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

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol, cast

from rocrate_validator.events import Event, EventType, Subscriber
from rocrate_validator.models._logging import logger
from rocrate_validator.models.events import (
    ProfileValidationEvent,
    RequirementCheckValidationEvent,
    RequirementValidationEvent,
    ValidationEvent,
)
from rocrate_validator.models.profile import Profile
from rocrate_validator.models.settings import ValidationSettings
from rocrate_validator.models.severity import (
    LevelCollection,
    Severity,
)

if TYPE_CHECKING:
    from rocrate_validator.models.requirement import (
        Requirement,
        RequirementCheck,
    )
    from rocrate_validator.models.result import ValidationResult
    from rocrate_validator.models.validation import ValidationContext


class ValidationStatisticsListener(Protocol):
    """
    Protocol for listeners interested in validation statistics updates.
    """

    def on_statistics_updated(self, statistics: ValidationStatistics):
        logger.debug("Statistics updated: %r", statistics.statistics)


class ValidationStatistics(Subscriber):
    """
    Computes and stores statistical metrics about the RO-Crate validation process.
    """

    def __init__(
        self,
        settings: dict | ValidationSettings,
        context: ValidationContext | None = None,
        skip_initialization: bool = False,
    ):
        super().__init__(name=self.__class__.__name__)
        if isinstance(settings, dict):
            settings = ValidationSettings.parse(settings)
        self._settings = settings
        self._context = context
        self._stats = self.__initialise__(settings) if not skip_initialization else {}
        self._result: ValidationResult | None = None
        self._listeners: list[ValidationStatisticsListener] = []

    @property
    def validation_settings(self) -> ValidationSettings:
        """
        Get the validation settings used for statistics computation
        """
        return self._settings

    @property
    def validation_result(self) -> ValidationResult | None:
        """
        Get the validation result
        """
        return self._result

    def add_listener(self, listener: ValidationStatisticsListener):
        """
        Add a listener to be notified on statistics updates
        """
        self._listeners.append(listener)
        logger.debug("Listener added: %r", listener)

    def notify_listeners(self):
        """
        Notify all registered listeners about statistics updates
        """
        for listener in self._listeners:
            listener.on_statistics_updated(self)
            logger.debug("Notified listener: %r", listener)

    @property
    def statistics(self) -> dict:
        """
        Get the computed validation statistics
        """
        return self._stats.copy()

    @property
    def profile(self) -> Profile:
        """
        Get the profile being validated
        """
        return cast("Profile", self._stats.get("profile"))

    @property
    def profiles(self) -> list[Profile]:
        """
        Get all profiles involved in validation
        """
        return self._stats.get("profiles", [])

    @property
    def severity(self) -> Severity:
        """
        Get the validation severity level
        """
        return cast("Severity", self._stats.get("severity"))

    @property
    def checks_by_severity(self) -> dict:
        """
        Get the checks grouped by severity
        """
        return self._stats.get("checks_by_severity", {})

    @property
    def check_count_by_severity(self) -> dict:
        """
        Get the count of checks grouped by severity
        """
        return {k: len(v) for k, v in self._stats.get("checks_by_severity", {}).items()}

    @property
    def requirements(self) -> list[Requirement]:
        """
        Get all requirements being validated
        """
        return self._stats.get("requirements", [])

    @property
    def passed_requirements(self) -> list[Requirement]:
        """
        Get the list of passed requirements
        """
        return self._stats.get("passed_requirements", [])

    @property
    def failed_requirements(self) -> list[Requirement]:
        """
        Get the list of failed requirements
        """
        return self._stats.get("failed_requirements", [])

    @property
    def total_requirements(self) -> int:
        """
        Get the total number of requirements
        """
        return len(self._stats.get("requirements", []))

    @property
    def checks(self) -> list[RequirementCheck]:
        """
        Get all checks being validated
        """
        return self._stats.get("checks", [])

    @property
    def passed_checks(self) -> list[RequirementCheck]:
        """
        Get the list of passed checks
        """
        return self._stats.get("passed_checks", [])

    @property
    def failed_checks(self) -> list[RequirementCheck]:
        """
        Get the list of failed checks
        """
        return self._stats.get("failed_checks", [])

    @property
    def total_checks(self) -> int:
        """
        Get the total number of checks
        """
        return len(self._stats.get("checks", []))

    @property
    def validated_profiles(self) -> list[Profile]:
        """
        Get the list of validated profiles
        """
        return self._stats.get("validated_profiles", [])

    @property
    def validated_requirements(self) -> list[Requirement]:
        """
        Get the list of validated requirements
        """
        return self._stats.get("validated_requirements", [])

    @property
    def validated_checks(self) -> list[RequirementCheck]:
        """
        Get the list of validated checks
        """
        return self._stats.get("validated_checks", [])

    @property
    def started_at(self) -> datetime | None:
        """
        Get the timestamp when validation started
        """
        return self._stats.get("started_at")

    @property
    def finished_at(self) -> datetime | None:
        """
        Get the timestamp when validation finished
        """
        return self._stats.get("finished_at")

    @property
    def duration(self) -> float | None:
        """
        Get the duration of the validation process in seconds
        """
        started_at = self.started_at
        finished_at = self.finished_at
        if started_at and finished_at:
            return (finished_at - started_at).total_seconds()
        return None

    @staticmethod
    def __collect_requirement_checks__(
        requirement,
        severity_validation,
        validation_settings,
        target_profile_identifier,
        checks,
        checks_by_severity,
    ) -> int:
        """Count and register a requirement's checks across severities >= the requested one."""
        requirement_checks_count = 0
        for severity in (
            Severity.REQUIRED,
            Severity.RECOMMENDED,
            Severity.OPTIONAL,
        ):
            logger.debug(f"Checking requirement: {requirement} severity: {severity} {severity < severity_validation}")
            # skip requirements with lower severity
            if severity < severity_validation:
                continue
            # count the checks
            requirement_checks = [
                _
                for _ in requirement.get_checks_by_level(LevelCollection.get(severity.name))
                if (not validation_settings.skip_checks or _.identifier not in validation_settings.skip_checks)
                and (not _.overridden or _.requirement.profile.identifier == target_profile_identifier)
            ]
            num_checks = len(requirement_checks)
            requirement_checks_count += num_checks
            if num_checks > 0:
                logger.debug(f"Requirement: {requirement} has {num_checks} checks of severity: {severity}")
                checks.update(requirement_checks)
                checks_by_severity[severity].update(requirement_checks)
        return requirement_checks_count

    @classmethod
    def __initialise__(cls, validation_settings: ValidationSettings):
        """
        Compute the statistics of the profile
        """
        # extract the validation settings
        severity_validation = validation_settings.requirement_severity
        profiles: list[Profile] = Profile.load_profiles(
            validation_settings.profiles_path,
            extra_profiles_path=validation_settings.extra_profiles_path,
            severity=cast("Severity", severity_validation),
            allow_requirement_check_override=validation_settings.allow_requirement_check_override,
        )
        profile: Profile = cast("Profile", Profile.find_in_list(profiles, validation_settings.profile_identifier))
        target_profile_identifier = profile.identifier
        # initialize the profiles list
        profiles = [profile]

        # add inherited profiles if enabled
        if not validation_settings.disable_inherited_profiles_issue_reporting:
            profiles.extend(profile.inherited_profiles)
        logger.debug("Inherited profiles: %r", profile.inherited_profiles)

        # Initialize the counters
        checks_by_severity: dict[Severity, set[RequirementCheck]] = {}
        checks: set[RequirementCheck] = set()
        requirements: set[Requirement] = set()

        # Initialize the counters
        for severity in (
            Severity.REQUIRED,
            Severity.RECOMMENDED,
            Severity.OPTIONAL,
        ):
            checks_by_severity[severity] = set()

        # Process the requirements and checks
        processed_requirements = []
        for profile in profiles:
            for requirement in profile.requirements:
                if requirement in processed_requirements:
                    continue
                processed_requirements.append(requirement)
                if requirement.hidden:
                    continue

                requirement_checks_count = cls.__collect_requirement_checks__(
                    requirement,
                    severity_validation,
                    validation_settings,
                    target_profile_identifier,
                    checks,
                    checks_by_severity,
                )

                # count the requirements and checks
                if requirement_checks_count == 0:
                    logger.debug(f"No checks for requirement: {requirement}")
                else:
                    # Only if there are checks for the requirement count it
                    logger.debug(f"Requirement: {requirement} checks count: {requirement_checks_count}")
                    assert not requirement.hidden, "Hidden requirements should not be counted"
                    # add the requirement to the list
                    requirements.add(requirement)

        # log processed requirements
        logger.debug(
            "Processed requirements %r: %r",
            len(processed_requirements),
            processed_requirements,
        )

        # Prepare the result
        result = {
            "profile": profile,
            "profiles": profiles,
            "requirements": requirements,
            "checks": checks,
            "severity": severity_validation,
            "checks_by_severity": checks_by_severity,
            "failed_requirements": [],
            "failed_checks": [],
            "passed_requirements": [],
            "passed_checks": [],
            "started_at": None,
            "finished_at": None,
            "validated_profiles": [],
            "validated_requirements": [],
            "validated_checks": [],
        }
        logger.debug(result)
        return result

    def update(self, event: Event, ctx: ValidationContext | None = None) -> None:
        self.__event_handlers__.get(event.event_type, lambda e, c: None)(event, ctx)

    def __handle_validation_start__(self, _event: Event, _ctx: ValidationContext | None) -> None:
        logger.debug("Validation started")
        self._stats["started_at"] = datetime.now(timezone.utc)

    def __handle_profile_validation_start__(self, event: Event, _ctx: ValidationContext | None) -> None:
        assert isinstance(event, ProfileValidationEvent)
        logger.debug("Profile validation start: %s", event.profile.identifier)

    def __handle_requirement_validation_start__(self, _event: Event, _ctx: ValidationContext | None) -> None:
        logger.debug("Requirement validation start")

    def __handle_requirement_check_validation_start__(self, _event: Event, _ctx: ValidationContext | None) -> None:
        logger.debug("Requirement check validation start")

    def __handle_requirement_check_validation_end__(self, event: Event, ctx: ValidationContext | None) -> None:
        assert isinstance(event, RequirementCheckValidationEvent)
        assert ctx is not None
        target_profile = ctx.target_validation_profile
        if not event.requirement_check.requirement.hidden and (
            not event.requirement_check.overridden
            or target_profile.identifier == event.requirement_check.requirement.profile.identifier
        ):
            if event.validation_result is not None:
                if event.validation_result:
                    self._stats["passed_checks"].append(event.requirement_check)
                else:
                    self._stats["failed_checks"].append(event.requirement_check)
                self._stats["validated_checks"].append(event.requirement_check)
                self.notify_listeners()
            else:
                logger.debug(
                    "Requirement check validation result is None: %s",
                    event.requirement_check.identifier,
                )
        else:
            logger.debug(
                "Skipping requirement check validation: %s",
                event.requirement_check.identifier,
            )

    def __handle_requirement_validation_end__(self, event: Event, _ctx: ValidationContext | None) -> None:
        assert isinstance(event, RequirementValidationEvent)
        if not event.requirement.hidden:
            if event.validation_result:
                self._stats["passed_requirements"].append(event.requirement)
            else:
                self._stats["failed_requirements"].append(event.requirement)
            self._stats["validated_requirements"].append(event.requirement)
            self.notify_listeners()

    def __handle_profile_validation_end__(self, event: Event, _ctx: ValidationContext | None) -> None:
        assert isinstance(event, ProfileValidationEvent)
        self._stats["validated_profiles"].append(event.profile)
        logger.debug("Profile validation ended: %s", event.profile.identifier)

    def __handle_validation_end__(self, event: Event, _ctx: ValidationContext | None) -> None:
        assert isinstance(event, ValidationEvent)
        self._result = event.validation_result
        self._stats["finished_at"] = datetime.now(timezone.utc)
        logger.debug("Validation ended with result: %s", event.validation_result)

    @property
    def __event_handlers__(self):
        return {
            EventType.VALIDATION_START: self.__handle_validation_start__,
            EventType.PROFILE_VALIDATION_START: self.__handle_profile_validation_start__,
            EventType.REQUIREMENT_VALIDATION_START: self.__handle_requirement_validation_start__,
            EventType.REQUIREMENT_CHECK_VALIDATION_START: self.__handle_requirement_check_validation_start__,
            EventType.REQUIREMENT_CHECK_VALIDATION_END: self.__handle_requirement_check_validation_end__,
            EventType.REQUIREMENT_VALIDATION_END: self.__handle_requirement_validation_end__,
            EventType.PROFILE_VALIDATION_END: self.__handle_profile_validation_end__,
            EventType.VALIDATION_END: self.__handle_validation_end__,
        }

    def to_dict(self) -> dict:
        """
        Get the computed validation statistics as a dictionary
        """
        return {
            # Execution time details
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration": self.duration,
            # Profile details
            "profile": self.profile.identifier if self.profile else None,
            "profiles": [p.identifier for p in self.profiles],
            "severity": self.severity.name if self.severity else None,
            # Computed totals
            "total_requirements": self.total_requirements,
            "total_passed_requirements": len(self.passed_requirements),
            "total_failed_requirements": len(self.failed_requirements),
            "total_checks": self.total_checks,
            "total_passed_checks": len(self.passed_checks),
            "total_failed_checks": len(self.failed_checks),
            "total_checks_by_severity": {k.name: len(v) for k, v in self.checks_by_severity.items()},
            # Requirements involved
            "requirements": {
                "count": self.total_requirements,
                "passed": {
                    "count": len(self.passed_requirements),
                    "percentage": (
                        (len(self.passed_requirements) / self.total_requirements * 100)
                        if self.total_requirements > 0
                        else 0.0
                    ),
                    "identifiers": sorted([r.identifier for r in self.passed_requirements]),
                },
                "failed": {
                    "count": len(self.failed_requirements),
                    "percentage": (
                        (len(self.failed_requirements) / self.total_requirements * 100)
                        if self.total_requirements > 0
                        else 0.0
                    ),
                    "identifiers": sorted([r.identifier for r in self.failed_requirements]),
                },
                "identifiers": sorted([r.identifier for r in self.requirements]),
            },
            # Checks involved
            "checks": {
                "count": self.total_checks,
                "passed": {
                    "count": len(self.passed_checks),
                    "percentage": (len(self.passed_checks) / self.total_checks * 100) if self.total_checks > 0 else 0.0,
                    "identifiers": sorted([c.identifier for c in self.passed_checks]),
                },
                "failed": {
                    "count": len(self.failed_checks),
                    "percentage": (len(self.failed_checks) / self.total_checks * 100) if self.total_checks > 0 else 0.0,
                    "identifiers": sorted([c.identifier for c in self.failed_checks]),
                },
                "identifiers": sorted([c.identifier for c in self.checks]),
                "by_severity": {k.name: len(v) for k, v in self._stats.get("checks_by_severity", {}).items()},
            },
        }

    def to_json(self) -> str:
        """
        Get the computed validation statistics as a JSON string
        """
        from rocrate_validator.models.result import CustomEncoder  # noqa: PLC0415

        return json.dumps(self.to_dict(), indent=4, cls=CustomEncoder)


class AggregatedValidationStatistics:
    """
    Represents aggregated validation statistics from multiple validation runs.
    """

    def __init__(self, statistics_list: list[ValidationStatistics]):
        if not statistics_list:
            raise ValueError("statistics_list cannot be empty")
        # Store the individual statistics
        self._statistics_list = statistics_list

        # Aggregate the statistics
        self._overall_stats = self.__compute_averall_stats__()

    @property
    def individual_statistics(self) -> list[ValidationStatistics]:
        """
        Get the individual validation statistics
        """
        return self._statistics_list

    def to_dict(self) -> dict:
        """
        Get the overall aggregated statistics as a dictionary
        """
        return {
            # Execution time details
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration": self.duration,
            # Profiles involved
            "profiles": [p.identifier for p in self.profiles],
            # Computed totals
            "total_requirements": self.total_requirements,
            "total_passed_requirements": len(self.passed_requirements),
            "total_failed_requirements": len(self.failed_requirements),
            "total_checks": self.total_checks,
            "total_passed_checks": len(self.passed_checks),
            "total_failed_checks": len(self.failed_checks),
            "total_checks_by_severity": {k.name: len(v) for k, v in self.checks_by_severity.items()},
            # Requirements involved
            "requirements": {
                "count": self.total_requirements,
                "passed": {
                    "count": len(self.passed_requirements),
                    "percentage": (
                        (len(self.passed_requirements) / self.total_requirements * 100)
                        if self.total_requirements > 0
                        else 0.0
                    ),
                    "identifiers": [r.identifier for r in self.passed_requirements],
                },
                "failed": {
                    "count": len(self.failed_requirements),
                    "percentage": (
                        (len(self.failed_requirements) / self.total_requirements * 100)
                        if self.total_requirements > 0
                        else 0.0
                    ),
                    "identifiers": [r.identifier for r in self.failed_requirements],
                },
                "identifiers": [r.identifier for r in self.requirements],
            },
            # Checks involved
            "checks": {
                "count": self.total_checks,
                "passed": {
                    "count": len(self.passed_checks),
                    "percentage": (len(self.passed_checks) / self.total_checks * 100) if self.total_checks > 0 else 0.0,
                    "identifiers": [c.identifier for c in self.passed_checks],
                },
                "failed": {
                    "count": len(self.failed_checks),
                    "percentage": (len(self.failed_checks) / self.total_checks * 100) if self.total_checks > 0 else 0.0,
                    "identifiers": [c.identifier for c in self.failed_checks],
                },
                "identifiers": [c.identifier for c in self.checks],
            },
        }

    @property
    def profiles(self) -> set[Profile]:
        """
        Get the set of profiles involved in the aggregated validation
        """
        return self._overall_stats.get("profiles", set())

    @property
    def total_profiles(self) -> int:
        """
        Get the total number of profiles involved in the aggregated validation
        """
        return len(self._overall_stats.get("profiles", set()))

    @property
    def requirements(self) -> set[Requirement]:
        """
        Get the set of requirements in the aggregated validation
        """
        return self._overall_stats.get("requirements", set())

    @property
    def passed_requirements(self) -> set[Requirement]:
        """
        Get the set of passed requirements in the aggregated validation
        """
        return self._overall_stats.get("passed_requirements", set())

    @property
    def failed_requirements(self) -> set[Requirement]:
        """
        Get the set of failed requirements in the aggregated validation
        """
        return self._overall_stats.get("failed_requirements", set())

    @property
    def total_requirements(self) -> int:
        """
        Get the total number of requirements in the aggregated validation
        """
        return len(self._overall_stats.get("requirements", set()))

    @property
    def checks(self) -> set[RequirementCheck]:
        """
        Get the set of checks in the aggregated validation
        """
        return self._overall_stats.get("checks", set())

    @property
    def checks_by_severity(self) -> dict:
        """
        Get the checks grouped by severity in the aggregated validation
        """
        return self._overall_stats.get("checks_by_severity", {})

    @property
    def total_checks(self) -> int:
        """
        Get the total number of checks in the aggregated validation
        """
        return len(self._overall_stats.get("checks", set()))

    @property
    def passed_checks(self) -> set[RequirementCheck]:
        """
        Get the set of passed checks in the aggregated validation
        """
        return self._overall_stats.get("passed_checks", set())

    @property
    def failed_checks(self) -> set[RequirementCheck]:
        """
        Get the set of failed checks in the aggregated validation
        """
        return self._overall_stats.get("failed_checks", set())

    @property
    def started_at(self) -> datetime | None:
        """
        Get the timestamp when the aggregated validation started
        """
        return self._overall_stats.get("started_at")

    @property
    def finished_at(self) -> datetime | None:
        """
        Get the timestamp when the aggregated validation finished
        """
        return self._overall_stats.get("finished_at")

    @property
    def duration(self) -> float:
        """
        Get the total duration of the aggregated validation in seconds
        """
        return self._overall_stats.get("duration", 0.0)

    def __compute_averall_stats__(self):
        """
        Compute the overall aggregated statistics
        """
        raw_stats = self.__aggregate_raw_stats__(self._statistics_list)
        return self.__build_sorted_stats_dict__(raw_stats)

    @classmethod
    def __aggregate_raw_stats__(
        cls,
        statistics_list: list[ValidationStatistics],
    ):
        """
        Aggregate raw (unsorted) statistics from a list of ValidationStatistics instances.
        """
        profiles: set[Profile] = set()
        requirements: set[Requirement] = set()
        checks: set[RequirementCheck] = set()
        checks_by_severity: dict[Severity, set[RequirementCheck]] = {}
        failed_requirements: set[Requirement] = set()
        failed_checks: set[RequirementCheck] = set()
        passed_requirements: set[Requirement] = set()
        passed_checks: set[RequirementCheck] = set()
        started_at: datetime | None = None
        finished_at: datetime | None = None
        duration: float = 0.0

        # Aggregate statistics from each ValidationStatistics instance
        for stats in statistics_list:
            # Aggregate profiles
            for profile in stats.profiles:
                profiles.add(profile)

            # Aggregate total requirements and checks
            requirements.update(stats.requirements)
            checks.update(stats.checks)
            checks_by_severity.update(stats.checks_by_severity)

            # Aggregate failed and passed requirements and checks
            failed_requirements.update(stats.failed_requirements)
            failed_checks.update(stats.failed_checks)
            passed_requirements.update(stats.passed_requirements)
            passed_checks.update(stats.passed_checks)

            # Aggregate started_at and finished_at
            if started_at is not None and stats.started_at is not None:
                started_at = min(started_at, stats.started_at)
            elif stats.started_at is not None:
                started_at = stats.started_at
            if finished_at is not None and stats.finished_at is not None:
                finished_at = max(finished_at, stats.finished_at)
            elif stats.finished_at is not None:
                finished_at = stats.finished_at
            # Aggregate duration
            duration += stats.duration or 0.0

        return {
            "profiles": profiles,
            "requirements": requirements,
            "checks": checks,
            "checks_by_severity": checks_by_severity,
            "failed_requirements": failed_requirements,
            "failed_checks": failed_checks,
            "passed_requirements": passed_requirements,
            "passed_checks": passed_checks,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration": duration,
        }

    @classmethod
    def __build_sorted_stats_dict__(cls, raw_stats):
        """
        Sort the raw aggregated sets and build the final sorted statistics dict.
        """
        sorted_checks_by_severity = {}
        for severity_key, severity_checks in raw_stats["checks_by_severity"].items():
            sorted_checks_by_severity[severity_key] = sorted(severity_checks, key=lambda c: c.identifier)

        return {
            "profiles": sorted(raw_stats["profiles"], key=lambda p: p.identifier),
            "requirements": sorted(raw_stats["requirements"], key=lambda r: r.identifier),
            "checks": sorted(raw_stats["checks"], key=lambda c: c.identifier),
            "checks_by_severity": sorted_checks_by_severity,
            "failed_requirements": sorted(raw_stats["failed_requirements"], key=lambda r: r.identifier),
            "failed_checks": sorted(raw_stats["failed_checks"], key=lambda c: c.identifier),
            "passed_requirements": sorted(raw_stats["passed_requirements"], key=lambda r: r.identifier),
            "passed_checks": sorted(raw_stats["passed_checks"], key=lambda c: c.identifier),
            "started_at": raw_stats["started_at"],
            "finished_at": raw_stats["finished_at"],
            "duration": raw_stats["duration"],
        }
