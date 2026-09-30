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

from typing import Any, cast

import pytest

from rocrate_validator.models import CheckResult, normalize_check_result
from rocrate_validator.requirements.python import check


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, CheckResult.PASSED),
        (False, CheckResult.FAILED),
        (None, CheckResult.SKIPPED),
        (CheckResult.PASSED, CheckResult.PASSED),
    ],
)
def test_normalize_check_result(value, expected):
    assert normalize_check_result(value) is expected


def test_normalize_check_result_rejects_invalid_values():
    with pytest.raises(TypeError, match="Check results must be bool"):
        normalize_check_result(cast("Any", "passed"))


@pytest.mark.parametrize("result_type", [bool, CheckResult, type(None), bool | CheckResult | None])
def test_check_decorator_accepts_tri_state_return_annotations(result_type):
    def check_function(check_instance, context):
        return True

    check_function.__annotations__["return"] = result_type
    decorated = check()(check_function)

    assert decorated.check


def test_check_decorator_rejects_invalid_return_annotation():
    with pytest.raises(RuntimeError, match="return bool, CheckResult, or None"):

        @check()
        def invalid_check(check_instance, context) -> int:
            return 1
