# Copyright (c) 2024-2025 CRS4
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

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Union

import rocrate_validator.log as logging
from rocrate_validator.errors import ProfileNotFound
from rocrate_validator.events import Subscriber
from rocrate_validator.models import (Profile, Severity, ValidationResult,
                                      ValidationSettings, Validator)
from rocrate_validator.utils import URI, HttpRequester, get_profiles_path

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def detect_profiles(settings: Union[dict, ValidationSettings]) -> list[Profile]:
    # initialize the validator
    validator = __initialise_validator__(settings)
    # detect the profiles
    profiles = validator.detect_rocrate_profiles()
    logger.debug("Profiles detected: %s", profiles)
    return profiles


def validate(settings: Union[dict, ValidationSettings],
             subscribers: Optional[list[Subscriber]] = None) -> ValidationResult:
    """
    Validate a RO-Crate against a profile and return the validation result

    :param settings: the validation settings
    :type settings: Union[dict, ValidationSettings]

    :param subscribers: the list of subscribers
    :type subscribers: Optional[list[Subscriber]]

    :return: the validation result
    :rtype: ValidationResult

    """
    # initialize the validator
    validator = __initialise_validator__(settings, subscribers)
    # validate the RO-Crate
    result = validator.validate()
    logger.debug("Validation completed: %s", result)
    return result


def __initialise_validator__(settings: Union[dict, ValidationSettings],
                             subscribers: Optional[list[Subscriber]] = None) -> Validator:
    """
    Validate a RO-Crate against a profile
    """
    # if settings is a dict, convert to ValidationSettings
    settings = ValidationSettings.parse(settings)

    # parse the rocrate path
    rocrate_path: URI = URI(settings.rocrate_uri)
    logger.debug("Validating RO-Crate: %s", rocrate_path)

    # check if the RO-Crate exists
    if not rocrate_path.is_available():
        raise FileNotFoundError(f"RO-Crate not found: {rocrate_path}")

    # check if remote validation is enabled
    disable_remote_crate_download = settings.disable_remote_crate_download
    logger.debug("Remote validation: %s", disable_remote_crate_download)
    if disable_remote_crate_download:
        # create a validator
        validator = Validator(settings)
        logger.debug("Validator created. Starting validation...")
        if subscribers:
            for subscriber in subscribers:
                validator.add_subscriber(subscriber)
        return validator

    def __init_validator__(settings: ValidationSettings) -> Validator:
        # create a validator
        validator = Validator(settings)
        logger.debug("Validator created. Starting validation...")
        if subscribers:
            for subscriber in subscribers:
                validator.add_subscriber(subscriber)
        return validator

    def __extract_and_validate_rocrate__(rocrate_path: Path):
        # store the original data path
        original_data_path = settings.rocrate_uri

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # extract the RO-Crate to the temporary directory
                with zipfile.ZipFile(rocrate_path, "r") as zip_ref:
                    zip_ref.extractall(tmp_dir)
                    logger.debug("RO-Crate extracted to temporary directory: %s", tmp_dir)
                # update the data path to point to the temporary directory
                settings.rocrate_uri = Path(tmp_dir)
                # continue with the validation process
                return __init_validator__(settings)
            finally:
                # restore the original data path
                settings.rocrate_uri = original_data_path
                logger.debug("Original data path restored: %s", original_data_path)

    # check if the RO-Crate is a remote RO-Crate,
    # i.e., if the RO-Crate is a URL. If so, download the RO-Crate
    # and extract it to a temporary directory. We support either http or https
    # or ftp protocols to download the remote RO-Crate.
    if rocrate_path.scheme in ('http', 'https', 'ftp'):
        logger.debug("RO-Crate is a remote RO-Crate")
        # create a temp folder to store the downloaded RO-Crate
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            # download the remote RO-Crate
            with HttpRequester().get(rocrate_path.uri, stream=True, allow_redirects=True) as r:
                with open(tmp_file.name, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            logger.debug("RO-Crate downloaded to temporary file: %s", tmp_file.name)
            # continue with the validation process by extracting the RO-Crate and validating it
            return __extract_and_validate_rocrate__(Path(tmp_file.name))

    # check if the RO-Crate is a ZIP file
    elif rocrate_path.as_path().suffix == ".zip":
        logger.debug("RO-Crate is a local ZIP file")
        # continue with the validation process by extracting the RO-Crate and validating it
        return __extract_and_validate_rocrate__(rocrate_path.as_path())

    # if the RO-Crate is not a ZIP file, directly validate the RO-Crate
    elif rocrate_path.is_local_directory():
        logger.debug("RO-Crate is a local directory")
        settings.rocrate_uri = rocrate_path.as_path()
        return __init_validator__(settings)
    else:
        raise ValueError(
            f"Invalid RO-Crate URI: {rocrate_path}. "
            "It MUST be a local directory or a ZIP file (local or remote).")


def get_profiles(profiles_path: Path = DEFAULT_PROFILES_PATH,
                 severity=Severity.OPTIONAL,
                 allow_requirement_check_override: bool =
                 ValidationSettings.allow_requirement_check_override) -> list[Profile]:
    """
    Get the list of profiles supported by the package.
    The profile source path can be overridden by specifying ``profiles_path``.

    :param profiles_path: the path to the profiles directory
    :type profiles_path: Path

    :param severity: the severity level
    :type severity: Severity

    :param allow_requirement_check_override: a flag to enable or disable
        the requirement check override (default: ``True``).
        If ``True``, the requirement check of a profile ``A`` can be overridden
        by the requirement check of a profile extension ``B`` (i.e., when ``B extends A``)
        if they share the same name.
        If ``False``, a profile extension ``B`` can only
        add new requirements to the profile ``A`` (i.e., checks with name not present in ``A``)
        and an error is raised if a check with the same name is found in both profiles.
    :type allow_requirement_check_override: bool

    :return: the list of profiles
    :rtype: list[Profile]
    """
    profiles = Profile.load_profiles(profiles_path,
                                     severity=severity,
                                     allow_requirement_check_override=allow_requirement_check_override)
    logger.debug("Profiles loaded: %s", profiles)
    return profiles


def get_profile(profile_identifier: str,
                profiles_path: Path = DEFAULT_PROFILES_PATH,
                severity=Severity.OPTIONAL,
                allow_requirement_check_override: bool =
                ValidationSettings.allow_requirement_check_override) -> Profile:
    """
    Get the profile with the given identifier.
    The profile source path can be overridden through ``profiles_path``.
    The profile is loaded based on the given severity level and the requirement check override flag.

    :param profile_identifier: the profile identifier
    :type profile_identifier: str

    :param profiles_path: the path to the profiles directory
    :type profiles_path: Path

    :param severity: the severity level
    :type severity: Severity

    :param allow_requirement_check_override: a flag to enable or disable
        the requirement check override (default: ``True``).
        If ``True``, the requirement check of a profile ``A`` can be overridden
        by the requirement check of a profile extension ``B`` (i.e., when ``B extends A``)
        if they share the same name.
        If ``False``, a profile extension ``B`` can only
        add new requirements to the profile ``A`` (i.e., checks with name not present in ``A``)
        and an error is raised if a check with the same name is found in both profiles.
    :type allow_requirement_check_override: bool

    :return: the profile
    :rtype: Profile

    """
    profiles = get_profiles(profiles_path, severity=severity,
                            allow_requirement_check_override=allow_requirement_check_override)
    profile = next((p for p in profiles if p.identifier == profile_identifier), None) or \
        next((p for p in profiles if str(p.identifier).replace(f"-{p.version}", '') == profile_identifier), None)
    if not profile:
        raise ProfileNotFound(profile_identifier)
    return profile
