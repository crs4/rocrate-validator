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

from typing import TYPE_CHECKING

from rocrate_validator.events import Event, EventType

if TYPE_CHECKING:
    from rocrate_validator.models.profile import Profile
    from rocrate_validator.models.requirement import Requirement, RequirementCheck
    from rocrate_validator.models.result import ValidationResult


class ValidationEvent(Event):
    def __init__(
        self,
        event_type: EventType,
        validation_result: ValidationResult | None = None,
        message: str | None = None,
    ):
        super().__init__(event_type, message)
        self._validation_result = validation_result

    @property
    def validation_result(self) -> ValidationResult | None:
        return self._validation_result


class ProfileValidationEvent(Event):
    def __init__(
        self,
        event_type: EventType,
        profile: Profile,
        message: str | None = None,
    ):
        assert event_type in (
            EventType.PROFILE_VALIDATION_START,
            EventType.PROFILE_VALIDATION_END,
        )
        super().__init__(event_type, message)
        self._profile = profile

    @property
    def profile(self) -> Profile:
        return self._profile

    def __str__(self) -> str:
        return f"ProfileValidationEvent({self.event_type}, {self.profile})"

    def __repr__(self) -> str:
        return f"ProfileValidationEvent(event_type={self.event_type}, profile={self.profile})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfileValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.profile == other.profile

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.profile))


class RequirementValidationEvent(Event):
    def __init__(
        self,
        event_type: EventType,
        requirement: Requirement,
        validation_result: bool | None = None,
        message: str | None = None,
    ):
        assert event_type in (
            EventType.REQUIREMENT_VALIDATION_START,
            EventType.REQUIREMENT_VALIDATION_END,
        )
        super().__init__(event_type, message)
        self._requirement = requirement
        self._validation_result = validation_result

    @property
    def requirement(self) -> Requirement:
        return self._requirement

    @property
    def validation_result(self) -> bool | None:
        return self._validation_result

    def __str__(self) -> str:
        return f"RequirementValidationEvent({self.event_type}, {self.requirement})"

    def __repr__(self) -> str:
        return f"RequirementValidationEvent(event_type={self.event_type}, requirement={self.requirement})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.requirement == other.requirement

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.requirement))


class RequirementCheckValidationEvent(Event):
    def __init__(
        self,
        event_type: EventType,
        requirement_check: RequirementCheck,
        validation_result: bool | None = None,
        message: str | None = None,
    ):
        assert event_type in (
            EventType.REQUIREMENT_CHECK_VALIDATION_START,
            EventType.REQUIREMENT_CHECK_VALIDATION_END,
        )
        super().__init__(event_type, message)
        self._requirement_check = requirement_check
        self._validation_result = validation_result

    @property
    def requirement_check(self) -> RequirementCheck:
        return self._requirement_check

    @property
    def validation_result(self) -> bool | None:
        return self._validation_result

    def __str__(self) -> str:
        return f"RequirementCheckValidationEvent({self.event_type}, {self.requirement_check})"

    def __repr__(self) -> str:
        return (
            f"RequirementCheckValidationEvent(event_type={self.event_type}, requirement_check={self.requirement_check})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheckValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.requirement_check == other.requirement_check

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.requirement_check))
