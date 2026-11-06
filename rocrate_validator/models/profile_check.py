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

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rocrate_validator.models.profile import Profile
    from rocrate_validator.models.severity import Severity


@dataclass(frozen=True)
class ProfileCheckResult:
    """Structured result produced by a profile consistency check."""

    check_id: str
    profile_identifier: str
    passed: bool
    message: str
    details: Mapping[str, str] = field(default_factory=dict)


class ProfileCheckFailure(Exception):
    """Raised when a profile consistency check does not pass."""

    def __init__(self, result: ProfileCheckResult):
        self.result = result
        super().__init__(result.message)


class ProfileCheck(ABC):
    """Base class for checks validating a profile definition."""

    identifier: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def run(self, profile: Profile) -> ProfileCheckResult:
        """Run this check against ``profile``."""


class UniqueRequirementCheckIdentity(ProfileCheck):
    """Ensure ``(name, severity)`` identifies at most one check per profile."""

    identifier = "unique-requirement-check-identity"
    description = "Requirement check names and severities must be unique within a profile"

    def run(self, profile: Profile) -> ProfileCheckResult:
        seen: set[tuple[str, Severity]] = set()
        for requirement in profile.requirements:
            for check in requirement.get_checks():
                identity = (check.name, check.severity)
                if identity in seen:
                    return ProfileCheckResult(
                        check_id=self.identifier,
                        profile_identifier=profile.identifier,
                        passed=False,
                        message="Duplicate requirement check identity",
                        details={
                            "name": check.name,
                            "severity": check.severity.name,
                        },
                    )
                seen.add(identity)
        return ProfileCheckResult(
            check_id=self.identifier,
            profile_identifier=profile.identifier,
            passed=True,
            message="All requirement check identities are unique",
        )


class RuleOverlayConsistency(ProfileCheck):
    """Ensure rule overlay sources can be composed without ambiguity."""

    identifier = "rule-overlay-consistency"
    description = "Rule overlay sources must be loaded direct parents with distinct check identities"

    def run(self, profile: Profile) -> ProfileCheckResult:
        sources = profile.is_rule_overlay_of
        if not sources:
            return ProfileCheckResult(
                check_id=self.identifier,
                profile_identifier=profile.identifier,
                passed=True,
                message="Profile does not declare rule overlay sources",
            )

        declared_parent_uris = set(profile.is_profile_of)
        loaded_parents = {parent.uri: parent for parent in profile.parents}
        for source_uri in sources:
            if source_uri not in declared_parent_uris:
                return ProfileCheckResult(
                    check_id=self.identifier,
                    profile_identifier=profile.identifier,
                    passed=False,
                    message="Rule overlay source is not a direct parent",
                    details={"source": source_uri},
                )
            if source_uri not in loaded_parents:
                return ProfileCheckResult(
                    check_id=self.identifier,
                    profile_identifier=profile.identifier,
                    passed=False,
                    message="Rule overlay source profile is not loaded",
                    details={"source": source_uri},
                )

        identities: dict[tuple[str, Severity], str] = {}
        for source_uri in sources:
            source_profile = loaded_parents[source_uri]
            for requirement in source_profile.requirements:
                for check in requirement.get_checks():
                    identity = (check.name, check.severity)
                    previous_source = identities.get(identity)
                    if previous_source is not None and previous_source != source_uri:
                        return ProfileCheckResult(
                            check_id=self.identifier,
                            profile_identifier=profile.identifier,
                            passed=False,
                            message="Rule overlay sources contain an ambiguous check identity",
                            details={
                                "name": check.name,
                                "severity": check.severity.name,
                                "sources": f"{previous_source}, {source_uri}",
                            },
                        )
                    identities[identity] = source_uri

        return ProfileCheckResult(
            check_id=self.identifier,
            profile_identifier=profile.identifier,
            passed=True,
            message="Rule overlay sources are consistent",
        )


class NoRequirementCheckOverrides(ProfileCheck):
    """Ensure a profile does not replace checks defined by direct parents."""

    identifier = "no-requirement-check-overrides"
    description = "Requirement check overrides must not be present"

    def run(self, profile: Profile) -> ProfileCheckResult:
        for requirement in profile.requirements:
            for check in requirement.get_checks():
                overridden_checks = check.overrides
                if overridden_checks:
                    return ProfileCheckResult(
                        check_id=self.identifier,
                        profile_identifier=profile.identifier,
                        passed=False,
                        message="Requirement check override is disabled",
                        details={
                            "name": check.name,
                            "severity": check.severity.name,
                            "sources": ", ".join(
                                overridden.requirement.profile.identifier for overridden in overridden_checks
                            ),
                        },
                    )
        return ProfileCheckResult(
            check_id=self.identifier,
            profile_identifier=profile.identifier,
            passed=True,
            message="No requirement check overrides found",
        )


class ProfileCheckSuite:
    """Run the registered consistency checks for a profile."""

    DEFAULT_CHECKS: ClassVar[tuple[type[ProfileCheck], ...]] = (
        UniqueRequirementCheckIdentity,
        RuleOverlayConsistency,
    )

    def __init__(self, checks: tuple[type[ProfileCheck], ...] | None = None):
        selected_checks = checks if checks is not None else self.DEFAULT_CHECKS
        self._checks = tuple(check() for check in selected_checks)

    def run(self, profile: Profile) -> tuple[ProfileCheckResult, ...]:
        """Return one result for every registered profile check."""
        return tuple(check.run(profile) for check in self._checks)
