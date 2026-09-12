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

from enum import Enum


class CheckResult(str, Enum):
    """Normalized outcome of a requirement check."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


CheckResultValue = bool | CheckResult | None


def normalize_check_result(value: CheckResultValue) -> CheckResult:
    """Convert legacy boolean and ``None`` outcomes to a check result."""
    if isinstance(value, CheckResult):
        return value
    if value is None:
        return CheckResult.SKIPPED
    if isinstance(value, bool):
        return CheckResult.PASSED if value else CheckResult.FAILED
    raise TypeError(f"Check results must be bool, CheckResult, or None, not {type(value).__name__}")
