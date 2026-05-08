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

from rocrate_validator import services
from rocrate_validator.models import RequirementLoader, Severity, ValidationContext, ValidationSettings
from tests.ro_crates import InvalidRootDataEntity


class _RequirementTypeSpy:
    """Stand-in for a Requirement subclass that records lifecycle hook calls."""

    def __init__(self, name: str, timeline: list):
        self.__name__ = name
        self._timeline = timeline
        self.calls: list[tuple[str, ValidationContext]] = []

    def initialize(self, context: ValidationContext) -> None:
        self.calls.append(("initialize", context))
        self._timeline.append(("initialize", self.__name__))

    def finalize(self, context: ValidationContext) -> None:
        self.calls.append(("finalize", context))
        self._timeline.append(("finalize", self.__name__))


@pytest.fixture
def validation_settings():
    return ValidationSettings(
        rocrate_uri=str(InvalidRootDataEntity().invalid_root_type),
        requirement_severity=Severity.OPTIONAL,
        abort_on_first=False,
    )


@pytest.fixture
def lifecycle_spies(monkeypatch):
    """
    Replace the registered requirement classes with two spy stand-ins.

    Returns (spies, timeline) where timeline records the global ordering
    of hook invocations across all spies.
    """
    timeline: list[tuple[str, str]] = []
    spies = [
        _RequirementTypeSpy("SpyTypeA", timeline),
        _RequirementTypeSpy("SpyTypeB", timeline),
    ]
    monkeypatch.setattr(
        RequirementLoader,
        "__get_requirement_classes__",
        staticmethod(lambda: spies),
    )
    return spies, timeline


def test_initialize_and_finalize_called_once_per_requirement_type(lifecycle_spies, validation_settings):
    """
    Check that each requirement type's initialize and
    finalize hooks are called exactly once per validation run.
    """
    spies, _ = lifecycle_spies

    services.validate(validation_settings)

    for spy in spies:
        events = [evt for evt, _ in spy.calls]
        assert events == ["initialize", "finalize"], (
            f"{spy.__name__} expected exactly one initialize then one finalize, got {events}"
        )


def test_lifecycle_hooks_receive_the_same_validation_context(lifecycle_spies, validation_settings):
    """
    Check that all lifecycle hooks receive the same ValidationContext instance.
    This ensures that the context is properly shared across all requirements.
    """
    spies, _ = lifecycle_spies

    services.validate(validation_settings)

    contexts = [ctx for spy in spies for _, ctx in spy.calls]
    assert contexts, "No lifecycle hook was invoked"
    first = contexts[0]
    assert isinstance(first, ValidationContext)
    assert all(ctx is first for ctx in contexts), (
        "All initialize/finalize invocations must share the same ValidationContext"
    )


def test_all_initialize_hooks_run_before_any_finalize_hook(lifecycle_spies, validation_settings):
    """
    Check that all initialize hooks are called before any finalize hook is called.
    This ensures that the context is fully initialized before any requirement starts finalizing.
    """
    _, timeline = lifecycle_spies

    services.validate(validation_settings)

    init_indices = [i for i, (evt, _) in enumerate(timeline) if evt == "initialize"]
    finalize_indices = [i for i, (evt, _) in enumerate(timeline) if evt == "finalize"]
    assert init_indices and finalize_indices, "Lifecycle hooks were not all triggered"
    assert max(init_indices) < min(finalize_indices), (
        f"Expected every initialize to precede every finalize, got timeline {timeline}"
    )


def test_lifecycle_hooks_invoked_exactly_once_per_validation_run(lifecycle_spies, validation_settings):
    """
    Run validation multiple times and check that each spy receives exactly one
    initialize+finalize pair per run.
    """

    # extract spies from fixture
    spies, _ = lifecycle_spies

    # run validation multiple times and
    # check that each spy receives exactly one initialize+finalize pair per run
    runs = 3
    for _ in range(runs):
        services.validate(validation_settings)

    for spy in spies:
        events = [evt for evt, _ in spy.calls]
        assert events == ["initialize", "finalize"] * runs, (
            f"{spy.__name__} should receive exactly one initialize+finalize "
            f"pair per validation run (got {events} across {runs} runs)"
        )
