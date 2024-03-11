import logging
from typing import Dict, Literal, Optional, Union

from pyshacl.pytypes import GraphLike

from .models import Profile, ValidationResult, Validator

# set up logging
logger = logging.getLogger(__name__)


def validate(
    rocrate_path: Union[GraphLike, str, bytes],
    profiles_path: str = "./profiles",
    profile_name: str = "ro-crate",
    inherit_profiles: bool = True,
    ontologies_path: Union[GraphLike, str, bytes] = None,
    advanced: Optional[bool] = False,
    inference: Optional[Literal["owl", "rdfs"]] = False,
    inplace: Optional[bool] = False,
    abort_on_first: Optional[bool] = False,
    allow_infos: Optional[bool] = False,
    allow_warnings: Optional[bool] = False,
    serialization_output_path: str = None,
    serialization_output_format: str = "turtle",
    **kwargs,
) -> ValidationResult:

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
        serialization_output_path=serialization_output_path,
        serialization_output_format=serialization_output_format,
        **kwargs,
    )
    logger.debug("Validator created. Starting validation...")
    result = validator.validate()
    logger.debug("Validation completed: %s", result)
    return result


def get_profiles(profiles_path: str = "./profiles") -> Dict[str, Profile]:

    profiles = Profile.load_profiles(profiles_path)
    logger.debug("Profiles loaded: %s", profiles)
    return profiles
