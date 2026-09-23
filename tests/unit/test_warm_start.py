# Copyright (c) 2024-2026 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import json
import threading
import time
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.compare import isomorphic

from rocrate_validator.errors import ValidationExecutionError
from rocrate_validator.models import URI, Profile, Requirement, ValidationContext, ValidationSettings, Validator
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.requirements.shacl.models import ShapesRegistry
from rocrate_validator.requirements.shacl.validator import SHACLValidationContext
from rocrate_validator.services import validate_metadata_as_dict
from tests.ro_crates import ValidROC


def _settings(crate: Path) -> ValidationSettings:
    return ValidationSettings(
        rocrate_uri=URI(crate),
        extra_profiles_path=Path("tests/data/profiles/fake"),
        profile_identifier="c",
        offline=True,
    )


def test_repeated_validation_reuses_prepared_profiles(monkeypatch):
    """A warm run must not reload profiles or rebuild their requirements."""
    calls = 0
    original = Profile.load_profiles

    def counted_load_profiles(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_load_profiles))
    validator = Validator(_settings(ValidROC().wrroc_paper))

    cold_result = validator.validate()
    warm_result = validator.validate()

    assert calls == 1
    assert cold_result.passed() == warm_result.passed()
    assert cold_result.statistics.total_checks == warm_result.statistics.total_checks
    assert cold_result.statistics.profiles == warm_result.statistics.profiles


def test_warm_run_does_not_reparse_shapes(monkeypatch):
    calls = 0
    original = ShapesRegistry.load_shapes

    def counted_load_shapes(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ShapesRegistry, "load_shapes", counted_load_shapes)
    validator = Validator(_settings(ValidROC().wrroc_paper))

    validator.validate()
    cold_calls = calls
    validator.validate()

    assert cold_calls > 0
    assert calls == cold_calls


def test_prepared_profiles_are_reused_across_crate_public_ids(monkeypatch):
    """Different crate bases share one canonically prepared profile plan."""
    calls = 0
    original = Profile.load_profiles

    def counted_load_profiles(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_load_profiles))
    original_uri = URI(ValidROC().wrroc_paper)
    settings = _settings(ValidROC().wrroc_paper)
    validator = Validator(settings)

    first_result = validator.validate()
    second_result = validator.validate(ValidROC().wrroc_paper_long_date)

    assert calls == 1
    assert settings.rocrate_uri == original_uri
    assert first_result.rocrate_uri != second_result.rocrate_uri
    shacl = Namespace("http://www.w3.org/ns/shacl#")
    first_target = next(
        ShapesRegistry.get_instance(first_result.context.profiles[-1]).shapes_graph.objects(predicate=shacl.targetNode)
    )
    second_target = next(
        ShapesRegistry.get_instance(second_result.context.profiles[-1]).shapes_graph.objects(predicate=shacl.targetNode)
    )
    assert first_result.context.prepared_validation_plan is second_result.context.prepared_validation_plan
    assert first_target == second_target
    assert str(first_target).startswith(first_result.context.prepared_profile_base)


def test_cross_base_reuse_keeps_each_crates_data_and_public_output_isolated(tmp_path, monkeypatch):
    profile_loads = 0
    shape_loads = 0
    original_profile_load = Profile.load_profiles
    original_shape_load = ShapesRegistry.load_shapes

    def counted_profile_load(cls, *args, **kwargs):
        nonlocal profile_loads
        profile_loads += 1
        return original_profile_load(*args, **kwargs)

    def counted_shape_load(self, *args, **kwargs):
        nonlocal shape_loads
        shape_loads += 1
        return original_shape_load(self, *args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_profile_load))
    monkeypatch.setattr(ShapesRegistry, "load_shapes", counted_shape_load)

    context = {
        "@vocab": "http://schema.org/",
        "about": {"@type": "@id"},
    }
    valid_metadata = {
        "@context": context,
        "@graph": [
            {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"}},
            {"@id": "./", "@type": "Dataset"},
        ],
    }
    invalid_metadata = copy.deepcopy(valid_metadata)
    invalid_metadata["@graph"][0].pop("@type")
    crate_a = tmp_path / "crate-a"
    crate_b = tmp_path / "crate-b"
    for crate, metadata in ((crate_a, valid_metadata), (crate_b, invalid_metadata)):
        crate.mkdir()
        (crate / "ro-crate-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    validator = Validator(_settings(crate_a))
    valid_result = validator.validate()
    invalid_result = validator.validate(crate_b)

    assert valid_result.passed()
    assert not invalid_result.passed()
    assert valid_result.context.publicID != invalid_result.context.publicID
    assert valid_result.context.prepared_validation_plan is invalid_result.context.prepared_validation_plan
    assert profile_loads == 1
    assert shape_loads > 0
    assert all(issue.violatingEntity == "./ro-crate-metadata.json" for issue in invalid_result.get_issues())


def test_per_call_metadata_does_not_mutate_validator_settings():
    crate = ValidROC().wrroc_paper
    with (crate / "ro-crate-metadata.json").open(encoding="utf-8") as stream:
        metadata = json.load(stream)
    metadata["@context"] = {
        "@vocab": "http://schema.org/",
        "about": {"@type": "@id"},
        "conformsTo": {"@type": "@id"},
    }
    settings = _settings(crate)
    validator = Validator(settings)

    result = validator.validate(metadata_dict=metadata)

    assert result.passed()
    assert settings.metadata_dict is None
    assert not settings.metadata_only


def test_distinct_explicit_metadata_bases_keep_separate_plans():
    crate = ValidROC().wrroc_paper
    with (crate / "ro-crate-metadata.json").open(encoding="utf-8") as stream:
        first_metadata = json.load(stream)
    first_metadata["@context"] = {
        "@base": "https://example.org/crate-a/",
        "@vocab": "http://schema.org/",
        "about": {"@type": "@id"},
        "conformsTo": {"@type": "@id"},
    }
    second_metadata = copy.deepcopy(first_metadata)
    second_metadata["@context"]["@base"] = "https://example.org/crate-b/"
    validator = Validator(_settings(crate))

    first = validator.validate(metadata_dict=first_metadata)
    second = validator.validate(metadata_dict=second_metadata)

    assert first.context.effective_ontology_base == "https://example.org/crate-a/"
    assert second.context.effective_ontology_base == "https://example.org/crate-b/"
    assert first.context.prepared_validation_plan is not second.context.prepared_validation_plan


def test_metadata_service_does_not_mutate_caller_settings():
    crate = ValidROC().wrroc_paper
    with (crate / "ro-crate-metadata.json").open(encoding="utf-8") as stream:
        metadata = json.load(stream)
    metadata["@context"] = {
        "@vocab": "http://schema.org/",
        "about": {"@type": "@id"},
        "conformsTo": {"@type": "@id"},
    }
    settings = _settings(crate)

    result = validate_metadata_as_dict(metadata, settings)

    assert result.passed()
    assert settings.metadata_dict is None
    assert not settings.metadata_only


def test_per_call_inputs_are_mutually_exclusive():
    validator = Validator(_settings(ValidROC().wrroc_paper))

    with pytest.raises(ValueError, match="mutually exclusive"):
        validator.validate(ValidROC().wrroc_paper, metadata_dict={"@graph": []})


def test_requirement_selection_survives_a_per_call_base_change(monkeypatch):
    settings = _settings(ValidROC().wrroc_paper)
    validator = Validator(settings)
    source_context = ValidationContext(validator, settings)
    selected = source_context.profiles[-1].requirements[0]
    executed = []

    def record_requirement(requirement, context):
        executed.append(requirement.identifier)
        return True

    monkeypatch.setattr(Requirement, "_do_validate_", record_requirement)

    validator.validate_requirements(
        [selected],
        include_dependencies=False,
        rocrate_uri=ValidROC().wrroc_paper_long_date,
    )

    assert executed == [selected.identifier]


def test_clear_prepared_profiles_forces_reload(monkeypatch):
    calls = 0
    original = Profile.load_profiles

    def counted_load_profiles(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_load_profiles))
    validator = Validator(_settings(ValidROC().wrroc_paper))

    validator.validate()
    validator.clear_prepared_profiles()
    validator.validate()

    assert calls == 2


def test_profile_detection_and_validation_share_catalog(monkeypatch):
    calls = 0
    original = Profile.load_profiles

    def counted_load_profiles(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_load_profiles))
    validator = Validator(_settings(ValidROC().wrroc_paper))

    detected = validator.detect_rocrate_profiles()
    result = validator.validate()

    assert detected
    assert result.passed()
    assert calls == 1


def test_prepare_can_eagerly_warm_and_refresh_profiles(monkeypatch):
    calls = 0
    original = Profile.load_profiles

    def counted_load_profiles(cls, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(Profile, "load_profiles", classmethod(counted_load_profiles))
    validator = Validator(_settings(ValidROC().wrroc_paper))

    validator.prepare()
    validator.validate()
    assert calls == 1

    validator.prepare(refresh=True)
    validator.validate()
    assert calls == 2


def test_inherited_ontologies_are_prepared_once(monkeypatch):
    ontology_parses = 0
    original_parse = Graph.parse

    def counted_parse(self, source=None, *args, **kwargs):
        nonlocal ontology_parses
        if source is not None and str(source).endswith("ontology.ttl"):
            ontology_parses += 1
        return original_parse(self, source, *args, **kwargs)

    monkeypatch.setattr(Graph, "parse", counted_parse)
    settings = ValidationSettings(
        rocrate_uri=URI(ValidROC().wrroc_paper),
        profile_identifier="isa-ro-crate",
        offline=True,
    )
    validator = Validator(settings)

    first_context = ValidationContext(validator, settings)
    first_plan = first_context.prepared_validation_plan
    second_context = ValidationContext(validator, settings)
    second_plan = second_context.prepared_validation_plan

    expected = Graph()
    for profile in first_plan.profiles:
        ontology_path = profile.path / "ontology.ttl"
        if ontology_path.exists():
            original_parse(expected, ontology_path, format="ttl", publicID=first_context.prepared_ontology_base)

    assert ontology_parses == 2
    assert first_plan is second_plan
    assert isomorphic(first_plan.ontology_graph, expected)


def test_failed_run_does_not_contaminate_next_run(monkeypatch):
    validator = Validator(_settings(ValidROC().wrroc_paper))
    original_execute_check = SHACLCheck.execute_check

    def fail_validation(*args, **kwargs):
        raise ValidationExecutionError("synthetic engine failure")

    monkeypatch.setattr(SHACLCheck, "execute_check", fail_validation)
    with pytest.raises(ValidationExecutionError, match="synthetic engine failure"):
        validator.validate()

    monkeypatch.setattr(SHACLCheck, "execute_check", original_execute_check)
    assert validator.validate().passed()


def test_per_run_graph_mutations_do_not_reach_the_next_run():
    validator = Validator(_settings(ValidROC().wrroc_paper))
    marker = (
        URIRef("https://example.org/run"),
        URIRef("https://example.org/has"),
        URIRef("https://example.org/private-marker"),
    )

    first = validator.validate()
    first_shacl_context = SHACLValidationContext.get_instance(first.context)
    first_shacl_context.ontology_graph.add(marker)
    first_shacl_context.shapes_registry._shapes_graph.add(marker)

    second = validator.validate()
    second_shacl_context = SHACLValidationContext.get_instance(second.context)

    assert marker not in second_shacl_context.ontology_graph
    assert marker not in second_shacl_context.shapes_registry.shapes_graph
    assert marker not in second.context.prepared_validation_plan.ontology_graph


def test_cold_and_warm_runs_report_equivalent_violations():
    crate = ValidROC().wrroc_paper
    with (crate / "ro-crate-metadata.json").open(encoding="utf-8") as stream:
        metadata = json.load(stream)
    metadata["@context"] = {
        "@vocab": "http://schema.org/",
        "about": {"@type": "@id"},
        "conformsTo": {"@type": "@id"},
    }
    settings = ValidationSettings(  # type: ignore[call-arg]
        metadata_dict=metadata,
        profiles_path=Path("tests/data/profiles/sparql_test"),
        profile_identifier="sparql-test",
        offline=True,
    )
    validator = Validator(settings)

    cold = validator.validate()
    warm = validator.validate()

    def issue_signature(result):
        return [
            (
                issue.check.identifier,
                issue.message,
                issue.violatingEntity,
                issue.violatingProperty,
                issue.violatingPropertyValue,
            )
            for issue in result.get_issues()
        ]

    assert issue_signature(cold)
    assert issue_signature(cold) == issue_signature(warm)
    assert cold.statistics.total_checks == warm.statistics.total_checks
    assert cold.statistics.check_count_by_severity == warm.statistics.check_count_by_severity


def test_validator_serializes_overlapping_runs(monkeypatch):
    validator = Validator(_settings(ValidROC().wrroc_paper))
    active = 0
    max_active = 0
    state_lock = threading.Lock()
    original = validator.__do_validate_locked__

    def tracked(*args, **kwargs):
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        try:
            return original(*args, **kwargs)
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(validator, "__do_validate_locked__", tracked)
    results = []
    threads = [threading.Thread(target=lambda: results.append(validator.validate())) for _ in range(2)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max_active == 1
    assert len(results) == 2
    assert all(result.passed() for result in results)
