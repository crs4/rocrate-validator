import logging
import os

from rocrate_validator.models import Profile
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
    profile_names = [profile for profile in profiles]
    logger.debug("The profile names: %r", profile_names)

    # The order of the profiles should be the same as the order of the directories
    # in the profiles directory
    profile_directories = os.listdir(profiles_path)
    logger.debug("The profile directories: %r", profile_directories)
    assert profile_names == profile_directories
