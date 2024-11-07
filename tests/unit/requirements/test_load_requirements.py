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

from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.models import LevelCollection, Profile, Severity
from rocrate_validator.requirements.shacl.requirements import SHACLRequirement
from tests.ro_crates import InvalidFileDescriptorEntity

# set up logging
logger = logging.getLogger(__name__)

#  Global set up the paths
paths = InvalidFileDescriptorEntity()


def test_requirements_loading(profiles_requirement_loading: str):

    # The order of the requirement levels
    levels = (LevelCollection.REQUIRED, LevelCollection.REQUIRED, LevelCollection.RECOMMENDED, LevelCollection.OPTIONAL)

    # Define the list of requirements names
    requirements_names = ["A", "B", "A_MUST", "B_MUST"]

    # Define the number of checks for each requirement
    number_of_checks_per_requirement = 4

    # Define the settings
    settings = {
        "profiles_path": profiles_requirement_loading,
        "severity": Severity.OPTIONAL
    }

    # Load the profiles
    profiles = Profile.load_profiles(**settings)
    assert len(profiles) == 1

    # Get the first profile
    profile = profiles[0]
    assert profile.identifier == "x", "The profile identifier is incorrect"

    # The first profile should have the following requirements
    requirements = profile.get_requirements(severity=Severity.OPTIONAL)
    assert len(requirements) == len(requirements_names), "The number of requirements is incorrect"

    # Sort requirements by their order
    sorted_requirements = sorted(
        requirements, key=lambda x: (-x.severity_from_path.value, x.path.name, x.name)
        if x.severity_from_path else (0, x.path.name, x.name))

    # Check the order of the requirements
    for i, requirement in enumerate(sorted_requirements):
        if i < len(sorted_requirements) - 1:
            assert requirement < requirements[i + 1]

    # Check the requirements and their checks
    for requirement_name in requirements_names:
        logger.debug("The requirement: %r", requirement_name)
        requirement = profile.get_requirement(requirement_name)
        assert requirement.name == requirement_name, "The name of the requirement is incorrect"
        if requirement_name in ["A", "B"]:
            assert requirement.severity_from_path is None, "The severity of the requirement should be None"
        elif requirement_name in ["A_MUST", "B_MUST"]:
            assert requirement.severity_from_path == Severity.REQUIRED, \
                "The severity of the requirement should be REQUIRED"

        offset = 1 if isinstance(requirement, SHACLRequirement) else 0
        assert len(requirement.get_checks()) == number_of_checks_per_requirement + offset, \
            "The number of requirement checks is incorrect"

        for i in range(number_of_checks_per_requirement):
            logger.debug("The requirement check: %r", f"{requirement_name}_{i}")
            check = requirement.get_checks()[i+offset]
            assert check.name == f"{requirement_name}_{i}", "The name of the requirement check is incorrect"
            assert check.level.severity == levels[i].severity, "The level of the requirement check is incorrect"


def test_order_of_loaded_profile_requirements(profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", profiles_path)
    assert os.path.exists(profiles_path)
    profiles = Profile.load_profiles(profiles_path=profiles_path, severity=Severity.RECOMMENDED)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # The first profile should be the default profile
    assert profiles[0].identifier == DEFAULT_PROFILE_IDENTIFIER

    # Get the first profile
    profile = profiles[0]

    # The first profile should have the following requirements
    requirements = profile.get_requirements()
    assert len(requirements) > 0
    for requirement in requirements:
        logger.debug("%r The requirement: %r -> severity: %r (path: %s)", requirement.order_number,
                     requirement.name, requirement.severity_from_path, requirement.path)

    # Sort requirements by their order
    requirements = sorted(requirements, key=lambda x: (-x.severity_from_path.value, x.path.name, x.name)
                          if x.severity_from_path else (0, x.path.name, x.name))

    # Check the order of the requirements
    for i, requirement in enumerate(requirements):
        if i < len(requirements) - 1:
            assert requirement < requirements[i + 1]

    # Check severity of some RequirementChecks
    for r in profile.get_requirements(severity=Severity.OPTIONAL):
        logger.debug("The requirement: %r -> severity: %r", r.name, r.severity_from_path)

    r = profile.get_requirement("RO-Crate Root Data Entity RECOMMENDED value")
    assert r.severity_from_path == Severity.RECOMMENDED, "The severity of the requirement should be RECOMMENDED"

    # Check the number of requirement checks
    r_checks = r.get_checks()
    assert len(r_checks) == 1, "The number of requirement checks should be 1"

    # Inspect the first requirement check
    requirement_check = r_checks[0]
    assert requirement_check.name == "Root Data Entity: RECOMMENDED value", \
        "The name of the requirement check is incorrect"
    assert requirement_check.description == \
        "Check if the Root Data Entity is denoted by the string `./` in the file descriptor JSON-LD", \
        "The description of the requirement check is incorrect"
    assert requirement_check.severity == Severity.RECOMMENDED, "The severity of the requirement check is incorrect"


def test_hidden_requirements(profiles_loading_hidden_requirements: str):

    # Define the list of requirements names
    requirements_names = ["A", "B", "A_MUST", "B_MUST"]

    # Define the settings
    settings = {
        "profiles_path": profiles_loading_hidden_requirements,
        "severity": Severity.OPTIONAL
    }

    # Load the profiles
    profiles = Profile.load_profiles(**settings)
    assert len(profiles) == 1

    # Get the first profile
    profile = profiles[0]
    assert profile.identifier == "xh", "The profile identifier is incorrect"

    # The first profile should have the following requirements
    requirements = profile.get_requirements(severity=Severity.OPTIONAL)
    assert len(requirements) == len(requirements_names), "The number of requirements is incorrect"

    # Check if the requirement A is hidden
    requirement_a = profile.get_requirement("A")
    assert requirement_a.hidden, "The requirement A should be hidden"

    # Check if the requirement B is hidden
    requirement_b = profile.get_requirement("B")
    assert requirement_b.hidden, "The requirement B should be hidden"

    # Check if the requirement A_MUST is not hidden
    requirement_a_must = profile.get_requirement("A_MUST")
    assert not requirement_a_must.hidden, "The requirement A_MUST should not be hidden"

    # Check if the requirement B_MUST is not hidden
    requirement_b_must = profile.get_requirement("B_MUST")
    assert not requirement_b_must.hidden, "The requirement B_MUST should not be hidden"
