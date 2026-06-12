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

from typing import ClassVar

from rocrate_validator.events import Event, EventType, Subscriber
from rocrate_validator.models import (
    ProfileValidationEvent,
    RequirementCheckValidationEvent,
    RequirementValidationEvent,
    ValidationContext,
    ValidationEvent,
)
from rocrate_validator.utils import log as logging

logger = logging.getLogger(__name__)


class EventDispatcher(Subscriber):
    """
    Subscriber that routes validation events to typed ``_on_*`` hooks.

    Hidden requirements and overridden checks (relative to the target
    profile) are filtered out before dispatch, so subclasses only see
    actionable events and don't need to repeat the guard.
    """

    _HANDLERS: ClassVar[dict[EventType, str]] = {
        EventType.VALIDATION_START: "_on_validation_start",
        EventType.PROFILE_VALIDATION_START: "_on_profile_validation_start",
        EventType.REQUIREMENT_VALIDATION_START: "_on_requirement_validation_start",
        EventType.REQUIREMENT_CHECK_VALIDATION_START: "_on_requirement_check_validation_start",
        EventType.REQUIREMENT_CHECK_VALIDATION_END: "_on_requirement_check_validation_end",
        EventType.REQUIREMENT_VALIDATION_END: "_on_requirement_validation_end",
        EventType.PROFILE_VALIDATION_END: "_on_profile_validation_end",
        EventType.VALIDATION_END: "_on_validation_end",
    }

    _CHECK_EVENTS: ClassVar[frozenset[EventType]] = frozenset({
        EventType.REQUIREMENT_CHECK_VALIDATION_START,
        EventType.REQUIREMENT_CHECK_VALIDATION_END,
    })

    _REQUIREMENT_EVENTS: ClassVar[frozenset[EventType]] = frozenset({
        EventType.REQUIREMENT_VALIDATION_START,
        EventType.REQUIREMENT_VALIDATION_END,
    })

    def __init__(self, name: str | None = None):
        super().__init__(name or type(self).__name__)

    def update(self, event: Event, ctx: ValidationContext | None = None) -> None:
        logger.debug("Event: %s", event.event_type)
        if not self._should_dispatch(event, ctx):
            return
        handler_name = self._HANDLERS.get(event.event_type)
        if handler_name is not None:
            getattr(self, handler_name)(event, ctx)

    def _should_dispatch(self, event: Event, ctx: ValidationContext | None) -> bool:
        et = event.event_type
        if et in self._CHECK_EVENTS:
            assert isinstance(event, RequirementCheckValidationEvent)
            if self._is_check_actionable(event, ctx):
                return True
            logger.debug("Skipping check: %s", event.requirement_check.identifier)
            return False
        if et in self._REQUIREMENT_EVENTS:
            assert isinstance(event, RequirementValidationEvent)
            return not event.requirement.hidden
        return True

    def _on_validation_start(self, event: Event, ctx: ValidationContext | None) -> None:
        pass

    def _on_profile_validation_start(self, event: ProfileValidationEvent,
                                     ctx: ValidationContext | None) -> None:
        pass

    def _on_requirement_validation_start(self, event: RequirementValidationEvent,
                                         ctx: ValidationContext | None) -> None:
        pass

    def _on_requirement_check_validation_start(self, event: RequirementCheckValidationEvent,
                                               ctx: ValidationContext | None) -> None:
        pass

    def _on_requirement_check_validation_end(self, event: RequirementCheckValidationEvent,
                                             ctx: ValidationContext | None) -> None:
        pass

    def _on_requirement_validation_end(self, event: RequirementValidationEvent,
                                       ctx: ValidationContext | None) -> None:
        pass

    def _on_profile_validation_end(self, event: ProfileValidationEvent,
                                   ctx: ValidationContext | None) -> None:
        pass

    def _on_validation_end(self, event: ValidationEvent,
                           ctx: ValidationContext | None) -> None:
        pass

    @staticmethod
    def _is_check_actionable(event: RequirementCheckValidationEvent,
                             ctx: ValidationContext | None) -> bool:
        """Return ``True`` if the check is neither hidden nor overridden."""
        assert ctx is not None, "Validation context must be provided"
        if event.requirement_check.requirement.hidden:
            return False
        if event.requirement_check.overridden:
            return (
                ctx.target_validation_profile.identifier
                == event.requirement_check.requirement.profile.identifier
            )
        return True
