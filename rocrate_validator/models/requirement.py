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

import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import total_ordering
from typing import TYPE_CHECKING, Any, cast

from rocrate_validator.constants import (
    DEFAULT_ONTOLOGY_FILE,
    PROFILE_FILE_EXTENSIONS,
    PROFILE_SPECIFICATION_FILE,
)
from rocrate_validator.errors import CheckDependencyError, ROCrateMetadataNotFoundError, ValidationExecutionError
from rocrate_validator.events import EventType
from rocrate_validator.models._logging import logger
from rocrate_validator.models.check_result import CheckResult, CheckResultValue, normalize_check_result
from rocrate_validator.models.severity import (
    LevelCollection,
    RequirementLevel,
    Severity,
)
from rocrate_validator.models.skipped_check import SkipCategory, SkipRequirementCheck
from rocrate_validator.utils.python_helpers import (
    get_requirement_name_from_file,
)

if TYPE_CHECKING:
    from pathlib import Path

    from rocrate_validator.models.profile import Profile
    from rocrate_validator.models.validation import ValidationContext


@total_ordering
class Requirement(ABC):
    """
    Abstract class representing a requirement of a profile.
    A requirement is a named set of checks that can be used to validate an RO-Crate.
    """

    def __init__(
        self,
        profile: Profile,
        name: str = "",
        description: str | None = None,
        path: Path | None = None,
        initialize_checks: bool = True,
    ):
        """
        Initialize the Requirement instance

        :meta private:
        """
        self._order_number: int | None = None
        self._profile = profile
        self._description = description
        self._path = path  # path of code implementing the requirement
        self._level_from_path: RequirementLevel | None = None
        self._checks: list[RequirementCheck] = []
        self._overridden: bool | None = None

        if not name and path:
            self._name = get_requirement_name_from_file(path)
        else:
            self._name = name

        # set flag to indicate if the checks have been initialized
        self._checks_initialized = False
        # initialize the checks if the flag is set
        if initialize_checks:
            _ = self.__init_checks__()
            # assign order numbers to checks
            self.__reorder_checks__()
            # update the checks initialized flag
            self._checks_initialized = True

    @property
    def order_number(self) -> int:
        """
        The order number of the requirement in the profile

        :return: the order number
        :rtype: int
        """
        assert self._order_number is not None
        return self._order_number

    @property
    def identifier(self) -> str:
        """
        The identifier of the requirement

        :return: the identifier
        :rtype: str
        """
        return f"{self.profile.identifier}_{self.relative_identifier}"

    @property
    def relative_identifier(self) -> str:
        """
        The relative identifier of the requirement

        :return: the relative identifier
        :rtype: str

        :meta private:
        """
        return f"{self.order_number}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def severity_from_path(self) -> Severity | None:
        return self.requirement_level_from_path.severity if self.requirement_level_from_path else None

    @property
    def requirement_level_from_path(self) -> RequirementLevel | None:
        if not self._level_from_path and self._path:
            try:
                self._level_from_path = LevelCollection.get(self._path.parent.name)
            except ValueError:
                logger.debug(
                    "The requirement level could not be determined from the path: %s",
                    self._path,
                )
        return self._level_from_path

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def description(self) -> str:
        if not self._description:
            self._description = (
                self.__class__.__doc__.strip() if self.__class__.__doc__ else f"Profile Requirement {self.name}"
            )
        return self._description

    @property
    def overridden(self) -> bool:
        # Check if the requirement has been overridden.
        # The requirement can be considered overridden if all its checks have been overridden
        if self._overridden is None:
            self._overridden = len([_ for _ in self._checks if not _.overridden]) == 0
        return self._overridden

    @property
    @abstractmethod
    def hidden(self) -> bool:
        pass

    @property
    def path(self) -> Path | None:
        return self._path

    @abstractmethod
    def __init_checks__(self) -> list[RequirementCheck]:
        pass

    def get_checks(self) -> list[RequirementCheck]:
        return self._checks.copy()

    def set_checks_order(self, checks: list[RequirementCheck]) -> None:
        """Replace the check order and refresh the public check numbers."""
        self._checks = checks.copy()
        for i, check in enumerate(self._checks, start=1):
            check.order_number = i

    def get_check(self, name: str) -> RequirementCheck | None:
        for check in self._checks:
            if check.name == name:
                return check
        return None

    def get_checks_by_level(self, level: RequirementLevel) -> list[RequirementCheck]:
        return list({check for check in self._checks if check.level.severity == level.severity})

    def __reorder_checks__(self) -> None:
        for i, check in enumerate(self._checks):
            check.order_number = i + 1

    def _do_validate_(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the validation
        Returns whether all checks in this requirement passed.

        :meta private:
        """
        logger.debug(
            "Validating Requirement %s with %s checks",
            self.name,
            len(self._checks),
        )
        all_passed = True
        checks_to_perform = [
            _
            for _ in self._checks
            if not context.settings.skip_checks or _.identifier not in context.settings.skip_checks
        ]
        configured_skips = [check for check in self._checks if check not in checks_to_perform]
        for check in configured_skips:
            context.result._record_check_result(
                check,
                CheckResult.SKIPPED,
                "Check was skipped by validation settings",
                SkipCategory.CONFIGURED,
            )
        processed_checks: set[RequirementCheck] = set()
        for check in checks_to_perform:
            processed_checks.add(check)
            dependency_skip_reason = self.__dependency_skip_reason__(check, context)
            if dependency_skip_reason:
                logger.debug("Skipping check '%s' because: %s", check.name, dependency_skip_reason)
                self.__record_dependency_skip__(check, context, dependency_skip_reason)
                continue
            try:
                all_passed, should_break = self.__execute_check__(check, context, all_passed)
                if should_break:
                    break
            except SkipRequirementCheck as e:
                logger.debug("Skipping check '%s' because: %s", check.name, e)
                self.__record_skipped_check__(check, context, e.message or "Check requested a skip", e.category)
                continue
            except Exception as e:
                self.__handle_check_error__(check, context, e)
            # Stop running further checks once the metadata is known to be unusable.
            if context.aborted:
                break
        self.__record_skipped_checks__(
            configured_skips,
            context,
            "Check was skipped by validation settings",
            SkipCategory.CONFIGURED,
        )
        self.__record_skipped_checks__(
            set(checks_to_perform) - processed_checks,
            context,
            "Validation stopped before this check was executed",
            SkipCategory.NOT_REACHED,
        )
        logger.debug(
            "Checks for Requirement '%s' completed. Checks passed? %s",
            self.name,
            all_passed,
        )
        return all_passed

    @staticmethod
    def __handle_check_error__(check, context, error: Exception) -> None:
        if isinstance(error, (FileNotFoundError, ROCrateMetadataNotFoundError)):
            # A missing descriptor/metadata graph is an input problem reported by
            # the dedicated descriptor checks, not an implementation failure.
            logger.debug("Skipping check %s: validation input is unavailable: %s", check, error)
            return

        if isinstance(error, ValidationExecutionError):
            # An engine-level failure means validation did not complete. Do not
            # turn it into a warning and accidentally return a clean result.
            raise error.with_traceback(error.__traceback__)

        if context.maybe_warn_offline_cache_miss(error):
            logger.debug("Offline cache miss during check %s: %s", check, error)
            return

        check_path = str(check.requirement.path) if check.requirement.path else check.identifier
        raise ValidationExecutionError(
            message=f"Unexpected error while executing check '{check.identifier}': {type(error).__name__}: {error}",
            path=check_path,
        ) from error

    @staticmethod
    def __record_skipped_check__(
        check,
        context,
        message: str = "Check was skipped",
        category: SkipCategory = SkipCategory.RETURNED,
    ) -> None:
        from rocrate_validator.models.events import (  # noqa: PLC0415
            RequirementCheckValidationEvent,
        )

        context.result._record_check_result(check, CheckResult.SKIPPED, message, category)
        inherited_reporting_disabled = (
            check.requirement.profile.identifier != context.profile_identifier
            and context.settings.disable_inherited_profiles_issue_reporting
        )
        if not inherited_reporting_disabled:
            context.validator.notify(
                RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_END,
                    check,
                    validation_result=CheckResult.SKIPPED,
                    message=message,
                )
            )

    @classmethod
    def __record_skipped_checks__(
        cls,
        checks,
        context,
        message: str = "Check was skipped",
        category: SkipCategory = SkipCategory.RETURNED,
    ) -> None:
        for check in sorted(checks):
            cls.__record_skipped_check__(check, context, message, category)

    @classmethod
    def record_skipped_checks(cls, requirements: list[Requirement], context: ValidationContext) -> None:
        """Record checks belonging to requirements that validation will not reach."""
        message = "Validation stopped before this check was executed"
        if context.abort_reason:
            message = f"Validation stopped before this check was executed: {context.abort_reason}"
        for requirement in requirements:
            cls.__record_skipped_checks__(requirement.get_checks(), context, message, SkipCategory.NOT_REACHED)

    @staticmethod
    def __dependency_skip_reason__(check, context: ValidationContext) -> str | None:
        if not check.depends_on:
            return None

        blocked_dependencies = []
        for dependency_name in check.depends_on:
            dependency = check.requirement.profile.get_requirement_check(dependency_name)
            if dependency is None:
                raise CheckDependencyError(
                    f"check {check.name!r} depends on unknown check {dependency_name!r}",
                    check.requirement.profile.identifier,
                )
            dependency_result = context.result.get_check_result(dependency)
            if dependency_result is not CheckResult.PASSED:
                result_name = dependency_result.value if dependency_result else "not processed"
                blocked_dependencies.append(f"{dependency.name} ({result_name})")

        if not blocked_dependencies:
            return None
        return "Check dependency did not pass: " + ", ".join(blocked_dependencies)

    @staticmethod
    def __record_dependency_skip__(check, context: ValidationContext, message: str) -> None:
        Requirement.__record_skipped_check__(check, context, message, SkipCategory.DEPENDENCY)

    def __execute_check__(self, check, context, all_passed):
        from rocrate_validator.models.events import (  # noqa: PLC0415
            RequirementCheckValidationEvent,
        )

        if check.overridden and check.requirement.profile.identifier != context.profile_identifier:
            logger.debug(
                "Skipping check '%s' because overridden by '%r'",
                check.identifier,
                [_.identifier for _ in check.overridden_by],
            )
            return all_passed, False
        if check.deactivated:
            logger.debug("Skipping check '%s' because deactivated", check.identifier)
            self.__record_skipped_check__(check, context, "Check is deactivated", SkipCategory.DEACTIVATED)
            return all_passed, False
        # Determine whether to skip event notification for inherited profiles
        skip_event_notify = False
        if (
            check.requirement.profile.identifier != context.profile_identifier
            and context.settings.disable_inherited_profiles_issue_reporting
        ):
            logger.debug(
                "Inherited profiles reporting disabled. "
                "Skipping requirement %s as it belongs to an inherited profile %s",
                check.requirement.identifier,
                check.requirement.profile.identifier,
            )
            skip_event_notify = True
        # Notify the start of the check execution if not skip_event_notify is set to True
        if not skip_event_notify:
            context.validator.notify(
                RequirementCheckValidationEvent(EventType.REQUIREMENT_CHECK_VALIDATION_START, check)
            )
        # Execute the check and get the result
        check_result = check.execute_check(context)
        normalized_result = normalize_check_result(check_result)
        logger.debug("Result of check %s: %s", check.identifier, normalized_result.value)
        skip_message = None
        skip_category = SkipCategory.RETURNED
        if skip_event_notify and normalized_result is CheckResult.SKIPPED:
            skip_message = "Inherited profile issue reporting is disabled"
            skip_category = SkipCategory.INHERITED
        context.result._record_check_result(check, normalized_result, skip_message, skip_category)
        # Notify the end of the check execution if not skip_event_notify is set to True
        if not skip_event_notify:
            context.validator.notify(
                RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_END,
                    check,
                    validation_result=normalized_result,
                    message=skip_message,
                )
            )
        logger.debug(
            "Ran check '%s'. Got result %s",
            check.identifier,
            normalized_result,
        )
        new_all_passed = all_passed and normalized_result is not CheckResult.FAILED
        should_break = normalized_result is CheckResult.FAILED and context.fail_fast
        return new_all_passed, should_break

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.name == other.name and self.description == other.description and self.path == other.path

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.description, self.path))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise TypeError(f"Cannot compare Requirement with {type(other)}")
        return (self._order_number, self.name) < (
            other._order_number,
            other.name,
        )

    def __repr__(self):
        return (
            f"ProfileRequirement("
            f"_order_number={self._order_number}, "
            f"name={self.name}, "
            f"description={self.description}"
            f", path={self.path}, "
            if self.path
            else ")"
        )

    def __str__(self) -> str:
        return self.name

    def to_dict(self, with_profile: bool = True, with_checks: bool = True) -> dict:
        result = {
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "order": self.order_number,
        }
        if with_profile:
            result["profile"] = self.profile.to_dict()
        if with_checks:
            result["checks"] = [_.to_dict(with_requirement=False, with_profile=False) for _ in self._checks]
        return result

    @classmethod
    def initialize(cls, context: ValidationContext) -> None:
        logger.debug(
            "Starting %s requirement initialization for context %s",
            cls.__name__,
            context,
        )
        # do initialization logic here (empty for now)
        logger.debug(
            "Completed %s requirement initialization for context %s",
            cls.__name__,
            context,
        )

    @classmethod
    def finalize(cls, context: ValidationContext) -> None:
        logger.debug(
            "Starting %s requirement finalization for context %s",
            cls.__name__,
            context,
        )
        # do finalization logic here (empty for now)
        logger.debug(
            "Completed %s requirement finalization for context %s",
            cls.__name__,
            context,
        )


class RequirementLoader:
    def __init__(self, profile: Profile):
        self._profile = profile

    @property
    def profile(self) -> Profile:
        return self._profile

    @staticmethod
    def __get_requirement_type__(requirement_path: Path) -> str:
        if requirement_path.suffix == ".py":
            return "python"
        if requirement_path.suffix == ".ttl":
            return "shacl"
        raise ValueError(f"Unsupported requirement type: {requirement_path.suffix}")

    @classmethod
    def __get_requirement_loader__(cls, profile: Profile, requirement_path: Path) -> RequirementLoader:
        requirement_type = cls.__get_requirement_type__(requirement_path)
        loader_instance_name = f"_{requirement_type}_loader_instance"
        loader_instance = getattr(profile, loader_instance_name, None)
        if loader_instance is None:
            module_name = f"rocrate_validator.requirements.{requirement_type}"
            logger.debug("Loading module: %s", module_name)
            module = importlib.import_module(module_name)
            loader_class_name = f"{'Py' if requirement_type == 'python' else 'SHACL'}RequirementLoader"
            loader_class = getattr(module, loader_class_name)
            loader_instance = loader_class(profile)
            setattr(profile, loader_instance_name, loader_instance)
        return loader_instance

    @staticmethod
    def __get_requirement_classes__() -> list[type[Requirement]]:

        # Ensure known requirement modules are imported so subclasses are registered.
        for requirement_type in ("python", "shacl"):
            module_name = f"rocrate_validator.requirements.{requirement_type}"
            importlib.import_module(module_name)

        def all_subclasses(
            base_class: type[Requirement],
        ) -> list[type[Requirement]]:
            result: list[type[Requirement]] = []
            for subcls in base_class.__subclasses__():
                result.append(subcls)
                result.extend(all_subclasses(subcls))
            return result

        return all_subclasses(Requirement)  # type: ignore[type-abstract]

    @staticmethod
    def load_requirements(profile: Profile, severity: Severity = Severity.REQUIRED) -> list[Requirement]:
        """
        Load the requirements related to the profile
        """

        def ok_file(p: Path) -> bool:
            return (
                p.is_file()
                and p.suffix in PROFILE_FILE_EXTENSIONS
                and p.name not in {DEFAULT_ONTOLOGY_FILE, PROFILE_SPECIFICATION_FILE}
                and not p.name.startswith(".")
                and not p.name.startswith("_")
            )

        files = sorted(
            (p for p in profile.path.rglob("*.*") if ok_file(p)),
            key=lambda x: (x.suffix != ".py", x),
        )

        # set the requirement level corresponding to the severity
        requirement_level = LevelCollection.get(severity.name)

        requirements = []
        for requirement_path in files:
            try:
                requirement_level_from_path = LevelCollection.get(requirement_path.parent.name)
                if requirement_level_from_path < requirement_level:
                    continue
            except ValueError:
                logger.debug(
                    "The requirement level could not be determined from the path: %s",
                    requirement_path,
                )
            requirement_loader = RequirementLoader.__get_requirement_loader__(profile, requirement_path)
            requirements.extend(
                cast(Any, requirement_loader).load(  # noqa: TC006
                    profile,
                    requirement_level,
                    requirement_path,
                    publicID=profile.publicID,
                )
            )
        # sort the requirements by severity
        requirements = sorted(
            requirements,
            key=lambda x: (
                (-x.severity_from_path.value, x.path.name, x.name)
                if x.severity_from_path is not None
                else (0, x.path.name, x.name)
            ),
            reverse=False,
        )
        requirements = RequirementLoader.order_by_dependencies(requirements)
        # assign order numbers to requirements
        for i, requirement in enumerate(requirements):
            requirement._order_number = i + 1
        # log and return the requirements
        logger.debug("Profile %s loaded %s requirements: %s", profile.identifier, len(requirements), requirements)
        return requirements

    @staticmethod
    def _check_index(requirements: list[Requirement]) -> dict[str, list[RequirementCheck]]:
        checks_by_name: dict[str, list[RequirementCheck]] = {}
        for requirement in requirements:
            for check in requirement.get_checks():
                checks_by_name.setdefault(check.name, []).append(check)
        return checks_by_name

    @staticmethod
    def _resolve_dependency(
        check: RequirementCheck,
        dependency_name: str,
        checks_by_name: dict[str, list[RequirementCheck]],
    ) -> RequirementCheck:
        candidates = checks_by_name.get(dependency_name, [])
        profile_name = check.requirement.profile.identifier
        if not candidates:
            raise CheckDependencyError(
                f"check {check.name!r} depends on unknown check {dependency_name!r}",
                profile_name,
            )
        if len(candidates) > 1:
            raise CheckDependencyError(
                f"check {check.name!r} depends on ambiguous check {dependency_name!r}",
                profile_name,
            )
        return candidates[0]

    @staticmethod
    def _topological_order(
        nodes: list[Any], edges: dict[int, set[int]], profile_name: str, node_type: str
    ) -> list[Any]:
        indegree = [0] * len(nodes)
        for targets in edges.values():
            for target in targets:
                indegree[target] += 1

        ready = [index for index, degree in enumerate(indegree) if degree == 0]
        ordered_indices: list[int] = []
        while ready:
            ready.sort()
            index = ready.pop(0)
            ordered_indices.append(index)
            for target in sorted(edges.get(index, ())):
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)

        if len(ordered_indices) != len(nodes):
            cycle_nodes = [nodes[index] for index, degree in enumerate(indegree) if degree > 0]
            cycle_names = ", ".join(getattr(node, "name", str(node)) for node in cycle_nodes)
            raise CheckDependencyError(f"dependency cycle detected among {node_type}: {cycle_names}", profile_name)

        return [nodes[index] for index in ordered_indices]

    @classmethod
    def order_by_dependencies(cls, requirements: list[Requirement]) -> list[Requirement]:
        """Apply check dependencies while preserving the baseline requirement order."""
        if not requirements:
            return []

        checks_by_name = cls._check_index(requirements)
        requirement_indices = {id(requirement): index for index, requirement in enumerate(requirements)}
        requirement_edges: dict[int, set[int]] = {}

        for requirement in requirements:
            checks = requirement.get_checks()
            check_indices = {id(check): index for index, check in enumerate(checks)}
            check_edges: dict[int, set[int]] = {}
            for check in checks:
                for dependency_name in check.depends_on:
                    dependency = cls._resolve_dependency(check, dependency_name, checks_by_name)
                    dependency_requirement_index = requirement_indices[id(dependency.requirement)]
                    source_requirement_index = requirement_indices[id(requirement)]
                    if dependency_requirement_index == source_requirement_index:
                        check_edges.setdefault(check_indices[id(dependency)], set()).add(check_indices[id(check)])
                    else:
                        requirement_edges.setdefault(dependency_requirement_index, set()).add(source_requirement_index)

            if check_edges:
                ordered_checks = cls._topological_order(
                    checks,
                    check_edges,
                    requirement.profile.identifier,
                    "checks",
                )
                requirement.set_checks_order(ordered_checks)

        return cls._topological_order(
            requirements,
            requirement_edges,
            requirements[0].profile.identifier,
            "requirements",
        )

    @classmethod
    def dependency_closure(
        cls,
        requirements: list[Requirement],
        *,
        include_dependencies: bool = True,
    ) -> list[Requirement]:
        """Return selected requirements plus their transitive check dependencies."""
        selected: list[Requirement] = []
        selected_ids: set[int] = set()
        queue = list(requirements)

        while queue:
            requirement = queue.pop(0)
            if id(requirement) in selected_ids:
                continue
            selected_ids.add(id(requirement))
            selected.append(requirement)

            profile_requirements = requirement.profile.requirements
            checks_by_name = cls._check_index(profile_requirements)
            for check in requirement.get_checks():
                for dependency_name in check.depends_on:
                    dependency = cls._resolve_dependency(check, dependency_name, checks_by_name)
                    dependency_requirement = dependency.requirement
                    if id(dependency_requirement) in selected_ids:
                        continue
                    if not include_dependencies:
                        raise CheckDependencyError(
                            f"check {check.name!r} depends on {dependency_name!r}, "
                            "but its requirement was not selected",
                            requirement.profile.identifier,
                        )
                    queue.append(dependency_requirement)

        return selected


@dataclass(frozen=True)
class SourceSnippet:
    """
    A snippet of source code backing a :class:`RequirementCheck`.
    :ivar language: language tag for syntax highlighting (e.g. ``"python"``, ``"turtle"``).
    :ivar code: the source code as text.
    :ivar source_path: path to the file the snippet was extracted from, when available.
    """

    language: str
    code: str
    source_path: Path | None = None


@total_ordering
class RequirementCheck(ABC):
    def __init__(
        self,
        requirement: Requirement,
        name: str | None,
        level: RequirementLevel | None = LevelCollection.REQUIRED,
        description: str | None = None,
        hidden: bool | None = None,
        *,
        deactivated: bool = False,
        depends_on: tuple[str, ...] | None = None,
    ):
        self._requirement: Requirement = requirement
        self._order_number = 0
        self._name = name
        self._level = level
        self._description = description
        self._hidden = hidden
        self._deactivated = deactivated
        self._depends_on = tuple(depends_on or ())

    @property
    def order_number(self) -> int:
        return self._order_number

    @order_number.setter
    def order_number(self, value: int) -> None:
        if value < 0:
            raise ValueError("order_number can't be < 0")
        self._order_number = value

    @property
    def identifier(self) -> str:
        return f"{self.requirement.identifier}.{self.order_number}"

    @property
    def relative_identifier(self) -> str:
        return f"{self.level.name} {self.requirement.relative_identifier}.{self.order_number}"

    @property
    def name(self) -> str:
        if not self._name:
            return self.__class__.__name__.replace("Check", "")
        return self._name

    @property
    def description(self) -> str:
        if not self._description:
            return self.__class__.__doc__.strip() if self.__class__.__doc__ else f"Check {self.name}"
        return self._description

    @property
    def requirement(self) -> Requirement:
        return self._requirement

    @property
    def level(self) -> RequirementLevel:
        return self._level or self.requirement.requirement_level_from_path or LevelCollection.REQUIRED

    @property
    def severity(self) -> Severity:
        return self.level.severity

    @property
    def overridden_by(self) -> list[RequirementCheck]:
        overridden_by = []
        for sibling_profile in self.requirement.profile.siblings:
            check = sibling_profile.get_requirement_check(self.name)
            if check:
                overridden_by.append(check)
        return overridden_by

    @property
    def overrides(self) -> list[RequirementCheck]:
        overrides = []
        for parent in self.requirement.profile.parents:
            check = parent.get_requirement_check(self.name)
            if check:
                overrides.append(check)
        return overrides

    @property
    def overridden(self) -> bool:
        return len(self.overridden_by) > 0

    @property
    def deactivated(self) -> bool:
        return self._deactivated

    @property
    def depends_on(self) -> tuple[str, ...]:
        """Names of checks that must run before this check."""
        return self._depends_on

    @property
    def hidden(self) -> bool:
        if self._hidden is not None:
            return self._hidden
        return self.requirement.hidden

    @abstractmethod
    def execute_check(self, context: ValidationContext) -> CheckResultValue:
        raise NotImplementedError()

    def get_source_snippet(self) -> SourceSnippet | None:
        """
        Return the source code that implements this check, or ``None`` if the
        backing source cannot be extracted for this check kind.
        Concrete subclasses should override this method.
        """
        return None

    def to_dict(self, with_requirement: bool = True, with_profile: bool = True) -> dict:
        result = {
            "identifier": self.identifier,
            "label": self.relative_identifier,
            "order": self.order_number,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.name,
            "depends_on": list(self.depends_on),
        }
        if with_requirement:
            result["requirement"] = self.requirement.to_dict(with_profile=with_profile, with_checks=False)
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise TypeError(f"Cannot compare RequirementCheck with {type(other)}")
        return self.requirement == other.requirement and self.name == other.name

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise TypeError(f"Cannot compare RequirementCheck with {type(other)}")
        return (self.requirement, self.identifier) < (
            other.requirement,
            other.identifier,
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.requirement, self.name or ""))
