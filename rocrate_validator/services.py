import logging
from pathlib import Path
from typing import  Union

from .models import Profile, Severity, ValidationResult, ValidationSettings, Validator
from .utils import get_profiles_path

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def validate(settings: Union[dict, ValidationSettings]) -> ValidationResult:
    """
    Validate a RO-Crate against a profile
    """
    # if settings is a dict, convert to ValidationSettings
    settings = ValidationSettings.parse(settings)

    # create a validator
    validator = Validator(settings)
    logger.debug("Validator created. Starting validation...")
    # validate the RO-Crate
    result = validator.validate()
    logger.debug("Validation completed: %s", result)
    return result


def get_profiles(profiles_path: Path = DEFAULT_PROFILES_PATH, publicID: str = None) -> dict[str, Profile]:
    """
    Load the profiles from the given path
    """
    profiles = Profile.load_profiles(profiles_path, publicID=publicID)
    logger.debug("Profiles loaded: %s", profiles)
    return profiles


def get_profile(profiles_path: Path = DEFAULT_PROFILES_PATH,
                profile_name: str = "ro-crate", publicID: str = None) -> Profile:
    """
    Load the profiles from the given path
    """
    profile_path = profiles_path / profile_name
    if not Path(profiles_path).exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    profile = Profile.load(f"{profiles_path}/{profile_name}", publicID=publicID)
    logger.debug("Profile loaded: %s", profile)
    return profile
