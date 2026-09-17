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

from rocrate_validator.models import CheckResult, SkipCategory, ValidationResult


def _result():
    result = object.__new__(ValidationResult)
    result._check_results = {}
    result._executed_checks = set()
    result._executed_checks_results = {}
    result._skipped_checks = set()
    result._skipped_check_details = {}
    return result


def _check():
    check = SimpleNamespace(
        identifier="test_1.1",
        name="dependent",
        severity=SimpleNamespace(name="REQUIRED"),
        requirement=SimpleNamespace(
            name="Dependent requirement",
            profile=SimpleNamespace(identifier="test"),
        ),
    )
    return type("TestCheck", (), check.__dict__)()


def test_skipped_check_detail_preserves_reason_and_category():
    result = _result()
    check = _check()

    result._record_check_result(check, CheckResult.SKIPPED, "base failed", SkipCategory.DEPENDENCY)

    assert result.skipped_check_details[0].category is SkipCategory.DEPENDENCY
    assert result.skipped_check_details[0].to_dict() == {
        "identifier": "test_1.1",
        "profile": "test",
        "requirement": "Dependent requirement",
        "name": "dependent",
        "severity": "REQUIRED",
        "message": "base failed",
        "category": "dependency",
    }


def test_skipped_check_detail_is_removed_when_check_passes():
    result = _result()
    check = _check()

    result.record_skip(check, "base skipped", SkipCategory.DEPENDENCY)
    result._record_check_result(check, CheckResult.PASSED)

    assert result.skipped_check_details == []


def test_skip_category_has_stable_values_and_descriptions():
    assert {category.value for category in SkipCategory} == {
        "returned",
        "configured",
        "deactivated",
        "dependency",
        "not_reached",
        "inherited",
    }
    assert all(category.description for category in SkipCategory)
    assert SkipCategory.DEPENDENCY.description == "The check was skipped because a dependency did not pass."
