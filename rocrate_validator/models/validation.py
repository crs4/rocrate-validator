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

import copy
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError

from rdflib import Graph

from rocrate_validator.errors import (
    CheckDependencyError,
    ProfileNotFound,
    ROCrateMetadataNotFoundError,
)
from rocrate_validator.events import Event, EventType, Publisher
from rocrate_validator.models._logging import logger
from rocrate_validator.models.events import (
    ProfileValidationEvent,
    RequirementCheckValidationEvent,
    RequirementValidationEvent,
    ValidationEvent,
)
from rocrate_validator.models.profile import Profile
from rocrate_validator.models.requirement import (
    Requirement,
    RequirementCheck,
    RequirementLoader,
)
from rocrate_validator.models.result import ValidationResult
from rocrate_validator.models.settings import ValidationSettings
from rocrate_validator.models.severity import Severity
from rocrate_validator.models.skipped_check import SkipCategory, SkipCategoryInput
from rocrate_validator.rocrate import ROCrate
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import find_offline_cache_miss
from rocrate_validator.utils.rdf import extract_base_from_jsonld
from rocrate_validator.utils.uri import URI

if TYPE_CHECKING:
    from rocrate_validator.models.profile_provenance import EffectiveRequirementCheck


@dataclass(frozen=True)
class PreparedValidationPlan:
    """
    Profile state that can be reused by validation runs with the same base.

    Profiles own their lazily loaded requirements and shape registries, so keeping
    the same profile instances avoids reparsing those artifacts on every run.  The
    plan deliberately excludes all crate data, results and SHACL execution state;
    those remain scoped to :class:`ValidationContext`.
    """

    profiles: tuple[Profile, ...]
    ontology_graph: Graph


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
        ``detect_rocrate_profiles(rocrate_uri=None, metadata_dict=None)``:
            Detects the profiles to validate against.
        ``prepare(rocrate_uri=None, metadata_dict=None, refresh=False)``:
            Eagerly prepares reusable profile artifacts.
        clear_prepared_profiles():
            Invalidates profile preparation owned by this validator.
        ``validate(rocrate_uri=None, metadata_dict=None)``:
            Validate the RO-Crate against the detected profiles according to the validation settings
        validate_requirements(requirements: list[Requirement]) -> ValidationResult:
            Validates the RO-Crate against the specified subset of the profile requirements.
    """

    def __init__(self, settings: dict | ValidationSettings):
        self._validation_settings = ValidationSettings.parse(settings)
        super().__init__()
        # initialize the current context
        self.__current_context__: ValidationContext | None = None
        # Profile artifacts may contain relative IRIs resolved against the crate
        # public ID, so plans are cached by every setting that affects profile
        # preparation, including that effective base.
        self.__prepared_profile_catalogs: dict[tuple[Any, ...], tuple[Profile, ...]] = {}
        self.__prepared_validation_plans: dict[tuple[Any, ...], PreparedValidationPlan] = {}
        # Publisher state and ``__current_context__`` are instance-local and
        # mutable. Serialize calls made on the same Validator instead of
        # allowing two runs to corrupt each other's event/statistics context.
        self.__run_lock = threading.Lock()

    @property
    def validation_settings(self) -> ValidationSettings:
        return self._validation_settings

    @staticmethod
    def __prepared_profile_catalog_key__(context: ValidationContext) -> tuple[Any, ...]:
        return (
            context.profiles_path.resolve(),
            context.extra_profiles_path.resolve() if context.extra_profiles_path else None,
            context.publicID,
            context.requirement_severity,
            context.allow_requirement_check_override,
        )

    def __get_prepared_profile_catalog__(self, context: ValidationContext) -> tuple[Profile, ...]:
        key = self.__prepared_profile_catalog_key__(context)
        profiles = self.__prepared_profile_catalogs.get(key)
        if profiles is None:
            profiles = tuple(
                Profile.load_profiles(
                    context.profiles_path,
                    extra_profiles_path=context.extra_profiles_path,
                    publicID=context.publicID,
                    severity=context.requirement_severity,
                    allow_requirement_check_override=context.allow_requirement_check_override,
                )
            )
            self.__prepared_profile_catalogs[key] = profiles
        return profiles

    @staticmethod
    def __prepared_validation_plan_key__(context: ValidationContext) -> tuple[Any, ...]:
        return (
            context.profiles_path.resolve(),
            context.extra_profiles_path.resolve() if context.extra_profiles_path else None,
            context.publicID,
            context.effective_ontology_base,
            context.profile_identifier,
            context.requirement_severity,
            context.inheritance_enabled,
            context.allow_requirement_check_override,
            context.disable_check_for_duplicates,
        )

    def __get_prepared_validation_plan__(self, context: ValidationContext) -> PreparedValidationPlan:
        key = self.__prepared_validation_plan_key__(context)
        plan = self.__prepared_validation_plans.get(key)
        if plan is None:
            profiles = tuple(context.__load_profiles__())
            ontology_graph = Graph()
            for profile in profiles:
                # Materialize lazy requirements and their per-profile shape
                # registries once. Contextual graphs passed to pySHACL are still
                # copied for every validation run.
                _ = profile.requirements
                ontology_path = profile.path / "ontology.ttl"
                if ontology_path.exists():
                    ontology_graph.parse(
                        ontology_path,
                        format="ttl",
                        publicID=context.effective_ontology_base,
                    )
            plan = PreparedValidationPlan(profiles, ontology_graph)
            self.__prepared_validation_plans[key] = plan
            # Loading may resolve a bare profile token (for example
            # ``ro-crate``) to a versioned identifier and update the settings.
            # Store the canonical key as an alias for subsequent warm runs.
            self.__prepared_validation_plans[self.__prepared_validation_plan_key__(context)] = plan
        return plan

    def clear_prepared_profiles(self) -> None:
        """
        Discard all profile preparation cached by this validator.

        Call this after changing profile files on disk. Existing validation
        results remain valid and keep their own per-run contexts.
        """

        with self.__run_lock:
            self.__prepared_profile_catalogs.clear()
            self.__prepared_validation_plans.clear()

    def prepare(
        self,
        rocrate_uri: str | Path | URI | None = None,
        *,
        metadata_dict: dict | None = None,
        refresh: bool = False,
    ) -> None:
        """
        Eagerly prepare the selected profile for a later validation run.

        By default an instance prepares profiles lazily during its first
        :meth:`validate` call. ``refresh=True`` first discards every catalog and
        plan cached by this validator, which is useful after editing profile
        files in a long-running process.
        """

        settings = self.__settings_for_run__(self.validation_settings, rocrate_uri, metadata_dict)
        with self.__run_lock:
            if refresh:
                self.__prepared_profile_catalogs.clear()
                self.__prepared_validation_plans.clear()
            context = ValidationContext(self, settings)
            _ = context.prepared_validation_plan

    @staticmethod
    def __settings_for_run__(
        settings: ValidationSettings,
        rocrate_uri: str | Path | URI | None,
        metadata_dict: dict | None,
    ) -> ValidationSettings:
        if rocrate_uri is not None and metadata_dict is not None:
            raise ValueError("rocrate_uri and metadata_dict are mutually exclusive")
        if rocrate_uri is None and metadata_dict is None:
            # Preserve the established behavior, including writing a resolved
            # bare profile identifier back to the caller's settings.
            return settings

        run_settings = copy.copy(settings)
        if rocrate_uri is not None:
            run_settings.rocrate_uri = URI(str(rocrate_uri))
            run_settings.metadata_dict = None
        else:
            if not isinstance(metadata_dict, dict):
                raise TypeError("metadata_dict must be a dictionary")
            run_settings.metadata_dict = copy.deepcopy(metadata_dict)
            run_settings.metadata_only = True
        return run_settings

    def detect_rocrate_profiles(
        self,
        rocrate_uri: str | Path | URI | None = None,
        *,
        metadata_dict: dict | None = None,
    ) -> list[Profile]:
        """
        Detect the profiles to validate against
        """
        settings = self.__settings_for_run__(self.validation_settings, rocrate_uri, metadata_dict)
        with self.__run_lock:
            return self.__detect_rocrate_profiles__(settings)

    def __detect_rocrate_profiles__(self, settings: ValidationSettings) -> list[Profile]:
        # initialize the validation context
        context = ValidationContext(self, settings)
        candidate_profiles_uris: set[str] = set()
        candidate_profiles_uris.update(context.ro_crate.metadata.get_conforms_to() or [])
        candidate_profiles_uris.update(context.ro_crate.metadata.get_root_data_entity_conforms_to() or [])

        logger.debug("Candidate profiles: %s", candidate_profiles_uris)
        if not candidate_profiles_uris:
            logger.debug("Unable to determine the profile to validate against")
            return []
        # load the profiles
        profiles = []
        candidate_profiles = []
        available_profiles = self.__get_prepared_profile_catalog__(context)
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

    def validate(
        self,
        rocrate_uri: str | Path | URI | None = None,
        *,
        metadata_dict: dict | None = None,
    ) -> ValidationResult:
        """
        Validate the RO-Crate against the detected profiles according to the validation settings
        """
        settings = self.__settings_for_run__(self.validation_settings, rocrate_uri, metadata_dict)
        return self.__do_validate__(settings=settings)

    def validate_requirements(
        self,
        requirements: list[Requirement],
        *,
        include_dependencies: bool = True,
        rocrate_uri: str | Path | URI | None = None,
        metadata_dict: dict | None = None,
    ) -> ValidationResult:
        """
        Validates the RO-Crate against the specified subset of the profile requirements.

        By default, requirements containing transitive check dependencies are added to
        the selected subset. Set ``include_dependencies`` to ``False`` to require the
        caller to provide the complete dependency closure explicitly.
        """
        assert all(isinstance(requirement, Requirement) for requirement in requirements), "Invalid requirement type"
        resolved_requirements = RequirementLoader.dependency_closure(
            requirements,
            include_dependencies=include_dependencies,
        )
        settings = self.__settings_for_run__(self.validation_settings, rocrate_uri, metadata_dict)
        return self.__do_validate__(resolved_requirements, settings=settings)

    def __do_validate__(
        self,
        requirements: list[Requirement] | None = None,
        *,
        settings: ValidationSettings,
    ) -> ValidationResult:

        with self.__run_lock:
            return self.__do_validate_locked__(requirements, settings=settings)

    def __do_validate_locked__(  # noqa: C901, PLR0912, PLR0915  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self,
        requirements: list[Requirement] | None,
        *,
        settings: ValidationSettings,
    ) -> ValidationResult:

        # initialize the validation context
        context = ValidationContext(self, settings)
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
            # Requirement objects belong to one prepared plan. Match by stable
            # identifier so a caller can reuse a selection when a per-call
            # crate input selects an equivalent plan for another RDF base.
            selected_requirement_ids = (
                None if requirements is None else {requirement.identifier for requirement in requirements}
            )
            self.notify(EventType.VALIDATION_START)
            for profile_index, profile in enumerate(profiles):
                logger.debug(
                    "Validating profile %s (id: %s)",
                    profile.name,
                    profile.identifier,
                )
                # set the target profile in the context
                context._target_validation_profile = profile
                self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_START, profile=profile))
                # perform the requirements validation
                if selected_requirement_ids is None:
                    profile_requirements = profile.get_requirements(
                        context.requirement_severity,
                        exact_match=context.requirement_severity_only,
                    )
                else:
                    profile_requirements = [
                        requirement
                        for requirement in profile.requirements
                        if requirement.identifier in selected_requirement_ids
                    ]
                logger.debug(
                    "Validating profile %s with %s requirements",
                    profile.identifier,
                    len(profile_requirements),
                )
                logger.debug(
                    "For profile %s, validating these %s requirements: %s",
                    profile.identifier,
                    len(profile_requirements),
                    profile_requirements,
                )
                terminate = False
                requirement_index = -1
                for requirement_index in range(len(profile_requirements)):  # pylint: disable=consider-using-enumerate
                    requirement = profile_requirements[requirement_index]
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
                    # Unconditional abort: the metadata is unusable (e.g. not valid JSON),
                    # so stop now instead of reporting false positives from later checks.
                    if context.aborted:
                        logger.debug("Aborting validation: %s", context.abort_reason)
                        terminate = True
                        break
                self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_END, profile=profile))
                if terminate:
                    Requirement.record_skipped_checks(profile_requirements[requirement_index + 1 :], context)
                    for remaining_profile in profiles[profile_index + 1 :]:
                        if selected_requirement_ids is None:
                            remaining_requirements = remaining_profile.get_requirements(
                                context.requirement_severity,
                                exact_match=context.requirement_severity_only,
                            )
                        else:
                            remaining_requirements = [
                                requirement
                                for requirement in remaining_profile.requirements
                                if requirement.identifier in selected_requirement_ids
                            ]
                        Requirement.record_skipped_checks(remaining_requirements, context)
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
        if isinstance(event, RequirementCheckValidationEvent):
            event.set_effective_identity(
                self.__current_context__.effective_check_identifier(event.requirement_check),
                self.__current_context__.effective_check_profile(event.requirement_check).identifier,
            )
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
        # reference to the immutable profile preparation selected for this run
        self._prepared_validation_plan: PreparedValidationPlan | None = None
        # reference to the target profile
        self._target_validation_profile: Profile | None = None
        # reference to the validation result
        self._result: ValidationResult | None = None
        # additional properties for the context
        self._properties: dict = {}
        # URLs already reported as missing from the HTTP cache during this run
        self._offline_cache_misses_warned: set[str] = set()
        # Effective identities are requested by several reporting consumers
        # for the same check during one validation run.
        self._effective_check_cache: dict[tuple[int, int], EffectiveRequirementCheck] = {}
        # flag set when the validation must be aborted because the metadata
        # cannot be read (e.g. the file descriptor is not valid JSON)
        self._aborted: bool = False
        self._abort_reason: str | None = None

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

    def record_skip(
        self,
        check: RequirementCheck,
        message: str,
        category: SkipCategoryInput = SkipCategory.RETURNED,
    ) -> None:
        """Record a structured reason while a check is returning ``SKIPPED``."""
        self.result.record_skip(check, message, category)

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
    def effective_ontology_base(self) -> str:
        """Base used while parsing profile ontology artifacts for this run."""

        try:
            return extract_base_from_jsonld(self.ro_crate.metadata.as_dict()) or self.publicID
        except (ROCrateMetadataNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
            # Profile preparation happens before descriptor checks execute. An
            # unreadable descriptor is validation input, not a preparation
            # failure: use the crate public ID and let the owning checks report
            # the precise missing/JSON/encoding issue in the normal pipeline.
            logger.debug("Unable to read metadata @base while preparing profiles: %s", error)
            return self.publicID

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
    def aborted(self) -> bool:
        """
        Whether the validation has been aborted because the metadata cannot be read.

        Unlike :attr:`fail_fast`, this abort is unconditional: when the file descriptor
        cannot be parsed (e.g. it is not valid JSON) no metadata can be read, so any
        further check would only produce false positives.

        :return: ``True`` if the validation has been aborted, ``False`` otherwise
        :rtype: bool
        """
        return self._aborted

    @property
    def abort_reason(self) -> str | None:
        """
        The reason why the validation has been aborted, if any.
        """
        return self._abort_reason

    def abort_validation(self, reason: str | None = None) -> None:
        """
        Signal that the validation cannot meaningfully continue because the metadata
        is unusable (e.g. the file descriptor is not valid JSON).

        The check that detects the problem is expected to record its issue first and
        then call this method; the validation loop stops as soon as the current
        requirement completes, avoiding false positives from checks that depend on
        readable metadata.

        :param reason: An optional human-readable description of the abort cause
        """
        self._aborted = True
        self._abort_reason = reason
        logger.debug("Validation aborted: %s", reason)

    @property
    def rel_fd_path(self) -> Path:
        """
        The relative path to the file descriptor

        :return: The relative path to the file descriptor
        :rtype: Path
        """
        return Path(self.ro_crate.metadata_descriptor_id)

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
        profiles = list(self.validator.__get_prepared_profile_catalog__(self))

        # Check if the target profile is in the list of profiles. A bare token
        # (e.g. `ro-crate`) resolves to the highest available version.
        try:
            profile = Profile.resolve_in_list(profiles, self.profile_identifier)
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
        # Record the resolved identifier, so that downstream consumers (e.g. the
        # statistics) agree on which profile was actually used.
        if profile.identifier != self.profile_identifier:
            logger.debug("Profile %r resolved to %r", self.profile_identifier, profile.identifier)
            self.settings.profile_identifier = profile.identifier

        # if the inheritance is enabled, return only the target profile
        if not self.inheritance_enabled:
            return [profile]

        # Visit profiles from the most general source to the target.  This is
        # important for both dependency ordering and SHACL composition: source
        # shapes are collected before the target profile performs the single
        # validation run over the complete merged shapes graph.  Python checks
        # that are replaced by an overlay are dispatched at their source slot.
        profiles = [*profile.inherited_profiles, profile]

        # Validate check identities only for profiles participating in this run.
        # Profile listing and discovery may still inspect intentionally invalid
        # fixtures without forcing requirement loading.
        if self.settings.validate_profile_checks:
            for validation_profile in profiles:
                validation_profile.validate_profile_checks()

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
            self._prepared_validation_plan = self.validator.__get_prepared_validation_plan__(self)
            self._profiles = list(self._prepared_validation_plan.profiles)
        return self._profiles.copy()

    @property
    def prepared_validation_plan(self) -> PreparedValidationPlan:
        """Prepared profile state selected for this validation context."""

        if self._prepared_validation_plan is None:
            _ = self.profiles
        assert self._prepared_validation_plan is not None
        return self._prepared_validation_plan

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
        # Overlay validation visits the target before its sources so that
        # target-specific fail-fast checks run first; resolve by identifier
        # instead of relying on the order of the profiles list.
        target = next((profile for profile in profiles if profile.identifier == self.profile_identifier), None)
        return target or profiles[-1]

    def is_rule_overlay_source(self, profile: Profile) -> bool:
        """Return whether ``profile`` is composed into the validation target."""
        target = self.target_profile
        return profile == target or profile.uri in target.is_rule_overlay_of

    def effective_check_identifier(self, check: RequirementCheck) -> str:
        """Return a context-local identifier without mutating the source check."""
        return self.effective_check_provenance(check).identifier

    def effective_check_profile(self, check: RequirementCheck) -> Profile:
        """Return the reporting profile for a check in this validation."""
        return self.effective_check_provenance(check).profile

    def effective_check_provenance(self, check: RequirementCheck) -> EffectiveRequirementCheck:
        """Return and cache the effective identity of ``check`` in this context."""
        target_profile = self.target_profile
        cache_key = (id(target_profile), id(check))
        provenance = self._effective_check_cache.get(cache_key)
        if provenance is None:
            provenance = target_profile.effective_requirement_check(check)
            self._effective_check_cache[cache_key] = provenance
        return provenance

    def is_check_skipped(self, check: RequirementCheck) -> bool:
        """
        Return whether validation settings skip ``check`` under a supported identity.

        A check contributed by an overlay source retains its source identifier
        while exposing a target-local effective identifier. Accepting either
        identity lets callers address the check without mutating its provenance.
        """
        skipped_identifiers = self.settings.skip_checks
        if not skipped_identifiers:
            return False
        check_identifiers = {check.identifier, self.effective_check_identifier(check)}
        return bool(check_identifiers.intersection(skipped_identifiers))

    def effective_check_replacement(self, check: RequirementCheck) -> RequirementCheck | None:
        """
        Return the target-local check replacing ``check``, if any.

        Replacement is resolved against the effective target profile rather
        than the source profile's sibling list.  This keeps execution scoped
        to the profile selected for the current validation and avoids treating
        unrelated profiles loaded in the same registry as active overrides.
        """
        target_profile = self.target_profile
        if check.requirement.profile == target_profile:
            return None
        candidate = target_profile.get_requirement_check(check.name, check.severity)
        if candidate is not None and check in candidate.overrides:
            return candidate
        return None

    def resolve_dependency_check(self, check: RequirementCheck, dependency_name: str) -> RequirementCheck:
        """
        Resolve a named dependency in the active overlay composition.

        Resolution uses the target profile's effective check set, which includes
        inherited checks while excluding definitions shadowed by a more specific
        replacement. Exactly one effective match is required; an absent or
        ambiguous dependency is a profile-definition error.
        """
        matches = RequirementLoader.effective_check_index(self.target_profile).get(dependency_name, [])
        if len(matches) != 1:
            raise CheckDependencyError(
                f"check {check.name!r} depends on unknown or ambiguous check {dependency_name!r}",
                check.requirement.profile.identifier,
            )
        return matches[0]

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
