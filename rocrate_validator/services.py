import logging
from pathlib import Path
from typing import Optional, Union

from pyshacl.pytypes import GraphLike

from .constants import (RDF_SERIALIZATION_FORMATS_TYPES,
                        VALID_INFERENCE_OPTIONS_TYPES)
from .models import (LevelCollection, Profile, RequirementLevel, Severity,
                     ValidationResult, Validator)
from .utils import get_profiles_path

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def validate(
    rocrate_path: Path,
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    profile_name: str = "ro-crate",
    inherit_profiles: bool = True,
    ontologies_path: Optional[Path] = None,
    advanced: Optional[bool] = False,
    inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
    inplace: Optional[bool] = False,
    abort_on_first: Optional[bool] = True,
    allow_infos: Optional[bool] = False,
    allow_warnings: Optional[bool] = False,
    requirement_severity: Union[str, Severity] = Severity.REQUIRED,
    requirement_severity_only: bool = False,
    serialization_output_path: Optional[Path] = None,
    serialization_output_format: RDF_SERIALIZATION_FORMATS_TYPES = "turtle",
    **kwargs,
) -> ValidationResult:
    """
    Validate a RO-Crate against a profile
    """
    # if requirement_severity is a str, convert to Severity
    if not isinstance(requirement_severity, Severity):
        requirement_severity = Severity[requirement_severity]

    validator = Validator(
        rocrate_path=rocrate_path,
        profiles_path=profiles_path,
        profile_name=profile_name,
        inherit_profiles=inherit_profiles,
        ontologies_path=ontologies_path,
        advanced=advanced,
        inference=inference,
        inplace=inplace,
        abort_on_first=abort_on_first,
        allow_infos=allow_infos,
        allow_warnings=allow_warnings,
        requirement_severity=requirement_severity,
        requirement_severity_only=requirement_severity_only,
        serialization_output_path=serialization_output_path,
        serialization_output_format=serialization_output_format,
        **kwargs,
    )
    logger.debug("Validator created. Starting validation...")
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
