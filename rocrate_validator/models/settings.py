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

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from rocrate_validator.constants import (
    DEFAULT_HTTP_CACHE_MAX_AGE,
    DEFAULT_PROFILE_IDENTIFIER,
)
from rocrate_validator.models._logging import logger
from rocrate_validator.models.severity import Severity
from rocrate_validator.utils.cache_warmup import auto_warm_up_for_settings
from rocrate_validator.utils.document_loader import install_document_loader
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import (
    get_default_http_cache_path,
    get_profiles_path,
)
from rocrate_validator.utils.uri import URI

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

BaseTypes = str | Path | bool | int | None


@dataclass
class ValidationSettings:
    """
    Represents the settings for RO-Crate validation.

    It includes the following attributes:
    """

    #: The URI of the RO-Crate
    rocrate_uri: URI  # pyright: ignore[reportRedeclaration]
    #: The relative root path of the RO-Crate
    rocrate_relative_root_path: Path | None = None
    # Profile settings
    #: The path to the profiles
    profiles_path: Path = DEFAULT_PROFILES_PATH
    #: The path to the extra profiles
    extra_profiles_path: Path | None = None
    #: The profile identifier to validate against
    profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER
    #: Flag to enable profile inheritance
    # Use the `enable_profile_inheritance` flag with caution: disable inheritance only if the
    # target validation profile is fully self-contained and does not rely on definitions
    # from inherited profiles (e.g., entities defined upstream). For modularization
    # purposes, some base entities and properties are defined in the base RO-Crate
    # profile and are intentionally not redefined in specialized profiles; they are
    # required for validations targeting those specializations and therefore cannot be skipped.
    # Nevertheless, the validator can still suppress issue reporting for checks defined
    # in inherited profiles by setting disable_inherited_profiles_issue_reporting to `True`.
    enable_profile_inheritance: bool = True
    # Validation settings
    #: Flag to abort on first error
    abort_on_first: bool | None = False
    #: Flag to disable reporting of issues related to inherited profiles
    disable_inherited_profiles_issue_reporting: bool = False
    #: Flag to disable remote crate download
    disable_remote_crate_download: bool = True
    # Requirement settings
    #: The requirement severity
    requirement_severity: str | Severity = Severity.REQUIRED
    #: Flag to validate requirement severity only skipping check with lower or higher severity
    requirement_severity_only: bool = False
    # Requirement check settings
    #: Flag to allow requirement check override
    allow_requirement_check_override: bool = True
    #: Flag to disable the check for duplicates
    disable_check_for_duplicates: bool = False
    #: Checks to skip
    skip_checks: list[str] | None = None
    #: Flag to validate only the metadata of the RO-Crate
    metadata_only: bool = False
    #: RO-Crate metadata as dictionary
    metadata_dict: dict | None = None
    #: Verbose output
    verbose: bool = False
    #: Cache max age in seconds (negative values mean "never expire")
    cache_max_age: int = DEFAULT_HTTP_CACHE_MAX_AGE
    #: Cache path
    cache_path: Path | None = None
    #: Flag to enable offline mode: HTTP requests are served only from the cache
    offline: bool = False
    #: Flag to disable the HTTP cache entirely: every request hits the network
    no_cache: bool = False

    def __post_init__(self):
        # if requirement_severity is a str, convert to Severity
        if isinstance(self.requirement_severity, str):
            self.requirement_severity = Severity[self.requirement_severity]
        # Offline mode needs the cache to serve responses, so it cannot be
        # combined with an explicit cache disable.
        if self.offline and self.no_cache:
            raise ValueError(
                "Offline mode requires the HTTP cache to be enabled; no_cache=True is incompatible with offline=True."
            )
        # Default to the persistent user cache whenever caching is enabled so that
        # consecutive runs (online then offline) share the same HTTP cache: this
        # is what lets the offline mode find the resources fetched online.
        if self.cache_path is None and not self.no_cache:
            default_path = get_default_http_cache_path()
            default_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path = default_path
            logger.debug("Cache path not set: defaulting to persistent user cache %s", self.cache_path)
        if self.offline and self.cache_path is None:
            logger.warning(
                "Offline mode enabled without a persistent cache path: "
                "all HTTP-backed resources will fail unless pre-populated."
            )
        # Re-apply the cache settings to the HTTP requester. ``initialize_cache``
        # reconfigures the existing singleton in place (rather than dropping it),
        # so new settings take effect without discarding state set on the instance.
        HttpRequester.initialize_cache(
            cache_path=str(self.cache_path) if self.cache_path is not None else None,
            cache_max_age=self.cache_max_age,
            offline=self.offline,
            no_cache=self.no_cache,
        )
        logger.debug(
            "HTTP cache initialized at %s with max age %s seconds (offline=%s, no_cache=%s)",
            self.cache_path,
            self.cache_max_age,
            self.offline,
            self.no_cache,
        )
        # Install the JSON-LD document loader so context resolution goes through the cache.
        try:
            install_document_loader()
        except Exception as e:
            logger.debug("Could not install JSON-LD document loader: %s", e)
        # Best-effort synchronous warm-up of profile-declared URLs.
        if not self.offline:
            try:
                auto_warm_up_for_settings(self)
            except Exception as e:
                logger.debug("Auto warm-up skipped: %s", e)

    def to_dict(self):
        """
        Convert the ValidationSettings to a dictionary
        """
        result = asdict(self)
        result["rocrate_uri"] = str(self.rocrate_uri)
        result.pop("metadata_dict", None)  # exclude metadata_dict from the dict representation
        # Remove disable_crate_download from the dict representation
        result.pop("disable_remote_crate_download", None)
        # Remove requirement_severity_only from the dict representation
        result.pop("requirement_severity_only", None)
        return result

    @property  # type: ignore[no-redef]
    def rocrate_uri(self) -> URI | None:
        """
        Get the RO-Crate URI

        :return: The RO-Crate URI
        :rtype: URI
        """
        return self._rocrate_uri

    @rocrate_uri.setter
    def rocrate_uri(self, value: str | Path | URI):
        """
        Set the RO-Crate URI.

        :param value: The RO-Crate URI.
        :type value: Union[str, Path, URI]
        """
        if not value:
            raise ValueError("Invalid RO-Crate URI")
        self._rocrate_uri: URI = URI(str(value))

    @classmethod
    def parse(cls, settings: dict | ValidationSettings) -> ValidationSettings:
        """
        Parse the settings to a ValidationSettings object.

        :param settings: The settings to parse.
        :type settings: Union[dict, ValidationSettings]

        :return: The parsed settings.
        :rtype: ValidationSettings

        :raises ValueError: If the settings type is invalid.
        """
        if isinstance(settings, dict):
            return cls(**settings)
        if isinstance(settings, ValidationSettings):
            return settings
        raise ValueError(f"Invalid settings type: {type(settings)}")
