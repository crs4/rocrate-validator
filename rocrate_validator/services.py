# Copyright (c) 2024-2026 CRS4
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

from rocrate_validator.constants import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_GATEWAY_TIMEOUT
from rocrate_validator.errors import ProfileNotFound
from rocrate_validator.events import Subscriber
from rocrate_validator.models import Profile, Severity, ValidationResult, ValidationSettings, Validator
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import get_profiles_path
from rocrate_validator.utils.uri import URI

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def detect_profiles(settings: dict | ValidationSettings) -> list[Profile]:
    # initialize the validator
    validator = __initialise_validator__(settings)
    # detect the profiles
    profiles = validator.detect_rocrate_profiles()
    logger.debug("Profiles detected: %s", profiles)
    return profiles


def validate_metadata_as_dict(
    metadata_dict: dict, settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None
) -> ValidationResult:
    """
    Validate the RO-Crate metadata only against a profile and return the validation result.
    """
    assert metadata_dict is not None, "Metadata dictionary cannot be None"
    assert isinstance(metadata_dict, dict), "Metadata must be a dictionary"
    # set the RO-Crate metadata dictionary in the settings
    if isinstance(settings, dict):
        settings["metadata_dict"] = metadata_dict
        settings["metadata_only"] = True
    else:
        settings.metadata_dict = metadata_dict
        settings.metadata_only = True
    # validate the RO-Crate metadata
    return validate(settings, subscribers)


def validate(
    settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None
) -> ValidationResult:
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


def _build_validator(settings: ValidationSettings, subscribers: list[Subscriber] | None) -> Validator:
    """Create a validator for the given settings and register any subscribers."""
    validator = Validator(settings)
    logger.debug("Validator created. Starting validation...")
    if subscribers:
        for subscriber in subscribers:
            validator.add_subscriber(subscriber)
    return validator


def _extract_and_validate(
    settings: ValidationSettings, subscribers: list[Subscriber] | None, rocrate_path: Path
) -> Validator:
    """Extract a (local or downloaded) zipped RO-Crate to a temp dir and validate it."""
    original_data_path = settings.rocrate_uri
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            with zipfile.ZipFile(rocrate_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)
                logger.debug("RO-Crate extracted to temporary directory: %s", tmp_dir)
            settings.rocrate_uri = URI(str(tmp_dir))
            return _build_validator(settings, subscribers)
        finally:
            if original_data_path is not None:
                settings.rocrate_uri = original_data_path
                logger.debug("Original data path restored: %s", original_data_path)


def _download_remote_rocrate(
    settings: ValidationSettings, subscribers: list[Subscriber] | None, rocrate_path: URI
) -> Validator:
    """Download a remote (http/https/ftp) RO-Crate to a temp file, then extract and validate it."""
    logger.debug("RO-Crate is a remote RO-Crate")
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        requester = HttpRequester()
        offline = bool(getattr(settings, "offline", False))
        # In offline mode, the cache is the only source of truth. Otherwise,
        # bypass the cache to refresh the stored copy so that subsequent
        # offline runs validate against the latest known remote state.
        if offline:
            response = requester.get(rocrate_path.uri, stream=True, allow_redirects=True)
        else:
            response = requester.fetch_fresh(rocrate_path.uri, stream=True, allow_redirects=True)
        with response as r:
            if r.status_code >= HTTP_STATUS_BAD_REQUEST:
                if offline and r.status_code == HTTP_STATUS_GATEWAY_TIMEOUT:
                    raise FileNotFoundError(
                        f"Remote RO-Crate '{rocrate_path.uri}' is not available in the HTTP cache. "
                        f"Validate it online first, or run "
                        f"`rocrate-validator cache warm --crate '{rocrate_path.uri}'`."
                    )
                raise FileNotFoundError(
                    f"Failed to download remote RO-Crate '{rocrate_path.uri}' (status {r.status_code})."
                )
            with Path(tmp_file.name).open("wb") as f:
                shutil.copyfileobj(r.raw, f)
        logger.debug("RO-Crate downloaded to temporary file: %s", tmp_file.name)
        return _extract_and_validate(settings, subscribers, Path(tmp_file.name))


def __initialise_validator__(
    settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None
) -> Validator:
    """
    Validate a RO-Crate against a profile
    """
    # if settings is a dict, convert to ValidationSettings
    settings = ValidationSettings.parse(settings)

    # parse the rocrate path
    assert settings.rocrate_uri is not None, "RO-Crate URI is required"
    rocrate_path: URI = URI(str(settings.rocrate_uri))
    logger.debug("Validating RO-Crate: %s", rocrate_path)

    # check if the RO-Crate exists
    if (
        not getattr(settings, "metadata_only", False)
        and getattr(settings, "metadata_dict", None) is None
        and not rocrate_path.is_available()
    ):
        raise FileNotFoundError(f"RO-Crate not found: {rocrate_path}")

    # check if remote validation is enabled
    disable_remote_crate_download = settings.disable_remote_crate_download
    logger.debug("Remote validation: %s", disable_remote_crate_download)
    if disable_remote_crate_download:
        return _build_validator(settings, subscribers)

    # Resolve the RO-Crate source: remote URL, local ZIP, or local directory.
    # We support http/https/ftp protocols to download a remote RO-Crate.
    if rocrate_path.scheme in ("http", "https", "ftp"):
        return _download_remote_rocrate(settings, subscribers, rocrate_path)
    if rocrate_path.as_path().suffix == ".zip":
        logger.debug("RO-Crate is a local ZIP file")
        return _extract_and_validate(settings, subscribers, rocrate_path.as_path())
    if rocrate_path.is_local_directory():
        logger.debug("RO-Crate is a local directory")
        settings.rocrate_uri = URI(str(rocrate_path.as_path()))
        return _build_validator(settings, subscribers)
    raise ValueError(
        f"Invalid RO-Crate URI: {rocrate_path}. It MUST be a local directory or a ZIP file (local or remote)."
    )


def get_profiles(
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    severity=Severity.OPTIONAL,
    allow_requirement_check_override: bool = ValidationSettings.allow_requirement_check_override,
) -> list[Profile]:
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
    profiles = Profile.load_profiles(
        profiles_path,
        extra_profiles_path=extra_profiles_path,
        severity=severity,
        allow_requirement_check_override=allow_requirement_check_override,
    )
    logger.debug("Profiles loaded: %s", profiles)
    return profiles


def get_profile(
    profile_identifier: str,
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    severity=Severity.OPTIONAL,
    allow_requirement_check_override: bool = ValidationSettings.allow_requirement_check_override,
) -> Profile:
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
    profiles = get_profiles(
        profiles_path,
        extra_profiles_path=extra_profiles_path,
        severity=severity,
        allow_requirement_check_override=allow_requirement_check_override,
    )
    profile = Profile.find_in_list(profiles, profile_identifier)
    if profile is None:
        raise ProfileNotFound(profile_identifier)
    return profile
