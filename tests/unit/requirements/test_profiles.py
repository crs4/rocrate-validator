import logging
import os

import pytest

from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.errors import DuplicateRequirementCheck, InvalidProfilePath
from rocrate_validator.models import (Profile, ValidationContext,
                                      ValidationSettings, Validator)
from tests.ro_crates import InvalidFileDescriptorEntity

# set up logging
logger = logging.getLogger(__name__)

#  Global set up the paths
paths = InvalidFileDescriptorEntity()


def test_order_of_loaded_profiles(profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.error("The profiles path: %r", profiles_path)
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
        "data_path": "/tmp/random_path",
        "inherit_profiles": False
    }

    settings = ValidationSettings(**settings)
    assert not settings.inherit_profiles, "The inheritance mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

    # Check if the InvalidProfilePath exception is raised
    with pytest.raises(InvalidProfilePath):
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_valid_profile_without_inheritance_from_validation_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c",
        "data_path": "/tmp/random_path",
        "inherit_profiles": False
    }

    settings = ValidationSettings(**settings)
    assert not settings.inherit_profiles, "The inheritance mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

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
        "data_path": "/tmp/random_path",
        "inherit_profiles": True,
        "disable_check_for_duplicates": True,
    }

    settings = ValidationSettings(**settings)
    assert settings.inherit_profiles, "The inheritance mode should be set to True"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

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


def test_loaded_valid_profile_with_inheritance_from_validator_context(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""

    def __perform_test__(profile_identifier: str, expected_inherited_profiles: list[str]):
        settings = {
            "profiles_path": fake_profiles_path,
            "profile_identifier": profile_identifier,
            "data_path": "/tmp/random_path",
            "disable_check_for_duplicates": True,
        }

        validator = Validator(settings)
        # initialize the validation context
        context = ValidationContext(validator, validator.validation_settings.to_dict())

        # Check if the inheritance mode is set to True
        assert context.inheritance_enabled

        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)

        # get and check the profile
        profile = context.get_profile_by_token(profile_identifier)[0]
        assert profile.token == profile_identifier, f"The profile name should be {profile_identifier}"

        # The number of profiles should be 1
        profiles_names = [_.token for _ in profile.inherited_profiles]
        assert profiles_names == expected_inherited_profiles, f"The number of profiles should be {expected_inherited_profiles}"

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
        "data_path": "/tmp/random_path",
        "inherit_profiles": True,
        "allow_shapes_override": False,
    }

    settings = ValidationSettings(**settings)
    assert settings.inherit_profiles, "The inheritance mode should be set to True"
    assert not settings.allow_shapes_override, "The override mode should be set to False"

    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_invalid_profile_with_override_on_same_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "invalid-duplicated-shapes",
        "data_path": "/tmp/random_path",
        "inherit_profiles": True,
        "allow_shapes_override": False
    }

    settings = ValidationSettings(**settings)
    assert settings.inherit_profiles, "The inheritance mode should be set to True"
    assert not settings.allow_shapes_override, "The override mode should be set to `True`"
    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

    with pytest.raises(DuplicateRequirementCheck):
        # Load the profiles
        profiles = context.profiles
        logger.debug("The profiles: %r", profiles)


def test_load_valid_profile_with_override_on_inherited_profile(fake_profiles_path: str):
    """Test the loaded profiles from the validator context."""
    settings = {
        "profiles_path": fake_profiles_path,
        "profile_identifier": "c-overridden",
        "data_path": "/tmp/random_path",
        "inherit_profiles": True,
        "allow_shapes_override": True
    }

    settings = ValidationSettings(**settings)
    assert settings.inherit_profiles, "The inheritance mode should be set to True"
    assert settings.allow_shapes_override, "The override mode should be set to `True`"
    validator = Validator(settings)
    # initialize the validation context
    context = ValidationContext(validator, validator.validation_settings.to_dict())

    # Load the profiles
    profiles = context.profiles
    logger.debug("The profiles: %r", profiles)

    # The number of profiles should be 2
    assert len(profiles) == 3, "The number of profiles should be 3"

    # the number of checks should be 2
    requirements_checks = [requirement for profile in profiles for requirement in profile.requirements]
    assert len(requirements_checks) == 3, "The number of requirements should be 2"
