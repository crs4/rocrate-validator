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

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:
    from rocrate_validator.models.requirement import RequirementCheck
    from rocrate_validator.models.validation import ValidationContext


@unique
class SkipCategory(str, Enum):
    """Reason category for a skipped requirement check."""

    _description: str

    RETURNED = ("returned", "The check returned SKIPPED without another skip reason.")
    CONFIGURED = ("configured", "The check was skipped by validation settings.")
    EXCEPTION = ("exception", "The check was skipped because an exception prevented validation.")
    DEACTIVATED = ("deactivated", "The check is deactivated in the profile.")
    DEPENDENCY = ("dependency", "The check was skipped because a dependency did not pass.")
    NOT_REACHED = ("not_reached", "The check was not reached because validation stopped earlier.")
    INHERITED = ("inherited", "The check belongs to an inherited profile that was not reported or run.")

    def __new__(cls, value: str, description: str):
        member = str.__new__(cls, value)
        member._value_ = value
        member._description = description
        return member

    @property
    def description(self) -> str:
        """Human-readable explanation of this category."""
        return self._description


SkipCategoryInput: TypeAlias = (
    SkipCategory
    | Literal[
        "returned",
        "configured",
        "exception",
        "deactivated",
        "dependency",
        "not_reached",
        "inherited",
    ]
)


class SkipRequirementCheck(Exception):
    """Signal that a requirement check should be skipped."""

    def __init__(
        self,
        check: RequirementCheck,
        message: str = "",
        category: SkipCategoryInput = SkipCategory.RETURNED,
    ):
        self.check = check
        self.message = message
        self.category = SkipCategory(category)

    def __str__(self) -> str:
        return f"SkipRequirementCheck(check={self.check})"


@dataclass(frozen=True)
class SkippedCheckDetail:
    """Structured information explaining why a check was skipped."""

    check: RequirementCheck
    message: str
    category: SkipCategory = SkipCategory.RETURNED
    context: ValidationContext | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", SkipCategory(self.category))

    def to_dict(self) -> dict[str, str]:
        source_identifier = self.check.identifier
        source_profile = self.check.requirement.profile.identifier
        identifier = self.context.effective_check_identifier(self.check) if self.context else source_identifier
        profile = self.context.effective_check_profile(self.check).identifier if self.context else source_profile
        result = {
            "identifier": identifier,
            "profile": profile,
            "requirement": self.check.requirement.name,
            "name": self.check.name,
            "severity": self.check.severity.name,
            "message": self.message,
            "category": self.category.value,
        }
        if identifier != source_identifier or profile != source_profile:
            result["source_identifier"] = source_identifier
            result["source_profile"] = source_profile
        return result
