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

import enum
import inspect
from dataclasses import dataclass
from functools import total_ordering

from enum_tools.documentation import document_enum


@enum.unique
@document_enum
@total_ordering
class Severity(enum.Enum):
    """
    Enum ordering "strength" of conditions to be verified
    """

    #: the condition is not mandatory
    OPTIONAL = 0
    #: the condition is recommended
    RECOMMENDED = 2
    #: the condition is mandatory
    REQUIRED = 4

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self.value < other.value
        raise TypeError(f"Comparison not supported between instances of {type(self)} and {type(other)}")

    @staticmethod
    def get(name: str) -> Severity:
        return getattr(Severity, name.upper())


@total_ordering
@dataclass
class RequirementLevel:
    """
    Represents a requirement level.

    A requirement has a name and a severity level of type :class:`.Severity`.
    It implements the comparison operators to allow ordering of the requirement levels.
    """

    name: str
    severity: Severity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementLevel):
            return False
        return self.name == other.name and self.severity == other.severity

    def __lt__(self, other: object) -> bool:
        # NOTE: this ordering is not totally coherent, since for two objects a and b
        # with equal Severity but different names you would have
        #       not a < b, which implies a >= b
        #       and also a != b and not a > b, which is incoherent with a >= b
        if not isinstance(other, RequirementLevel):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.severity < other.severity

    def __hash__(self) -> int:
        return hash((self.name, self.severity))

    def __repr__(self) -> str:
        return f"RequirementLevel(name={self.name}, severity={self.severity})"

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.severity.value

    def __index__(self) -> int:
        return self.severity.value


class LevelCollection:
    """
    Collection of :class:`.RequirementLevel` instances.

    Provides a set of predefined RequirementLevel instances
    that can be used to define the severity of a requirement.
    They map the keywords defined in **RFC 2119** to the corresponding severity levels.

    .. note::
        The keywords **MUST**, **MUST NOT**, **REQUIRED**,
        **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**,
        **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document
        are to be interpreted as described in **RFC 2119**.

    """

    #: The requirement level OPTIONAL is mapped to the OPTIONAL severity level
    OPTIONAL = RequirementLevel("OPTIONAL", Severity.OPTIONAL)
    #: The requirement level MAY is mapped to the OPTIONAL severity level
    MAY = RequirementLevel("MAY", Severity.OPTIONAL)
    #: The requirement level REQUIRED is mapped to the REQUIRED severity level
    REQUIRED = RequirementLevel("REQUIRED", Severity.REQUIRED)
    #: The requirement level SHOULD is mapped to the RECOMMENDED severity level
    SHOULD = RequirementLevel("SHOULD", Severity.RECOMMENDED)
    #: The requirement level SHOULD NOT is mapped to the RECOMMENDED severity level
    SHOULD_NOT = RequirementLevel("SHOULD_NOT", Severity.RECOMMENDED)
    #: The requirement level RECOMMENDED is mapped to the RECOMMENDED severity level
    RECOMMENDED = RequirementLevel("RECOMMENDED", Severity.RECOMMENDED)

    #: The requirement level MUST is mapped to the REQUIRED severity level
    MUST = RequirementLevel("MUST", Severity.REQUIRED)
    #: The requirement level MUST_NOT is mapped to the REQUIRED severity level
    MUST_NOT = RequirementLevel("MUST_NOT", Severity.REQUIRED)
    #: The requirement level SHALL is mapped to the REQUIRED severity level
    SHALL = RequirementLevel("SHALL", Severity.REQUIRED)
    #: The requirement level SHALL_NOT is mapped to the REQUIRED severity level
    SHALL_NOT = RequirementLevel("SHALL_NOT", Severity.REQUIRED)

    def __init__(self):
        raise NotImplementedError(f"{type(self)} can't be instantiated")

    @staticmethod
    def all() -> list[RequirementLevel]:
        return [
            level
            for name, level in inspect.getmembers(LevelCollection)
            if not inspect.isroutine(level) and not inspect.isdatadescriptor(level) and not name.startswith("__")
        ]

    @staticmethod
    def get(name: str) -> RequirementLevel:
        try:
            return getattr(LevelCollection, name.upper())
        except AttributeError:
            raise ValueError(f"Invalid RequirementLevel: {name}") from None
