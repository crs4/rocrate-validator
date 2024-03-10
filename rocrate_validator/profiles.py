from dataclasses import dataclass
import inspect
import os
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class RequirementType:
    name: str
    value: int

    def __eq__(self, other):
        return self.name == other.name and self.value == other.severity

    def __ne__(self, other):
        return self.name != other.name or self.value != other.severity

    def __lt__(self, other):
        return self.value < other.severity

    def __le__(self, other):
        return self.value <= other.severity

    def __gt__(self, other):
        return self.value > other.severity

    def __ge__(self, other):
        return self.value >= other.severity

    def __hash__(self):
        return hash((self.name, self.value))

    def __repr__(self):
        return f'RequirementType(name={self.name}, severity={self.value})'


class RequirementLevels:
    """
    * The key words MUST, MUST NOT, REQUIRED,
    * SHALL, SHALL NOT, SHOULD, SHOULD NOT,
    * RECOMMENDED, MAY, and OPTIONAL in this document
    * are to be interpreted as described in RFC 2119.
    """
    MAY = RequirementType('MAY', 1)
    OPTIONAL = RequirementType('OPTIONAL', 1)
    SHOULD = RequirementType('SHOULD', 2)
    SHOULD_NOT = RequirementType('SHOULD_NOT', 2)
    REQUIRED = RequirementType('REQUIRED', 3)
    MUST = RequirementType('MUST', 3)
    MUST_NOT = RequirementType('MUST_NOT', 3)
    SHALL = RequirementType('SHALL', 3)
    SHALL_NOT = RequirementType('SHALL_NOT', 3)
    RECOMMENDED = RequirementType('RECOMMENDED', 3)

    def all() -> Dict[str, RequirementType]:
        return {name: member for name, member in inspect.getmembers(RequirementLevels)
                if not inspect.isroutine(member)
                and not inspect.isdatadescriptor(member) and not name.startswith('__')}


