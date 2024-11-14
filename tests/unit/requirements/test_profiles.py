# Copyright (c) 2024 CRS4
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
import os

import pytest

from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.errors import (DuplicateRequirementCheck,
                                      InvalidProfilePath,
                                      ProfileSpecificationError)
from rocrate_validator.models import (Profile, ValidationContext,
                                      ValidationSettings, Validator)
from tests.ro_crates import InvalidFileDescriptorEntity, ValidROC

# set up logging
logger = logging.getLogger(__name__)

#  Global set up the paths
paths = InvalidFileDescriptorEntity()


def test_order_of_loaded_profiles(profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", profiles_path)
    assert os.path.exists(profiles_path)
    profiles = Profile.load_profiles(profiles_path=profiles_path)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # Extract the profile names
    profile_names = sorted([profile.token for profile in profiles])
    logger.debug("The profile names: %r", profile_names)

    # The order of the profiles should be the same as the order of the directories
    # in the profiles directory
    profile_directories = sorted(os.listdir(profiles_path))
    logger.debug("The profile directories: %r", profile_directories)
    assert profile_names == profile_directories


def test_load_invalid_profile_from_validation_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": "/tmp/random_path_xxx",
        "profile_identifier": DEFAULT_PROFILE_IDENTIFIER,
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": False
    }

    settings = ValidationSettings(**settings)
    assert not settings.enable_profile_inheritance, "The inheritance mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    # Check if the InvalidProfilePath exception is raised
    with pytest.raises(InvalidProfilePath):
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_valid_profile_without_inheritance_from_validation_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": False
    }

    settings = ValidationSettings(**settings)
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
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "disable_check_for_duplicates": True,
    }

    settings = ValidationSettings(**settings)
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
    assert profile.is_transitive_profile_of == [
        "https://w3id.org/a"], "The transitiveProfileOf property should be ['a']"


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
    with pytest.raises(ProfileSpecificationError) as excinfo:
        logger.debug("result: %r", excinfo)
        # Load the profiles
        Profile.load_profiles(profiles_path=fake_conflicting_versioned_profiles_path)
    # Check that the conflicting versions are found
    assert "Inconsistent versions found: {'3.2.2', '3.2.1', '2.3'}"


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
        assert profiles_names == expected_inherited_profiles, \
            f"The number of profiles should be {expected_inherited_profiles}"

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
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "invalid-duplicated-shapes",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": False,
    }

    settings = ValidationSettings(**settings)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"
    assert not settings.allow_requirement_check_override, "The override mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_invalid_profile_with_override_on_same_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "invalid-duplicated-shapes",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": False
    }

    settings = ValidationSettings(**settings)
    assert settings.enable_profile_inheritance, "The inheritance mode should be set to True"
    assert not settings.allow_requirement_check_override, "The override mode should be set to `True`"
    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings)

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_valid_profile_with_override_on_inherited_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c-overridden",
        "rocrate_uri": ValidROC().wrroc_paper,
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": True
    }

    settings = ValidationSettings(**settings)
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


def test_profile_parents(check_overriding_profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", check_overriding_profiles_path)
    assert os.path.exists(check_overriding_profiles_path)
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

        elif profile.token == "b":
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "a", "The parent should be 'a'"

        elif profile.token == "c":
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "a", "The parent should be 'a'"

        elif profile.token == "d":
            assert len(profile.parents) == 1, "The number of parents should be 1"
            assert profile.parents[0].token == "b", "The parent should be 'b'"

        elif profile.token == "e":
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
    assert os.path.exists(check_overriding_profiles_path)
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
        assert len(profile.inherited_profiles) == len(inherited_profiles), \
            f"The number of inherited profiles should be {len(inherited_profiles)}"
        inherited_profiles_tokens = [_.token for _ in profile.inherited_profiles]
        assert set(inherited_profiles_tokens) == set(inherited_profiles), \
            f"The inherited profiles should be {inherited_profiles}"

        # Check overridden status
        logger.debug("%r overridden by: %r", check.identifier, [
                     _.requirement.profile.identifier for _ in check.overridden_by])
        assert check.overridden == (len(overridden_by) > 0), \
            f"The check overridden status should be {len(overridden_by) > 0}"
        assert len(check.overridden_by) == len(overridden_by), \
            f"The number of overridden checks should be {len(overridden_by)}"
        overridden_by_tokens = [_.requirement.profile.identifier for _ in check.overridden_by]
        assert set(overridden_by_tokens) == set(overridden_by), \
            f"The overridden checks should be {overridden_by}"

        # Check override status
        assert len(check.override) == len(override), \
            f"The number of overridden checks should be {len(override)}"
        override_tokens = [_.requirement.profile.identifier for _ in check.override]
        assert set(override_tokens) == set(override), \
            f"The overridden checks should be {override}"

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
