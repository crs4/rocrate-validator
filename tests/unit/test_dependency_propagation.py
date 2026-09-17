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

from types import SimpleNamespace

from rocrate_validator.models import CheckResult, Requirement, RequirementCheck, RequirementLoader, SkipCategory
from rocrate_validator.models.check_result import normalize_check_result


class _Profile:
    identifier = "test"

    def __init__(self):
        self.requirements = []

    @property
    def parents(self):
        return []

    @property
    def siblings(self):
        return []

    def get_requirement_check(self, name):
        for requirement in self.requirements:
            check = requirement.get_check(name)
            if check:
                return check
        return None


class _Requirement(Requirement):
    def __init__(self, profile, name):
        super().__init__(profile, name=name, initialize_checks=False)
        profile.requirements.append(self)

    @property
    def hidden(self):
        return False

    def __init_checks__(self):
        return []


class _Check(RequirementCheck):
    def __init__(self, requirement, name, result, depends_on=()):
        super().__init__(requirement, name, depends_on=depends_on)
        self.result = result
        self.calls = 0

    def execute_check(self, context):
        self.calls += 1
        return self.result


class _Result:
    def __init__(self):
        self._check_results = {}
        self.skipped_checks = set()

    def _record_check_result(
        self,
        check,
        result,
        skip_message=None,
        skip_category=SkipCategory.RETURNED,
    ):
        normalized_result = normalize_check_result(result)
        self._check_results[check.identifier] = normalized_result
        if normalized_result is CheckResult.SKIPPED:
            self.skipped_checks.add(check)
        else:
            self.skipped_checks.discard(check)
        return normalized_result

    def _add_executed_check(self, check, result):
        self._record_check_result(check, result)

    def _add_skipped_check(self, check):
        self._record_check_result(check, CheckResult.SKIPPED)

    def get_check_result(self, check):
        return self._check_results.get(check.identifier)


class _Validator:
    def __init__(self):
        self.events = []

    def notify(self, event):
        self.events.append(event)


class _Context:
    def __init__(self, profile, skip_checks=(), fail_fast=False):
        self.profile_identifier = profile.identifier
        self.settings = SimpleNamespace(
            skip_checks=list(skip_checks),
            disable_inherited_profiles_issue_reporting=False,
        )
        self.result = _Result()
        self.validator = _Validator()
        self.fail_fast = fail_fast
        self.aborted = False


def _check(requirement, name, result, depends_on=(), deactivated=False):
    check = _Check(requirement, name, result, depends_on=depends_on)
    check._deactivated = deactivated
    requirement._checks.append(check)
    check.order_number = len(requirement._checks)
    return check


def _run(requirements, *, skip_checks=(), fail_fast=False):
    profile = requirements[0].profile
    ordered_requirements = RequirementLoader.order_by_dependencies(requirements)
    for order_number, requirement in enumerate(ordered_requirements, start=1):
        requirement._order_number = order_number
    context = _Context(profile, skip_checks=skip_checks, fail_fast=fail_fast)
    for requirement in ordered_requirements:
        requirement._do_validate_(context)
    return context


def test_failed_dependency_skips_dependent_check():
    profile = _Profile()
    base_requirement = _Requirement(profile, "Base")
    dependent_requirement = _Requirement(profile, "Dependent")
    base = _check(base_requirement, "base", False)
    dependent = _check(dependent_requirement, "dependent", True, depends_on=("base",))

    context = _run([dependent_requirement, base_requirement])

    assert context.result.get_check_result(base) is CheckResult.FAILED
    assert context.result.get_check_result(dependent) is CheckResult.SKIPPED
    assert dependent.calls == 0


def test_skipped_dependency_skips_dependent_check():
    profile = _Profile()
    base_requirement = _Requirement(profile, "Base")
    dependent_requirement = _Requirement(profile, "Dependent")
    base = _check(base_requirement, "base", CheckResult.SKIPPED)
    dependent = _check(dependent_requirement, "dependent", True, depends_on=("base",))

    context = _run([base_requirement, dependent_requirement])

    assert context.result.get_check_result(base) is CheckResult.SKIPPED
    assert context.result.get_check_result(dependent) is CheckResult.SKIPPED
    assert dependent.calls == 0


def test_dependency_skip_propagates_transitively():
    profile = _Profile()
    base_requirement = _Requirement(profile, "Base")
    middle_requirement = _Requirement(profile, "Middle")
    leaf_requirement = _Requirement(profile, "Leaf")
    base = _check(base_requirement, "base", False)
    middle = _check(middle_requirement, "middle", True, depends_on=("base",))
    leaf = _check(leaf_requirement, "leaf", True, depends_on=("middle",))

    context = _run([leaf_requirement, middle_requirement, base_requirement])

    assert context.result.get_check_result(base) is CheckResult.FAILED
    assert context.result.get_check_result(middle) is CheckResult.SKIPPED
    assert context.result.get_check_result(leaf) is CheckResult.SKIPPED
    assert middle.calls == 0
    assert leaf.calls == 0


def test_independent_checks_continue_after_dependency_failure():
    profile = _Profile()
    base_requirement = _Requirement(profile, "Base")
    dependent_requirement = _Requirement(profile, "Dependent")
    independent_requirement = _Requirement(profile, "Independent")
    base = _check(base_requirement, "base", False)
    dependent = _check(dependent_requirement, "dependent", True, depends_on=("base",))
    independent = _check(independent_requirement, "independent", True)

    context = _run(
        [dependent_requirement, independent_requirement, base_requirement],
        fail_fast=False,
    )

    assert context.result.get_check_result(base) is CheckResult.FAILED
    assert context.result.get_check_result(dependent) is CheckResult.SKIPPED
    assert context.result.get_check_result(independent) is CheckResult.PASSED
    assert independent.calls == 1
