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

import pytest

from rocrate_validator.errors import CheckDependencyError
from rocrate_validator.models import CheckResult, RequirementCheck, RequirementLoader


class _Profile:
    identifier = "test"

    def __init__(self):
        self.requirements = []


class _Requirement:
    def __init__(self, profile, name):
        self.profile = profile
        self.name = name
        self._checks = []
        profile.requirements.append(self)

    def get_checks(self):
        return self._checks.copy()

    def set_checks_order(self, checks):
        self._checks = checks.copy()
        for order_number, check in enumerate(self._checks, start=1):
            check.order_number = order_number


class _Check(RequirementCheck):
    def execute_check(self, context):
        return CheckResult.PASSED


def _check(requirement, name, depends_on=()):
    check = _Check(requirement, name, depends_on=depends_on)
    requirement._checks.append(check)
    return check


def test_order_by_dependencies_reorders_checks_within_a_requirement():
    profile = _Profile()
    requirement = _Requirement(profile, "Requirement")
    dependent = _check(requirement, "dependent", ("base",))
    base = _check(requirement, "base")

    RequirementLoader.order_by_dependencies([requirement])

    assert requirement.get_checks() == [base, dependent]
    assert [check.order_number for check in requirement.get_checks()] == [1, 2]


def test_order_by_dependencies_reorders_requirements():
    profile = _Profile()
    dependent_requirement = _Requirement(profile, "Dependent")
    dependency_requirement = _Requirement(profile, "Dependency")
    dependent = _check(dependent_requirement, "dependent", ("base",))
    base = _check(dependency_requirement, "base")

    assert RequirementLoader.order_by_dependencies([dependent_requirement, dependency_requirement]) == [
        dependency_requirement,
        dependent_requirement,
    ]
    assert dependent.depends_on == ("base",)
    assert base.depends_on == ()


@pytest.mark.parametrize(
    ("dependency_name", "message"),
    [
        ("missing", "unknown check"),
    ],
)
def test_order_by_dependencies_rejects_unknown_dependencies(dependency_name, message):
    profile = _Profile()
    requirement = _Requirement(profile, "Requirement")
    _check(requirement, "dependent", (dependency_name,))

    with pytest.raises(CheckDependencyError, match=message):
        RequirementLoader.order_by_dependencies([requirement])


def test_order_by_dependencies_rejects_ambiguous_dependencies():
    profile = _Profile()
    dependent_requirement = _Requirement(profile, "Dependent")
    first_dependency = _Requirement(profile, "First")
    second_dependency = _Requirement(profile, "Second")
    _check(dependent_requirement, "dependent", ("base",))
    _check(first_dependency, "base")
    _check(second_dependency, "base")

    with pytest.raises(CheckDependencyError, match="ambiguous check"):
        RequirementLoader.order_by_dependencies(profile.requirements)


def test_order_by_dependencies_rejects_cycles():
    profile = _Profile()
    requirement = _Requirement(profile, "Requirement")
    _check(requirement, "first", ("second",))
    _check(requirement, "second", ("first",))

    with pytest.raises(CheckDependencyError, match="dependency cycle"):
        RequirementLoader.order_by_dependencies([requirement])
