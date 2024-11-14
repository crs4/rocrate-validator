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

import os


from rocrate_validator import log as logging
from rocrate_validator.cli.commands.validate import __compute_profile_stats__
from rocrate_validator.models import DEFAULT_PROFILES_PATH, LevelCollection, Profile

# set up logging
logger = logging.getLogger(__name__)


def test_compute_stats(fake_profiles_path):

    settings = {
        "fail_fast": False,
        "profiles_path": fake_profiles_path,
        "profile_identifier": "a",
        "enable_profile_inheritance": True,
        "allow_requirement_check_override": True,
        "requirement_severity": "REQUIRED",
    }

    profiles_path = settings["profiles_path"]
    logger.debug("The profiles path: %r", DEFAULT_PROFILES_PATH)
    assert os.path.exists(profiles_path)
    profiles = Profile.load_profiles(profiles_path)
    # The number of profiles should be greater than 0
    assert len(profiles) > 0

    # Get the profile ro-crate
    profile = profiles[0]
    logger.debug("The profile: %r", profile)
    assert profile is not None
    assert profile.identifier == "a"

    # extract the list of not hidden requirements
    logger.error("The number of requirements: %r", len(profile.get_requirements()))
    requirements = [r for r in profile.get_requirements() if not r.hidden]
    logger.debug("The requirements: %r", requirements)
    assert len(requirements) > 0

    stats = __compute_profile_stats__(settings)

    # Check severity
    assert stats["severity"].name == "REQUIRED"

    # Check the number of profiles
    assert len(stats["profiles"]) == 1

    # check the number of requirements in stats and the number of requirements in the profile
    assert stats["total_requirements"] == len(requirements)

    # Check if the number of requirements is greater than 0
    assert stats["total_requirements"] > 0

    # extract the first and unique requirement
    requirement = requirements[0]

    # check the number of checks in the requirement
    assert len(requirement.get_checks()) == len(requirement.get_checks_by_level(LevelCollection.get("REQUIRED")))

    # check the number of requirement checks
    assert stats["total_checks"] == len([_ for _ in requirements[0].get_checks() if not _.overridden])

    logger.error(stats)
