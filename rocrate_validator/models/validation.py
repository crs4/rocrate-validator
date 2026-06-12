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

from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from rdflib import Graph

from rocrate_validator.constants import ROCRATE_METADATA_FILE
from rocrate_validator.errors import (
    ProfileNotFound,
    ROCrateMetadataNotFoundError,
)
from rocrate_validator.events import Event, EventType, Publisher
from rocrate_validator.models._logging import logger
from rocrate_validator.models.events import (
    ProfileValidationEvent,
    RequirementValidationEvent,
    ValidationEvent,
)
from rocrate_validator.models.profile import Profile
from rocrate_validator.models.requirement import (
    Requirement,
    RequirementLoader,
)
from rocrate_validator.models.result import ValidationResult
from rocrate_validator.models.severity import Severity
from rocrate_validator.models.settings import ValidationSettings
from rocrate_validator.rocrate import ROCrate
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import find_offline_cache_miss
from rocrate_validator.utils.uri import URI


class Validator(Publisher):
    """
    Validator class for validating Research Object Crates(RO-Crate)
    against specified profiles according to the validation settings.

    Attributes:
        validation_settings(ValidationSettings): The settings used for validation.

    Methods:
        __init__(settings: Union[str, ValidationSettings]):
            Initializes the Validator with the given settings.
        validation_settings() -> ValidationSettings:
            Returns the validation settings.
        detect_rocrate_profiles() -> list[Profile]:
            Detects the profiles to validate against.
        validate() -> ValidationResult:
            Validate the RO-Crate against the detected profiles according to the validation settings
        validate_requirements(requirements: list[Requirement]) -> ValidationResult:
            Validates the RO-Crate against the specified subset of the profile requirements.
    """

    def __init__(self, settings: dict | ValidationSettings):
        self._validation_settings = ValidationSettings.parse(settings)
        super().__init__()
        # initialize the current context
        self.__current_context__: ValidationContext | None = None

    @property
    def validation_settings(self) -> ValidationSettings:
        return self._validation_settings

    def detect_rocrate_profiles(self) -> list[Profile]:
        """
        Detect the profiles to validate against
        """
        try:
            # initialize the validation context
            context = ValidationContext(self, self.validation_settings)
            candidate_profiles_uris: set[str] = set()
            try:
                candidate_profiles_uris.update(context.ro_crate.metadata.get_conforms_to() or [])
            except Exception as e:
                logger.debug("Error while getting candidate profiles URIs: %s", e)
            try:
                candidate_profiles_uris.update(context.ro_crate.metadata.get_root_data_entity_conforms_to() or [])
            except Exception as e:
                logger.debug("Error while getting candidate profiles URIs: %s", e)

            logger.debug("Candidate profiles: %s", candidate_profiles_uris)
            if not candidate_profiles_uris:
                logger.debug("Unable to determine the profile to validate against")
                return []
            # load the profiles
            profiles = []
            candidate_profiles = []
            available_profiles = Profile.load_profiles(
                context.profiles_path,
                extra_profiles_path=context.extra_profiles_path,
                publicID=context.publicID,
                severity=context.requirement_severity,
            )
            profiles = [p for p in available_profiles if p.uri in candidate_profiles_uris]
            # get the candidate profiles
            for profile in profiles:
                candidate_profiles.append(profile)
                inherited_profiles = profile.inherited_profiles
                for inherited_profile in inherited_profiles:
                    if inherited_profile in candidate_profiles:
                        candidate_profiles.remove(inherited_profile)
            logger.debug(
                "%d Candidate Profiles found: %s",
                len(candidate_profiles),
                candidate_profiles,
            )
            # unmatched candidate profiles
            unmatched_profiles = candidate_profiles_uris.difference({p.uri for p in profiles})
            logger.debug("Unmatched Candidate Profiles URIs: %s", unmatched_profiles)
            if len(unmatched_profiles) > 0:
                logger.warning(
                    "The conformance to the following profiles could not be verified: %s",
                    ", ".join(unmatched_profiles),
                )
            return candidate_profiles

        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception("Error detecting RO-Crate profiles")
            return []

    def validate(self) -> ValidationResult:
        """
        Validate the RO-Crate against the detected profiles according to the validation settings
        """
        return self.__do_validate__()

    def validate_requirements(self, requirements: list[Requirement]) -> ValidationResult:
        """
        Validates the RO-Crate against the specified subset of the profile requirements
        """
        assert all(isinstance(requirement, Requirement) for requirement in requirements), "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def __do_validate__(self, requirements: list[Requirement] | None = None) -> ValidationResult:

        # initialize the validation context
        context = ValidationContext(self, self.validation_settings)
        # register the current context
        self.__current_context__ = context

        # initialize the requirement types
        self.__invoke_pre_validation_hooks__(context)

        try:
            # set the profiles to validate against
            profiles = context.profiles
            assert len(profiles) > 0, "No profiles to validate"
            # Pre-load every profile's requirements so all shape graphs are
            # populated before the validation loop runs. This lets a check
            # see `sh:deactivated true` triples declared by descendant
            # profiles that have not yet been visited.
            for p in profiles:
                _ = p.requirements
            self.notify(EventType.VALIDATION_START)
            for profile in profiles:
                logger.debug(
                    "Validating profile %s (id: %s)",
                    profile.name,
                    profile.identifier,
                )
                # set the target profile in the context
                context._target_validation_profile = profile
                self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_START, profile=profile))
                # perform the requirements validation
                requirements = profile.get_requirements(
                    context.requirement_severity,
                    exact_match=context.requirement_severity_only,
                )
                logger.debug(
                    "Validating profile %s with %s requirements",
                    profile.identifier,
                    len(requirements),
                )
                logger.debug(
                    "For profile %s, validating these %s requirements: %s",
                    profile.identifier,
                    len(requirements),
                    requirements,
                )
                terminate = False
                for requirement in requirements:
                    if not requirement.overridden:
                        self.notify(
                            RequirementValidationEvent(
                                EventType.REQUIREMENT_VALIDATION_START,
                                requirement=requirement,
                            )
                        )
                    passed = requirement._do_validate_(context)
                    logger.debug(
                        "Requirement %s passed: %s",
                        requirement.identifier,
                        passed,
                    )
                    if not requirement.overridden:
                        self.notify(
                            RequirementValidationEvent(
                                EventType.REQUIREMENT_VALIDATION_END,
                                requirement=requirement,
                                validation_result=passed,
                            )
                        )
                    if passed:
                        logger.debug("Validation Requirement passed")
                    else:
                        logger.debug(f"Validation Requirement {requirement} failed (profile: {profile.identifier})")
                        if context.fail_fast:
                            logger.debug("Aborting on first requirement failure")
                            terminate = True
                            break
                self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_END, profile=profile))
                if terminate:
                    break

            # finalize the requirement types
            self.__invoke_post_validation_hooks__(context)
            # notify the end of the validation
            self.notify(ValidationEvent(EventType.VALIDATION_END, validation_result=context.result))
            # return the validation result
            return context.result
        finally:
            # clear the current context
            self.__current_context__ = None

    def __invoke_pre_validation_hooks__(self, context: ValidationContext):
        logger.debug("Initializing requirement types: starting...")
        requirements_types = RequirementLoader.__get_requirement_classes__()
        for requirement_type in requirements_types:
            requirement_type.initialize(context)
        logger.debug("Initializing requirement types: completed")

    def __invoke_post_validation_hooks__(self, context: ValidationContext):
        logger.debug("Finalizing requirement types: starting...")
        requirements_types = RequirementLoader.__get_requirement_classes__()
        for requirement_type in requirements_types:
            requirement_type.finalize(context)
        logger.debug("Finalizing requirement types: completed")

    def notify(self, event: Event | EventType, ctx: Any | None = None):
        """Override notify to update statistics"""
        assert self.__current_context__ is not None, "No current validation context"
        result: ValidationResult = self.__current_context__.result
        if isinstance(event, EventType):
            event = Event(event)
        result.statistics.update(event, ctx=self.__current_context__)
        return super().notify(event, ctx=self.__current_context__)


class ValidationContext:
    """
    Class that represents the context for the validation process.
    """

    def __init__(self, validator: Validator, settings: ValidationSettings):
        # reference to the validator
        self._validator = validator
        # reference to the settings
        self._settings = settings
        # reference to the data graph
        self._data_graph: Graph | None = None
        # reference to the profiles
        self._profiles: list[Profile] | None = None
        # reference to the target profile
        self._target_validation_profile: Profile | None = None
        # reference to the validation result
        self._result: ValidationResult | None = None
        # additional properties for the context
        self._properties: dict = {}
        # URLs already reported as missing from the HTTP cache during this run
        self._offline_cache_misses_warned: set[str] = set()

        # initialize the ROCrate object
        if settings.metadata_dict:
            self._rocrate = ROCrate.from_metadata_dict(settings.metadata_dict)
        else:
            rocrate_uri = settings.rocrate_uri
            assert rocrate_uri is not None, "RO-Crate URI is required when metadata_dict is not provided"
            self._rocrate = ROCrate.new_instance(
                rocrate_uri,
                relative_root_path=settings.rocrate_relative_root_path,
            )
        assert isinstance(self._rocrate, ROCrate), "Invalid RO-Crate instance"

    @property
    def ro_crate(self) -> ROCrate:
        """
        The RO-Crate instance

        :return: The RO-Crate instance
        :rtype: ROCrate
        """
        return self._rocrate

    @property
    def validator(self) -> Validator:
        """
        The validator instance which this context belongs to

        :return: The validator instance
        :rtype: Validator
        """
        return self._validator

    @property
    def result(self) -> ValidationResult:
        """
        The validation result

        :return: The validation result
        :rtype: ValidationResult
        """
        if self._result is None:
            self._result = ValidationResult(self)
        return self._result

    @property
    def settings(self) -> ValidationSettings:
        """
        The validation settings

        :return: The validation settings
        :rtype: ValidationSettings
        """
        return self._settings

    @property
    def publicID(self) -> str:
        """
        The root URI of the RO-Crate
        """
        path = str(self.ro_crate.uri.base_uri)
        if not path.endswith("/"):
            path = f"{path}/"
        return path

    @property
    def profiles_path(self) -> Path:
        """
        The path to the profiles

        :return: The path to the profiles
        :rtype: Path
        """
        profiles_path = self.settings.profiles_path
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        return profiles_path

    @property
    def extra_profiles_path(self) -> Path | None:
        """
        The path to the extra profiles

        :return: The path to the extra profiles
        :rtype: Optional[Path]
        """
        extra_profiles_path = self.settings.extra_profiles_path
        if isinstance(extra_profiles_path, str):
            extra_profiles_path = Path(extra_profiles_path)
        return extra_profiles_path or None

    @property
    def requirement_severity(self) -> Severity:
        """
        The requirement severity to validate against

        :return: The requirement severity
        :rtype: Severity
        """
        severity = self.settings.requirement_severity
        if isinstance(severity, str):
            severity = Severity[severity]
        elif not isinstance(severity, Severity):
            raise TypeError(f"Invalid severity type: {type(severity)}")
        return severity

    @property
    def requirement_severity_only(self) -> bool:
        """
        Flag to validate requirement severity only skipping check with lower or higher severity

        :return: The flag to validate requirement severity only
        :rtype: bool
        """
        return self.settings.requirement_severity_only

    @property
    def rocrate_uri(self) -> URI:
        """
        The URI of the RO-Crate

        :return: The URI of the RO-Crate
        :rtype: Path
        """
        rocrate_uri = self.settings.rocrate_uri
        if rocrate_uri is None:
            raise ValueError("RO-Crate URI is not set")
        return rocrate_uri

    @property
    def fail_fast(self) -> bool:
        """
        Flag to abort on first error

        :return: The flag to abort on first error
        :rtype: bool
        """
        return bool(self.settings.abort_on_first)

    @property
    def rel_fd_path(self) -> Path:
        """
        The relative path to the file descriptor

        :return: The relative path to the file descriptor
        :rtype: Path
        """
        return Path(ROCRATE_METADATA_FILE)

    def __load_data_graph__(self) -> Graph:
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata of: %s", self.ro_crate.uri)
        _ = data_graph.parse(
            data=self.ro_crate.metadata.as_dict(),  # type: ignore[arg-type]
            format="json-ld",
            publicID=self.publicID,
        )
        logger.debug("RO-Crate metadata loaded: %s", data_graph)
        return data_graph

    def get_data_graph(self, refresh: bool = False) -> Graph:
        """
        Utility method to get the data graph of the RO-Crate,
        i.e., the metadata of the RO-Crate as an RDF graph.

        :param refresh: Flag to refresh the data graph
        :type refresh: bool

        :return: The data graph of the RO-Crate
        :rtype: :py:class:rdflib.Graph

        :raises ROCrateMetadataNotFoundError: If the RO-Crate metadata is not found
        """
        # load the data graph
        try:
            if not self._data_graph or refresh:
                self._data_graph = self.__load_data_graph__()
            return self._data_graph
        except (HTTPError, FileNotFoundError) as e:
            logger.debug("Error loading data graph: %s", e)
            raise ROCrateMetadataNotFoundError(str(self.rocrate_uri)) from e

    @property
    def data_graph(self) -> Graph:
        """
        The data graph of the RO-Crate,
        i.e., the metadata of the RO-Crate as an RDF graph.

        :return: The data graph of the RO-Crate
        :rtype: Graph
        """
        return self.get_data_graph()

    @property
    def inheritance_enabled(self) -> bool:
        """
        Flag which indicates if profile inheritance is enabled

        :return: The flag to enable profile inheritance
        :rtype: bool
        """
        return self.settings.enable_profile_inheritance

    @property
    def profile_identifier(self) -> str:
        """
        The profile identifier to validate against

        :return: The profile identifier
        :rtype: str
        """
        return self.settings.profile_identifier

    @property
    def allow_requirement_check_override(self) -> bool:
        """
        Flag that indicates if requirement check override is allowed

        :return: The flag to allow requirement check override
        :rtype: bool
        """
        return self.settings.allow_requirement_check_override

    @property
    def disable_check_for_duplicates(self) -> bool:
        """
        Flag that indicates if the check for duplicates is disabled

        :return: The flag to disable the check for duplicates
        :rtype: bool
        """
        return self.settings.disable_check_for_duplicates

    def __load_profiles__(self) -> list[Profile]:

        # load all profiles
        profiles = Profile.load_profiles(
            self.profiles_path,
            extra_profiles_path=self.settings.extra_profiles_path,
            publicID=self.publicID,
            severity=self.requirement_severity,
            allow_requirement_check_override=self.allow_requirement_check_override,
        )

        # Check if the target profile is in the list of profiles
        profile = Profile.get_by_identifier(self.profile_identifier)
        if not profile:
            try:
                candidate_profiles = Profile.get_by_token(self.profile_identifier)
                logger.debug("Candidate profiles found by token: %s", profile)
                if candidate_profiles:
                    # Find the profile with the highest version number
                    profile = max(candidate_profiles, key=lambda p: p.version or "")
                    self.settings.profile_identifier = profile.identifier
                    logger.debug("Profile with the highest version number: %s", profile)
            except AttributeError as e:
                # raised when the profile is not found
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception("Profile not found: %s", self.profile_identifier)
                raise ProfileNotFound(
                    self.profile_identifier,
                    message=f"Profile '{self.profile_identifier}' not found in '{self.profiles_path}'",
                ) from e
            if profile is None:
                raise ProfileNotFound(
                    self.profile_identifier,
                    message=f"Profile '{self.profile_identifier}' not found in '{self.profiles_path}'",
                )

        # if the inheritance is enabled, return only the target profile
        if not self.inheritance_enabled:
            return [profile]

        # Set the profiles to validate against as the target profile and its inherited profiles
        profiles = [*profile.inherited_profiles, profile]

        # if the check for duplicates is disabled, return the profiles
        if self.disable_check_for_duplicates:
            return profiles

        return profiles

    @property
    def profiles(self) -> list[Profile]:
        """
        The profiles to validate against,
        i.e., the target profile and its inherited profiles

        :return: The profiles to validate against
        :rtype: list[Profile]
        """
        if not self._profiles:
            self._profiles = self.__load_profiles__()
        return self._profiles.copy()

    @property
    def target_validation_profile(self) -> Profile:
        """
        The target validation profile to validate against

        :return: The target validation profile
        :rtype: Profile
        """
        assert self._target_validation_profile is not None, "Target validation profile not set"
        return self._target_validation_profile

    @property
    def target_profile(self) -> Profile:
        """
        The target profile to validate against

        :return: The target profile
        :rtype: Profile
        """
        profiles = self.profiles
        assert len(profiles) > 0, "No profiles to validate"
        return self.profiles[-1]

    def get_profile_by_token(self, token: str) -> list[Profile]:
        """
        Get the profile by token from the profiles to validate against

        :param token: The token of the profile
        :type token: str

        :return: The profile with the given token
        :rtype: Profile
        """
        return [p for p in self.profiles if p.token == token]

    def get_profile_by_identifier(self, identifier: str) -> Profile:
        """
        Get the profile by identifier from the profiles to validate against

        :param identifier: The identifier of the profile
        :type identifier: str

        :return: The profile with the given identifier
        :rtype: Profile
        """
        for p in self.profiles:
            if p.identifier == identifier:
                return p
        raise ProfileNotFound(identifier)

    def maybe_warn_offline_cache_miss(self, exc: BaseException) -> bool:
        """
        If ``exc`` (or any cause/context in its chain) is an
        :class:`OfflineCacheMissError`, emit a single user-facing warning
        for the missing URL — but only the first time that URL is seen
        during this validation run — and return ``True``.

        Returns ``False`` when the exception is unrelated to offline cache
        misses, so callers can fall back to their generic handling.
        """
        miss = find_offline_cache_miss(exc)
        if miss is None:
            return False
        if miss.url not in self._offline_cache_misses_warned:
            self._offline_cache_misses_warned.add(miss.url)
            logger.warning("%s", miss)
        return True
