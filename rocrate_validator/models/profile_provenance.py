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

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rocrate_validator.models.profile import Profile
    from rocrate_validator.models.requirement import RequirementCheck


class RequirementCheckRelation(Enum):
    """How a requirement check became part of an effective profile."""

    DEFINED_LOCALLY = "defined_locally"
    INHERITED = "inherited"
    REPLACES = "replaces"


@dataclass(frozen=True)
class EffectiveRequirementCheck:
    """
    A requirement check as exposed by a specific validation profile.

    The source check is never mutated. ``identifier`` and ``profile`` are the
    identity under which the check is reported by the effective profile, while
    the ``source_*`` properties retain the implementation provenance.
    """

    check: RequirementCheck
    identifier: str
    profile: Profile
    relation: RequirementCheckRelation
    replaces: tuple[RequirementCheck, ...] = ()

    @property
    def source_identifier(self) -> str:
        return self.check.identifier

    @property
    def source_profile(self) -> Profile:
        return self.check.requirement.profile

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the effective check."""
        return {
            "identifier": self.identifier,
            "profile": self.profile.identifier,
            "source_identifier": self.source_identifier,
            "source_profile": self.source_profile.identifier,
            "relation": self.relation.value,
            "replaces": [check.identifier for check in self.replaces],
        }
