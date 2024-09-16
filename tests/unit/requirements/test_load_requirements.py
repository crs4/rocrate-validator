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
from rocrate_validator.models import Profile
from tests.ro_crates import InvalidFileDescriptorEntity

# set up logging
logger = logging.getLogger(__name__)

#  Global set up the paths
paths = InvalidFileDescriptorEntity()


def test_order_of_loaded_profile_requirements(profiles_path: str):
    """Test the order of the loaded profiles."""
    logger.debug("The profiles path: %r", profiles_path)
    assert os.path.exists(profiles_path)
    profiles = Profile.load_profiles(profiles_path=profiles_path)
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
        logger.error("%r The requirement: %r -> severity: %r (path: %s)", requirement.order_number,
                     requirement.name, requirement.severity_from_path, requirement.path)

    # Sort requirements by their order
    requirements = sorted(requirements, key=lambda x: (-x.severity_from_path.value, x.path.name, x.name))

    # Check the order of the requirements
    for i, requirement in enumerate(requirements):
        if i < len(requirements) - 1:
            assert requirement < requirements[i + 1]
