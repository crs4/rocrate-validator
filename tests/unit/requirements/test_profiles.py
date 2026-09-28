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

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from rdflib import Graph, Literal, Namespace

from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER, SHACL_NS
from rocrate_validator.errors import DuplicateRequirementCheck, InvalidProfilePath, ProfileSpecificationError
from rocrate_validator.events import EventType
from rocrate_validator.models import (
    URI,
    CheckResult,
    Profile,
    RequirementCheckRelation,
    Severity,
    ValidationContext,
    ValidationSettings,
    Validator,
)
from rocrate_validator.models.events import RequirementCheckValidationEvent
from rocrate_validator.models.profile_check import (
    NoRequirementCheckOverrides,
    ProfileCheckSuite,
    RuleOverlayConsistency,
)
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.requirements.shacl.errors import SHACLValidationError
from rocrate_validator.requirements.shacl.models import ShapesRegistry
from rocrate_validator.requirements.shacl.validator import (
    SHACLValidationAlreadyProcessed,
    SHACLValidationContext,
)
from tests.ro_crates import InvalidFileDescriptorEntity, ValidROC

# set up logging
logger = logging.getLogger(__name__)

# Global set up the paths
paths = InvalidFileDescriptorEntity()


@pytest.mark.skip(reason="Obsolete test for the old profile loading mechanism")
def test_order_of_loaded_profiles(profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", profiles_path)
    assert Path(profiles_path).exists()
    profiles = Profile.load_profiles(profiles_path=profiles_path)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # Extract the profile names
    profile_names = sorted([profile.token for profile in profiles])
    logger.debug("The profile names: %r", profile_names)

    # The order of the profiles should be the same as the order of the directories
    # in the profiles directory
    profile_directories = sorted(p.name for p in Path(profiles_path).iterdir())
    logger.debug("The profile directories: %r", profile_directories)
    assert profile_names == profile_directories


def test_load_invalid_profile_from_validation_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": "/tmp/random_path_xxx",
        "profile_identifier": DEFAULT_PROFILE_IDENTIFIER,
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": False,
    }

    settings = ValidationSettings(**settings_dict)
    assert not settings.enable_profile_inheritance, "The inheritance mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    # Check if the InvalidProfilePath exception is raised
    with pytest.raises(InvalidProfilePath):
        # Load the profiles
        _ = context.profiles


def test_profile_detection_error_is_not_silenced(monkeypatch):
    """Unexpected metadata errors must not become an empty profile selection."""

    class BrokenMetadata:
        def get_conforms_to(self):
            raise RuntimeError("metadata profile detection failed")

    class BrokenROCrate:
        metadata = BrokenMetadata()

    settings = ValidationSettings(
        rocrate_uri=URI(ValidROC().wrroc_paper),
        profile_identifier=DEFAULT_PROFILE_IDENTIFIER,
    )
    monkeypatch.setattr(ValidationContext, "ro_crate", property(lambda self: BrokenROCrate()))

    with pytest.raises(RuntimeError, match="profile detection failed"):
        Validator(settings).detect_rocrate_profiles()


def test_load_valid_profile_without_inheritance_from_validation_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": False,
    }

    settings = ValidationSettings(**settings_dict)
    assert not settings.enable_profile_inheritance, "The inheritance mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    # Load the profiles
    profiles = context.profiles
    logger.debug("The profiles: %r", profiles)

    # The number of profiles should be 1
    assert len(profiles) == 1, "The number of profiles should be 1"


def test_profile_spec_properties(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "disable_check_for_duplicates": True,
    }

    settings = ValidationSettings(**settings_dict)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    # Load the profiles
    profiles = context.profiles
    logger.debug("The profiles: %r", profiles)

    # The number of profiles should be 1
    assert len(profiles) == 2, "The number of profiles should be 2"

    # Get the profile
    profile = context.get_profile_by_token("c")[0]
    assert profile.token == "c", "The profile name should be c"
    assert profile.comment == "Comment for the Profile C.", "The profile comment should be 'Comment for the Profile C.'"
    assert profile.version == "1.0.0", "The profile version should be 1.0.0"
    assert profile.is_profile_of == ["https://w3id.org/a"], "The profileOf property should be ['a']"
    assert profile.is_transitive_profile_of == ["https://w3id.org/a"], (
        "The transitiveProfileOf property should be ['a']"
    )


def test_profiles_loading_free_folder_structure(profiles_with_free_folder_structure_path: str):
    """Test the loaded profiles from the validator context."""
    profiles = Profile.load_profiles(profiles_path=profiles_with_free_folder_structure_path)
    logger.debug("The profiles: %r", profiles)
    for p in profiles:
        logger.warning("The profile '%s' has %d requirements", p, len(p.requirements))

    # The number of profiles should be 3
    assert len(profiles) == 3, "The number of profiles should be 3"

    # The profile names should be a, b, and c
    assert profiles[0].token == "a", "The profile name should be 'a'"
    assert profiles[1].token == "b", "The profile name should be 'b'"
    assert profiles[2].token == "c", "The profile name should be 'c'"


def test_versioned_profiles_loading(fake_versioned_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    profiles = Profile.load_profiles(profiles_path=fake_versioned_profiles_path)
    logger.debug("The profiles: %r", profiles)
    for p in profiles:
        logger.warning("The profile '%s' has %d requirements", p, len(p.requirements))
    # The number of profiles should be 3
    assert len(profiles) == 3, "The number of profiles should be 3"

    # The profile a should have an explicit version 1.0.0
    assert profiles[0].token == "a", "The profile name should be 'a'"
    assert profiles[0].version == "1.0.0", "The profile version should be 1.0.0"

    # The profile b should have a version inferred by the 2.0
    assert profiles[1].token == "b", "The profile name should be 'b'"
    assert profiles[1].version == "2.0", "The profile version should be 2.0"

    # The profile c should have a version inferred by the 3.2.1
    assert profiles[2].token == "c", "The profile name should be 'c'"
    assert profiles[2].version == "3.2.1", "The profile version should be 3.2.1"


def test_conflicting_versioned_profiles_loading(fake_conflicting_versioned_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    with pytest.raises(ProfileSpecificationError, match="Inconsistent versions found"):
        Profile.load_profiles(profiles_path=fake_conflicting_versioned_profiles_path)


def test_loaded_valid_profile_with_inheritance_from_validator_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""

    def __perform_test__(profile_identifier: str, expected_inherited_profiles: list[str]):
        settings = {
            "profiles_path": fake_profiles_path,
            "profile_identifier": profile_identifier,
            "rocrate_uri": ValidROC().wrroc_paper,
            "disable_check_for_duplicates": True,
        }

        validator = Validator(settings)
        # initialize the validation context
        context = ValidationContext(validator, validator.validation_settings)

        # Check if the inheritance mode is set to True
        assert context.inheritance_enabled

        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)

        # get and check the profile
        profile = context.get_profile_by_token(profile_identifier)[0]
        assert profile.token == profile_identifier, f"The profile name should be {profile_identifier}"

        # The number of profiles should be 1
        profiles_names = [_.token for _ in profile.inherited_profiles]
        assert profiles_names == expected_inherited_profiles, (
            f"The number of profiles should be {expected_inherited_profiles}"
        )

    # Test the inheritance mode with 1 profile
    __perform_test__("a", [])
    # Test the inheritance mode with 2 profiles
    __perform_test__("b", ["a"])
    # Test the inheritance mode with 2 profiles
    __perform_test__("c", ["a"])
    # Test the inheritance mode with 4 profiles: using the profileOf property
    __perform_test__("d1", ["a", "b", "c"])
    # Test the inheritance mode with 4 profiles: using the transitiveProfileOf property
    __perform_test__("d2", ["a", "b", "c"])


def test_load_invalid_profile_no_override_enabled(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "invalid-duplicated-shapes",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": False,
    }

    settings = ValidationSettings(**settings_dict)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"
    assert not settings.allow_requirement_check_override, "The override mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        _ = context.profiles


def test_load_invalid_profile_with_override_on_same_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "invalid-duplicated-shapes",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": False,
    }

    settings = ValidationSettings(**settings_dict)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"
    assert not settings.allow_requirement_check_override, "The override mode should be set to `True`"
    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        _ = context.profiles


def test_validation_rejects_duplicate_check_identity_with_overrides_enabled(fake_profiles_path: str):
    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="invalid-duplicated-shapes",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
    )

    with pytest.raises(DuplicateRequirementCheck, match="Check Metadata File Descriptor entity existence"):
        _ = ValidationContext(Validator(settings), settings).profiles


def test_load_valid_profile_with_override_on_inherited_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c-overridden",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": True,
    }

    settings = ValidationSettings(**settings_dict)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"
    assert settings.allow_requirement_check_override, "The override mode should be set to `True`"
    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    # Load the profiles
    profiles = context.profiles
    logger.debug("The profiles: %r", profiles)

    # The number of profiles should be 2
    assert len(profiles) == 3, "The number of profiles should be 3"

    # the number of checks should be 2
    requirements_checks = [requirement for profile in profiles for requirement in profile.requirements]
    assert len(requirements_checks) == 3, "The number of requirements should be 2"


def test_check_name_and_severity_are_unique_within_each_profile():
    profiles = Profile.load_profiles(
        profiles_path=Path("rocrate_validator/profiles"),
        severity=Severity.OPTIONAL,
    )
    for profile in profiles:
        checks = [check for requirement in profile.requirements for check in requirement.get_checks()]
        identities = {(check.name, check.severity) for check in checks}
        assert len(identities) == len(checks), profile.identifier


def test_profile_checks_return_structured_cached_results():
    profile = next(
        item
        for item in Profile.load_profiles(Path("rocrate_validator/profiles"), severity=Severity.OPTIONAL)
        if item.identifier == "ro-crate-1.2"
    )

    first = profile.validate_checks()
    second = profile.validate_checks()

    assert first is second
    assert {result.check_id for result in first} == {
        "unique-requirement-check-identity",
        "rule-overlay-consistency",
    }
    assert all(result.passed for result in first)


def test_disabling_check_override_rejects_parent_match(check_overriding_profiles_path: str):
    with pytest.raises(DuplicateRequirementCheck, match=r"\[REQUIRED\]"):
        Profile.load_profiles(
            check_overriding_profiles_path,
            severity=Severity.OPTIONAL,
            allow_requirement_check_override=False,
        )


def test_requirement_check_override_policy_is_not_a_default_profile_check():
    assert NoRequirementCheckOverrides not in ProfileCheckSuite.DEFAULT_CHECKS


def test_requirement_check_override_policy_returns_structured_failure(check_overriding_profiles_path: str):
    profiles = Profile.load_profiles(check_overriding_profiles_path, severity=Severity.OPTIONAL)
    overriding_profile = next(item for item in profiles if item.identifier == "b")

    result = NoRequirementCheckOverrides().run(overriding_profile)

    assert not result.passed
    assert result.check_id == "no-requirement-check-overrides"
    assert result.details == {
        "name": "Check S",
        "severity": "REQUIRED",
        "sources": "a",
    }


def test_rule_overlay_sources_are_consistent(check_overriding_profiles_path: str):
    profiles = Profile.load_profiles(check_overriding_profiles_path, severity=Severity.OPTIONAL)
    overlay = next(item for item in profiles if item.identifier == "b")

    result = RuleOverlayConsistency().run(overlay)

    assert result.passed


def test_rule_overlay_source_must_be_a_direct_parent(check_overriding_profiles_path: str, monkeypatch):
    profiles = Profile.load_profiles(check_overriding_profiles_path, severity=Severity.OPTIONAL)
    overlay = next(item for item in profiles if item.identifier == "d")
    original_is_rule_overlay_of = cast("Any", Profile.is_rule_overlay_of).fget
    assert original_is_rule_overlay_of is not None
    monkeypatch.setattr(
        Profile,
        "is_rule_overlay_of",
        property(
            lambda profile: (
                ["https://w3id.org/a"]
                if profile.identifier == overlay.identifier
                else original_is_rule_overlay_of(profile)
            )
        ),
    )

    result = RuleOverlayConsistency().run(overlay)

    assert not result.passed
    assert result.message == "Rule overlay source is not a direct parent"
    assert result.details == {"source": "https://w3id.org/a"}


def test_multiple_rule_overlay_sources_require_distinct_check_identities(
    check_overriding_profiles_path: str,
    monkeypatch,
):
    profiles = Profile.load_profiles(check_overriding_profiles_path, severity=Severity.OPTIONAL)
    overlay = next(item for item in profiles if item.identifier == "y")
    original_is_rule_overlay_of = cast("Any", Profile.is_rule_overlay_of).fget
    assert original_is_rule_overlay_of is not None
    monkeypatch.setattr(
        Profile,
        "is_rule_overlay_of",
        property(
            lambda profile: (
                ["https://w3id.org/e", "https://w3id.org/f"]
                if profile.identifier == overlay.identifier
                else original_is_rule_overlay_of(profile)
            )
        ),
    )

    result = RuleOverlayConsistency().run(overlay)

    assert not result.passed
    assert result.message == "Rule overlay sources contain an ambiguous check identity"
    assert result.details["name"] == "Check S"
    assert result.details["severity"] == "REQUIRED"


def test_check_name_and_severity_match_parent_override(check_overriding_profiles_path: str):
    profiles = Profile.load_profiles(check_overriding_profiles_path, severity=Severity.OPTIONAL)
    parent = next(item for item in profiles if item.identifier == "a")
    child = next(item for item in profiles if item.identifier == "b")

    parent_check = parent.get_requirement_check("Check the name of the entity", Severity.REQUIRED)
    child_check = child.get_requirement_check("Check the name of the entity", Severity.REQUIRED)

    assert parent_check is not None
    assert child_check is not None
    assert child_check.overrides == [parent_check]
    assert child_check in parent_check.overridden_by

    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
    )
    context = ValidationContext(Validator(settings), settings)
    original_order = child_check.order_number
    child_check.order_number = 99
    try:
        assert (
            context.effective_check_identifier(child_check) == f"b_{parent_check.relative_identifier.split(' ', 1)[-1]}"
        )
    finally:
        child_check.order_number = original_order


def test_effective_checks_expose_overlay_provenance():
    profiles = Profile.load_profiles("tests/data/profiles/effective_checks", severity=Severity.OPTIONAL)
    profile = next(item for item in profiles if item.identifier == "effective-b")

    effective_checks = profile.get_effective_requirement_checks()
    by_name = {item.check.name: item for item in effective_checks}

    assert len(effective_checks) == 2
    replacement = by_name["Shared check"]
    assert replacement.relation == RequirementCheckRelation.REPLACES
    assert replacement.identifier == "effective-b_1.2"
    assert replacement.source_identifier == "effective-b_1.1"
    assert [check.identifier for check in replacement.replaces] == ["effective-a_1.2"]

    inherited = by_name["Inherited check"]
    assert inherited.relation == RequirementCheckRelation.INHERITED
    assert inherited.profile == profile
    assert inherited.identifier == "effective-b_1.1"
    assert inherited.source_identifier == "effective-a_1.1"
    assert inherited.source_profile.identifier == "effective-a"
    assert inherited.replaces == ()
    assert inherited.to_dict() == {
        "identifier": "effective-b_1.1",
        "profile": "effective-b",
        "source_identifier": "effective-a_1.1",
        "source_profile": "effective-a",
        "relation": "inherited",
        "replaces": [],
    }


def test_effective_checks_retain_ordinary_inherited_identity():
    profiles = Profile.load_profiles(Path("rocrate_validator/profiles"), severity=Severity.OPTIONAL)
    profile = next(item for item in profiles if item.identifier == "process-run-crate-0.5")
    inherited = next(
        item
        for item in profile.get_effective_requirement_checks()
        if item.relation == RequirementCheckRelation.INHERITED
    )

    assert inherited.profile == inherited.source_profile
    assert inherited.identifier == inherited.source_identifier
    assert inherited.source_profile != profile


def test_same_name_with_different_severity_does_not_override():
    profiles = Profile.load_profiles(
        profiles_path=Path("rocrate_validator/profiles"),
        severity=Severity.OPTIONAL,
        allow_requirement_check_override=True,
    )
    workflow_run = next(item for item in profiles if item.identifier == "workflow-run-crate-0.5")
    process_run = next(item for item in profiles if item.identifier == "process-run-crate-0.5")

    required = workflow_run.get_requirement_check("Root Data Entity conformsTo", Severity.REQUIRED)
    recommended = workflow_run.get_requirement_check("Root Data Entity conformsTo", Severity.RECOMMENDED)
    parent = process_run.get_requirement_check("Root Data Entity conformsTo", Severity.REQUIRED)

    assert required is not None
    assert recommended is not None
    assert parent is not None
    assert required.overrides == [parent]
    assert recommended.overrides == []


def test_rule_overlay_effective_identity_is_context_local(check_overriding_profiles_path: str):
    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
    )
    context = ValidationContext(Validator(settings), settings)
    parent = next(item for item in context.profiles if item.identifier == "a")
    inherited_check = parent.get_requirement_check("Check the name of the entity", Severity.REQUIRED)

    assert inherited_check is not None
    source_identifier = inherited_check.identifier
    assert context.is_rule_overlay_source(parent)
    assert context.effective_check_profile(inherited_check).identifier == "b"
    assert context.effective_check_identifier(inherited_check).startswith("b_")
    assert inherited_check.identifier == source_identifier
    assert inherited_check.requirement.profile.identifier == "a"

    issue = context.result.add_issue("test issue", inherited_check)
    serialized_check = issue.to_dict()["check"]
    assert serialized_check["identifier"].startswith("b_")
    assert serialized_check["profile"] == "b"
    assert serialized_check["source_identifier"] == source_identifier
    assert serialized_check["source_profile"] == "a"

    context.result._record_check_result(inherited_check, CheckResult.SKIPPED, "test skip")
    serialized_skip = context.result.skipped_check_details[0].to_dict()
    assert serialized_skip["identifier"].startswith("b_")
    assert serialized_skip["profile"] == "b"
    assert serialized_skip["source_identifier"] == source_identifier
    assert serialized_skip["source_profile"] == "a"
    assert context.result.statistics.effective_check_identifier(inherited_check).startswith("b_")
    assert context.result.statistics.effective_check_profile(inherited_check).identifier == "b"

    event = RequirementCheckValidationEvent(EventType.REQUIREMENT_CHECK_VALIDATION_END, inherited_check)
    event.set_effective_identity(
        context.effective_check_identifier(inherited_check),
        context.effective_check_profile(inherited_check).identifier,
    )
    assert event.effective_identifier.startswith("b_")
    assert event.effective_profile_identifier == "b"
    assert event.source_identifier == source_identifier
    assert event.source_profile_identifier == "a"

    suppressed_settings = replace(settings, disable_inherited_profiles_issue_reporting=True)
    suppressed_context = ValidationContext(Validator(suppressed_settings), suppressed_settings)
    assert suppressed_context.result.statistics.total_checks == context.result.statistics.total_checks


def test_rule_overlay_keeps_source_before_target(check_overriding_profiles_path: str):
    """Verify that overlay composition retains general-to-specific traversal."""
    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
    )

    context = ValidationContext(Validator(settings), settings)

    assert [profile.identifier for profile in context.profiles] == ["a", "b"]


def test_rule_overlay_check_can_be_skipped_by_source_or_effective_identifier(
    check_overriding_profiles_path: str,
) -> None:
    """Accept either check identity when configuring an overlay skip."""
    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
    )
    context = ValidationContext(Validator(settings), settings)
    source_profile = next(profile for profile in context.profiles if profile.identifier == "a")
    source_check = source_profile.get_requirement_check("Check the name of the entity", Severity.REQUIRED)

    assert source_check is not None
    supported_identifiers = (
        source_check.identifier,
        context.effective_check_identifier(source_check),
    )

    for identifier in supported_identifiers:
        skip_settings = replace(settings, skip_checks=[identifier])
        skip_context = ValidationContext(Validator(skip_settings), skip_settings)
        skip_source = next(profile for profile in skip_context.profiles if profile.identifier == "a")
        skip_check = skip_source.get_requirement_check("Check the name of the entity", Severity.REQUIRED)

        assert skip_check is not None
        assert skip_context.is_check_skipped(skip_check)


def test_shacl_overlay_profiles_are_loaded_once_before_processing(
    check_overriding_profiles_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load every overlay profile graph once while allowing deferred re-entry."""
    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
    )
    context = ValidationContext(Validator(settings), settings)
    source = next(profile for profile in context.profiles if profile.identifier == "a")
    target = next(profile for profile in context.profiles if profile.identifier == "b")
    shacl_context = SHACLValidationContext.get_instance(context)
    loaded_paths: list[Path] = []

    def load_ontology(profile_path: Path) -> Graph:
        """Record ontology loads without parsing external graph content."""
        loaded_paths.append(profile_path)
        return Graph()

    monkeypatch.setattr(shacl_context, "__load_ontology_graph__", load_ontology)

    assert shacl_context.__set_current_validation_profile__(source)
    assert shacl_context.__set_current_validation_profile__(source)
    assert shacl_context.__set_current_validation_profile__(target)
    assert loaded_paths == [source.path, target.path]
    assert shacl_context.__get_ontology_path__(source.path) == source.path / "ontology.ttl"
    assert shacl_context.__get_ontology_path__(target.path) == target.path / "ontology.ttl"

    shacl_context.current_validation_result = True
    with pytest.raises(SHACLValidationAlreadyProcessed):
        shacl_context.__set_current_validation_profile__(target)


def test_normally_inherited_check_keeps_source_identity(check_overriding_profiles_path: str):
    settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="c",
        rocrate_uri=URI(ValidROC().wrroc_paper),
    )
    context = ValidationContext(Validator(settings), settings)
    parent = next(item for item in context.profiles if item.identifier == "a")
    inherited_check = parent.get_requirement_check("Check the name of the entity", Severity.REQUIRED)

    assert inherited_check is not None
    assert not context.is_rule_overlay_source(parent)
    assert context.effective_check_profile(inherited_check).identifier == "a"
    assert context.effective_check_identifier(inherited_check) == inherited_check.identifier


def test_overlay_identity_is_isolated_between_consecutive_contexts(check_overriding_profiles_path: str):
    base_settings = ValidationSettings(
        profiles_path=Path(check_overriding_profiles_path),
        profile_identifier="b",
        rocrate_uri=URI(ValidROC().wrroc_paper),
    )
    overlay_context = ValidationContext(Validator(base_settings), base_settings)
    overlay_parent = next(item for item in overlay_context.profiles if item.identifier == "a")
    overlay_check = overlay_parent.get_requirement_check("Check the name of the entity", Severity.REQUIRED)
    assert overlay_check is not None
    assert overlay_context.effective_check_profile(overlay_check).identifier == "b"

    inherited_settings = replace(base_settings, profile_identifier="c")
    inherited_context = ValidationContext(Validator(inherited_settings), inherited_settings)
    inherited_parent = next(item for item in inherited_context.profiles if item.identifier == "a")
    inherited_check = inherited_parent.get_requirement_check("Check the name of the entity", Severity.REQUIRED)
    assert inherited_check is not None
    assert inherited_context.effective_check_profile(inherited_check).identifier == "a"
    assert inherited_context.effective_check_identifier(inherited_check) == inherited_check.identifier

    assert overlay_context.effective_check_profile(overlay_check).identifier == "b"


def test_zero_shape_target_profile_triggers_pyshacl_run(monkeypatch, fake_profiles_path: str):
    """Regression test for the 0-shape profile bug:
    when the target profile has no SHACL checks of its own,
    Validator must still drive a single pyshacl run
    on the merged shapes graph so inherited shapes get evaluated.
    Without the fix in `Validator.__ensure_target_shacl_run__`,
    no SHACLCheck would be recorded as executed for the wrapper target."""

    monkeypatch.setattr(ValidationContext, "data_graph", property(lambda self: Graph()))
    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="c-wrapper",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
        disable_check_for_duplicates=True,
    )
    result = Validator(settings).validate()

    executed_shacl = [c for c in result.executed_checks if isinstance(c, SHACLCheck)]
    assert executed_shacl, (
        "Expected at least one inherited SHACLCheck to be executed for the "
        "c-wrapper target. None recorded — the zero-shape pyshacl run was "
        "skipped."
    )


def test_pyshacl_engine_failure_is_not_silenced(monkeypatch, fake_profiles_path: str):
    """A pySHACL crash must abort validation instead of producing a clean result."""

    def fail_validation(*args, **kwargs):
        raise ImportError("cannot import name 'ConjunctiveLike' from 'pyshacl.consts'")

    monkeypatch.setattr(ValidationContext, "data_graph", property(lambda self: Graph()))
    monkeypatch.setattr("rocrate_validator.requirements.shacl.validator.pyshacl.validate", fail_validation)
    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="c-deactivated",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
        disable_check_for_duplicates=True,
    )

    with pytest.raises(SHACLValidationError, match="ConjunctiveLike") as exc_info:
        Validator(settings).validate()

    assert isinstance(exc_info.value.__cause__, ImportError)


def test_pyshacl_engine_failure_in_zero_shape_finalizer_is_not_silenced(monkeypatch, fake_profiles_path: str):
    """The forced SHACL run for an inheritance-only target must also fail closed."""

    def fail_validation(*args, **kwargs):
        raise ImportError("cannot import name 'ConjunctiveLike' from 'pyshacl.consts'")

    monkeypatch.setattr(ValidationContext, "data_graph", property(lambda self: Graph()))
    monkeypatch.setattr("rocrate_validator.requirements.shacl.validator.pyshacl.validate", fail_validation)
    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="c-wrapper",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
        disable_check_for_duplicates=True,
    )

    with pytest.raises(SHACLValidationError, match="ConjunctiveLike") as exc_info:
        Validator(settings).validate()

    assert isinstance(exc_info.value.__cause__, ImportError)


def test_profile_parents(check_overriding_profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", check_overriding_profiles_path)
    assert Path(check_overriding_profiles_path).exists()
    # Load the profiles
    profiles = Profile.load_profiles(profiles_path=check_overriding_profiles_path)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # Extract the profile names
    profile_names = sorted([profile.token for profile in profiles])
    logger.debug("The profile names: %r", profile_names)

    # Check the number of loaded profiles
    assert len(profile_names) == 8, "The number of profiles should be 8"

    # Check the number of parents of each profile
    for profile in profiles:
        if profile.token == "a":
            assert len(profile.parents) == 0, "The number of parents should be 0"

        elif profile.token in {"b", "c"}:
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "a", "The parent should be 'a'"

        elif profile.token in {"d", "e"}:
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "b", "The parent should be 'b'"

        elif profile.token == "f":
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "c", "The parent should be 'c'"

        elif profile.token == "x":
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "d", "The parent should be 'd'"

        elif profile.token == "y":
            assert len(profile.parents) == 2, "The number of parents should be 2"
            assert profile.parents[0].token == "e", "The parent should be 'e'"
            assert profile.parents[1].token == "f", "The parent should be 'f'"


def test_profile_check_overriding(check_overriding_profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", check_overriding_profiles_path)
    assert Path(check_overriding_profiles_path).exists()
    # Load the profiles
    profiles = Profile.load_profiles(profiles_path=check_overriding_profiles_path)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # Extract the profile names
    profile_names = sorted([profile.token for profile in profiles])
    logger.debug("The profile names: %r", profile_names)

    # Check the number of loaded profiles
    assert len(profile_names) == 8, "The number of profiles should be 8"

    def check_profile(profile, check, inherited_profiles, overridden_by, override):
        # Check inherited profiles
        assert len(profile.inherited_profiles) == len(inherited_profiles), (
            f"The number of inherited profiles should be {len(inherited_profiles)}"
        )
        inherited_profiles_tokens = [_.token for _ in profile.inherited_profiles]
        assert set(inherited_profiles_tokens) == set(inherited_profiles), (
            f"The inherited profiles should be {inherited_profiles}"
        )

        # Check overridden status
        logger.debug(
            "%r overridden by: %r", check.identifier, [_.requirement.profile.identifier for _ in check.overridden_by]
        )
        assert check.overridden == (len(overridden_by) > 0), (
            f"The check overridden status should be {len(overridden_by) > 0}"
        )
        assert len(check.overridden_by) == len(overridden_by), (
            f"The number of overridden checks should be {len(overridden_by)}"
        )
        overridden_by_tokens = [_.requirement.profile.identifier for _ in check.overridden_by]
        assert set(overridden_by_tokens) == set(overridden_by), f"The overridden checks should be {overridden_by}"

        # Check override status
        assert len(check.overrides) == len(override), f"The number of overridden checks should be {len(override)}"
        override_tokens = [_.requirement.profile.identifier for _ in check.overrides]
        assert set(override_tokens) == set(override), f"The overridden checks should be {override}"

    # Check the number of requirements and checks of each profile
    for profile in profiles:
        logger.debug("The profile: %r", profile)
        # Check the number of requirements
        logger.debug("The number of requirements: %r", len(profile.requirements))
        assert len(profile.requirements) == 1, "The number of requirements should be 1"
        # Get the requirement
        requirement = profile.requirements[0]
        logger.debug("The requirement: %r of the profile %r", requirement, profile.token)
        # The number of checks should be 1
        logger.debug("The number of checks: %r", len(requirement.get_checks()))
        assert len(requirement.get_checks()) == 2, "The number of checks should be 2"

        # Get the check
        check = requirement.get_checks()[0]
        logger.debug("The check: %r of requirement %r of the profiles %s", check, requirement, profile.token)

        # Check the profile 'a'
        if profile.token == "a":
            check_profile(profile, check, [], ["b", "c"], [])

        # Check the profile 'b'
        elif profile.token == "b":
            check_profile(profile, check, ["a"], ["d", "e"], ["a"])

        # Check the profile 'c'
        elif profile.token == "c":
            check_profile(profile, check, ["a"], ["f"], ["a"])

        # Check the profile 'd'
        elif profile.token == "d":
            check_profile(profile, check, ["a", "b"], ["x"], ["b"])

        # Check the profile 'e'
        elif profile.token == "e":
            check_profile(profile, check, ["a", "b"], ["y"], ["b"])

        # Check the profile 'f'
        elif profile.token == "f":
            check_profile(profile, check, ["a", "c"], ["y"], ["c"])

        # Check the profile 'y'
        elif profile.token == "y":
            check_profile(profile, check, ["a", "b", "c", "e", "f"], [], ["e", "f"])

        # Check the profile 'x'
        elif profile.token == "x":
            check_profile(profile, check, ["a", "b", "d"], [], ["d"])


def test_python_check_decorator_sets_deactivated_flag():
    """The @check decorator must propagate the `deactivated` flag onto the
    decorated function so that PyRequirement.__init_checks__ can read it."""
    from rocrate_validator.requirements.python import check

    @check(name="off", deactivated=True)
    def disabled(self, ctx):
        return False

    @check(name="on")
    def enabled(self, ctx):
        return True

    assert disabled.deactivated is True  # pyright: ignore[reportFunctionMemberAccess]
    assert enabled.deactivated is False  # pyright: ignore[reportFunctionMemberAccess]


def test_python_check_decorator_sets_dependencies():
    """The @check decorator must preserve declared check dependencies."""
    from rocrate_validator.requirements.python import check

    @check(name="dependent", depends_on=("base",))
    def dependent(self, ctx):
        return True

    assert dependent.depends_on == ("base",)  # pyright: ignore[reportFunctionMemberAccess]


def test_shacl_shape_with_deactivated_marks_check_skipped(fake_profiles_path: str):
    """A child profile that overrides an inherited NodeShape by `sh:name` and
    sets `sh:deactivated true` should produce a check whose `deactivated`
    property is True; the parent's check should be marked as `overridden`."""
    settings_dict: dict[str, Any] = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c-deactivated",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": True,
    }

    settings = ValidationSettings(**settings_dict)
    validator = Validator(settings)
    context = ValidationContext(validator, validator.validation_settings)

    profiles = context.profiles
    profile_tokens = sorted(p.token for p in profiles)
    # Inheritance chain: a <- c <- c-deactivated
    assert profile_tokens == ["a", "c", "c-deactivated"]

    target = next(p for p in profiles if p.token == "c-deactivated")
    parent_c = next(p for p in profiles if p.token == "c")

    # The PropertyShape carries `sh:deactivated true`; the matching check is
    # the second one (the first is the hidden NodeShape root check).
    target_property_check = target.requirements[0].get_checks()[1]
    parent_property_check = parent_c.requirements[0].get_checks()[1]

    assert target_property_check.deactivated is True, (
        "The deactivated property should reflect sh:deactivated true on the PropertyShape"
    )

    # The parent property check is overridden by the child's (same sh:name).
    overridden_by_tokens = [c.requirement.profile.token for c in parent_property_check.overridden_by]
    assert "c-deactivated" in overridden_by_tokens, "The parent check should be reported as overridden by c-deactivated"
    assert parent_property_check.overridden is True

    # Default state for a non-deactivated check.
    assert parent_property_check.deactivated is False


def test_shacl_check_deactivated_via_cross_profile_triple(fake_profiles_path: str):
    """A child profile that adds `<parentShapeIRI> sh:deactivated true` to its
    own shapes graph (without redeclaring the shape) should cause the parent's
    check to report `deactivated=True`. Verifies the cross-profile lookup in
    SHACLCheck.deactivated and the pre-load pass in Validator."""

    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="c-deactivated-direct",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
    )
    validator = Validator(settings)
    context = ValidationContext(validator, validator.validation_settings)

    profiles = context.profiles
    profile_tokens = sorted(p.token for p in profiles)
    assert profile_tokens == ["a", "c", "c-deactivated-direct"]

    target = next(p for p in profiles if p.token == "c-deactivated-direct")
    parent_c = next(p for p in profiles if p.token == "c")

    # Trigger lazy loading of every profile's shape graph (the Validator
    # would do this in __do_validate__; we replay it here for the unit test).
    for p in profiles:
        _ = p.requirements

    parent_shape_check = next(c for c in parent_c.requirements[0].get_checks() if isinstance(c, SHACLCheck))
    assert parent_shape_check.deactivated is False, "Sanity check: the parent shape should not be deactivated yet"

    # Simulate what a child-profile shape file would contribute: a single
    # `<parentShapeIRI> sh:deactivated true` triple in its own shapes graph.
    target_registry = ShapesRegistry.get_instance(target)
    sh = Namespace(SHACL_NS)
    target_registry._shapes_graph.add((parent_shape_check.shape.node, sh.deactivated, Literal(True)))

    assert parent_shape_check.deactivated is True, (
        "The parent's check must read sh:deactivated true from the child's shapes graph"
    )


def test_shacl_check_deactivation_scoped_to_descendants(fake_profiles_path: str):
    """A `sh:deactivated true` triple declared by a profile that does NOT
    inherit from the shape's owning profile must be ignored. Otherwise
    unrelated profiles loaded in the same process could spuriously deactivate
    one another's checks."""

    settings = ValidationSettings(
        profiles_path=Path(fake_profiles_path),
        profile_identifier="c",
        rocrate_uri=URI(ValidROC().wrroc_paper),
        enable_profile_inheritance=True,
        allow_requirement_check_override=True,
    )
    validator = Validator(settings)
    context = ValidationContext(validator, validator.validation_settings)

    # Force population of the global profile registry by listing all profiles
    # under the fake_profiles_path, then resolve the specific ones we need.
    all_profiles = Profile.load_profiles(profiles_path=fake_profiles_path)
    parent_c = next(p for p in all_profiles if p.token == "c")
    # Profile "b" is a descendant of "a" but NOT of "c" — unrelated.
    profile_b = next(p for p in all_profiles if p.token == "b")
    assert parent_c not in profile_b.inherited_profiles
    assert profile_b not in Profile.get_descendants(parent_c)

    # Trigger lazy loading.
    for p in all_profiles:
        if p.token != "invalid-duplicated-shapes":
            _ = p.requirements
    _ = context.profiles  # warm context too

    parent_shape_check = next(c for c in parent_c.requirements[0].get_checks() if isinstance(c, SHACLCheck))
    assert parent_shape_check.deactivated is False

    # Inject a deactivation triple into an unrelated profile's registry.
    sh = Namespace(SHACL_NS)
    ShapesRegistry.get_instance(profile_b)._shapes_graph.add(
        (parent_shape_check.shape.node, sh.deactivated, Literal(True))
    )

    assert parent_shape_check.deactivated is False, (
        "An unrelated profile's deactivation triple must not affect the check"
    )
