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

from pathlib import Path

import pytest

from rocrate_validator import services
from rocrate_validator.events import EventType, Subscriber
from rocrate_validator.models import CheckResult, SkipCategory, ValidationContext, ValidationSettings, Validator
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.requirements.shacl.validator import SHACLValidator
from rocrate_validator.utils.io_helpers.output.text.layout.progress import ProgressMonitor


@pytest.fixture
def statistics_settings(tmp_path: Path):
    """A small overlay with inherited, deactivated, hidden and target-local checks."""
    profiles = tmp_path / "profiles"
    for token in ("base", "overlay", "wrapper"):
        profile = profiles / token
        profile.mkdir(parents=True)
        inheritance = "prof:isProfileOf <urn:base>; validator:isRuleOverlayOf <urn:base>;" if token != "base" else ""
        (profile / "profile.ttl").write_text(
            f"""
            @prefix prof: <http://www.w3.org/ns/dx/prof/> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix validator: <https://github.com/crs4/rocrate-validator/> .
            <urn:{token}> a prof:Profile; prof:hasToken "{token}";
                rdfs:label "{token}"; {inheritance} .
            """,
            encoding="utf-8",
        )
    prefixes = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix schema: <http://schema.org/> .
        @prefix validator: <https://github.com/crs4/rocrate-validator/> .
    """
    (profiles / "base" / "shapes.ttl").write_text(
        prefixes
        + """
        <urn:name> a sh:NodeShape; sh:name "Name"; sh:targetNode <urn:item>;
            sh:property [sh:path schema:name; sh:name "Required name"; sh:minCount 1] .
        <urn:disabled> a sh:NodeShape; sh:name "Disabled"; sh:targetNode <urn:item>;
            sh:deactivated true; sh:class schema:Dataset .
        <urn:hidden> a sh:NodeShape, validator:HiddenShape; sh:name "Hidden";
            sh:targetNode <urn:item>; sh:class schema:Thing .
        """,
        encoding="utf-8",
    )
    (profiles / "overlay" / "shapes.ttl").write_text(
        prefixes
        + """
        <urn:description> a sh:NodeShape; sh:name "Description"; sh:targetNode <urn:item>;
            sh:property [sh:path schema:description; sh:name "Required description"; sh:minCount 1] .
        """,
        encoding="utf-8",
    )
    return ValidationSettings(
        rocrate_uri=tmp_path,
        profiles_path=profiles,
        profile_identifier="overlay",
        metadata_only=True,
        metadata_dict={
            "@context": {"@vocab": "http://schema.org/"},
            "@graph": [{"@id": "urn:item", "@type": "Thing", "name": "Example", "description": "Example"}],
        },
    )


class _StatisticsTrace(Subscriber):
    def __init__(self):
        super().__init__("statistics trace")
        self.skipped_counts = []
        self.profile_snapshots = {}

    def update(self, event, ctx=None):
        statistics = ctx.result.statistics
        self.skipped_counts.append(statistics.total_skipped_checks)
        if event.event_type is EventType.PROFILE_VALIDATION_END:
            self.profile_snapshots[event.profile.identifier] = (
                set(statistics.validated_checks),
                set(statistics.skipped_checks),
            )


class _ProgressTrace(ProgressMonitor):
    def __init__(self, settings, stats=None):
        super().__init__(settings, stats)
        self.snapshots = []

    def update(self, event, ctx=None):
        super().update(event, ctx)
        self.snapshots.append([(task.completed, task.total) for task in self.progress.tasks])


@pytest.mark.parametrize("profile", ["overlay", "wrapper"])
def test_deferred_checks_are_not_reported_as_skipped(statistics_settings, profile):
    statistics_settings.profile_identifier = profile
    trace = _StatisticsTrace()
    result = services.validate(statistics_settings, subscribers=[trace])

    assert result.passed()
    assert trace.skipped_counts == sorted(trace.skipped_counts)
    assert result.statistics.total_skipped_checks == result.skipped_checks_count == 1
    assert result.skipped_check_details[0].category is SkipCategory.DEACTIVATED
    validated, skipped = trace.profile_snapshots["base"]
    assert not validated  # inherited SHACL checks are still pending
    assert {check.name for check in skipped} == {"Disabled"}
    assert set(result.statistics.validated_checks) | set(result.statistics.skipped_checks) == result.statistics.checks


@pytest.mark.parametrize("profile", ["overlay", "wrapper"])
def test_live_and_final_progress_count_unique_processed_checks(statistics_settings, profile):
    statistics_settings.profile_identifier = profile
    monitor = _ProgressTrace(statistics_settings)
    result = services.validate(statistics_settings, subscribers=[monitor])
    final_monitor = ProgressMonitor(statistics_settings, result.statistics)

    assert all(completed <= total for snapshot in monitor.snapshots for completed, total in snapshot)
    assert [(task.completed, task.total) for task in monitor.progress.tasks] == [
        (task.completed, task.total) for task in final_monitor.progress.tasks
    ]
    assert all(task.completed == task.total for task in monitor.progress.tasks)


@pytest.mark.parametrize("effective_identifier", [False, True])
def test_configured_skip_is_included_in_totals_and_preserved(statistics_settings, effective_identifier):
    context = ValidationContext(Validator(statistics_settings), statistics_settings)
    source = next(profile for profile in context.profiles if profile.identifier == "base")
    check = source.get_requirement_check("Required name")
    statistics_settings.skip_checks = [
        context.effective_check_identifier(check) if effective_identifier else check.identifier
    ]
    result = services.validate(statistics_settings)
    statistics = result.statistics

    assert {detail.check.name for detail in result.skipped_check_details} == {"Required name", "Disabled"}
    assert statistics.total_skipped_checks == result.skipped_checks_count == 2
    assert set(statistics.validated_checks) | set(statistics.skipped_checks) == statistics.checks


def test_batched_target_failures_are_counted(statistics_settings):
    del statistics_settings.metadata_dict["@graph"][0]["description"]
    result = services.validate(statistics_settings)

    assert not result.passed()
    assert {check.name for check in result.statistics.failed_checks} == {"Required description"}
    assert set(result.statistics.failed_checks) == result.failed_checks
    assert all(result.get_check_result(check) is CheckResult.FAILED for check in result.statistics.failed_checks)
    statistics = result.statistics
    assert len(statistics.validated_checks) + statistics.total_skipped_checks == statistics.total_checks


@pytest.mark.parametrize("abort", [False, True])
def test_deferred_checks_become_skipped_when_validation_stops(statistics_settings, monkeypatch, abort):
    statistics_settings.abort_on_first = not abort
    execute_check = SHACLCheck.execute_check

    def stop_at_target(check, context):
        if check.requirement.profile.identifier == "overlay":
            context.result.add_issue("Stop before the combined SHACL run", check)
            if abort:
                context.abort_validation("Input is unavailable")
            return False
        return execute_check(check, context)

    def unexpected_batch(*args, **kwargs):
        pytest.fail("SHACL must not run after validation has stopped")

    monkeypatch.setattr(SHACLCheck, "execute_check", stop_at_target)
    monkeypatch.setattr(SHACLValidator, "validate", unexpected_batch)
    trace = _StatisticsTrace()
    result = services.validate(statistics_settings, subscribers=[trace])
    statistics = result.statistics

    assert not result.passed()
    assert trace.skipped_counts == sorted(trace.skipped_counts)
    assert {
        detail.check.name for detail in result.skipped_check_details if detail.category is SkipCategory.NOT_REACHED
    } == {"Check Name", "Required name", "Required description"}
    assert not statistics.passed_checks
    assert statistics.total_skipped_checks == result.skipped_checks_count == 4
    assert set(statistics.validated_checks) | set(statistics.skipped_checks) == statistics.checks
    assert result.to_dict()["skipped_checks"] == len(result.to_dict()["skipped_check_details"]) == 4


@pytest.mark.parametrize("missing_property", ["name", "description"])
def test_fail_fast_batch_keeps_failed_and_skipped_counts_disjoint(statistics_settings, missing_property):
    statistics_settings.abort_on_first = True
    del statistics_settings.metadata_dict["@graph"][0][missing_property]
    result = services.validate(statistics_settings)
    statistics = result.statistics

    assert not result.passed()
    assert len(statistics.failed_checks) == 1
    assert set(statistics.failed_checks) == result.failed_checks
    assert set(statistics.validated_checks).isdisjoint(statistics.skipped_checks)
    assert statistics.total_skipped_checks == result.skipped_checks_count
    assert set(statistics.validated_checks) | set(statistics.skipped_checks) == statistics.checks


def test_suppressed_inherited_checks_do_not_inflate_progress(statistics_settings):
    profile_path = statistics_settings.profiles_path / "overlay" / "profile.ttl"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8").replace("validator:isRuleOverlayOf <urn:base>;", ""),
        encoding="utf-8",
    )
    statistics_settings.disable_inherited_profiles_issue_reporting = True
    monitor = _ProgressTrace(statistics_settings)
    result = services.validate(statistics_settings, subscribers=[monitor])

    assert result.passed()
    assert result.statistics.total_checks == 2
    assert result.statistics.total_skipped_checks == result.skipped_checks_count == 0
    assert all(task.completed == task.total for task in monitor.progress.tasks)
    assert all(completed <= total for snapshot in monitor.snapshots for completed, total in snapshot)
