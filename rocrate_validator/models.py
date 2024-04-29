from __future__ import annotations

import enum
import inspect
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Optional, Union

from rdflib import Graph

from rocrate_validator.constants import (DEFAULT_ONTOLOGY_FILE, DEFAULT_PROFILE_NAME,
                                         DEFAULT_PROFILE_README_FILE,
                                         IGNORED_PROFILE_DIRECTORIES,
                                         PROFILE_FILE_EXTENSIONS,
                                         RDF_SERIALIZATION_FORMATS_TYPES,
                                         ROCRATE_METADATA_FILE,
                                         VALID_INFERENCE_OPTIONS_TYPES)
from rocrate_validator.utils import (get_profiles_path,
                                     get_requirement_name_from_file)

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

logger = logging.getLogger(__name__)

BaseTypes = Union[str, Path, bool, int, None]


@enum.unique
@total_ordering
class Severity(enum.Enum):
    """Enum ordering "strength" of conditions to be verified"""
    OPTIONAL = 0
    RECOMMENDED = 2
    REQUIRED = 4

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self.value < other.value
        else:
            raise TypeError(f"Comparison not supported between instances of {type(self)} and {type(other)}")


@total_ordering
@dataclass
class RequirementLevel:
    name: str
    severity: Severity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementLevel):
            return False
        return self.name == other.name and self.severity == other.severity

    def __lt__(self, other: object) -> bool:
        # TODO: this ordering is not totally coherent, since for two objects a and b
        # with equal Severity but different names you would have
        #       not a < b, which implies a >= b
        #       and also a != b and not a > b, which is incoherent with a >= b
        if not isinstance(other, RequirementLevel):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.severity < other.severity

    def __hash__(self) -> int:
        return hash((self.name, self.severity))

    def __repr__(self) -> str:
        return f'RequirementLevel(name={self.name}, severity={self.severity})'

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.severity.value

    def __index__(self) -> int:
        return self.severity.value


class LevelCollection:
    """
    * The keywords MUST, MUST NOT, REQUIRED,
    * SHALL, SHALL NOT, SHOULD, SHOULD NOT,
    * RECOMMENDED, MAY, and OPTIONAL in this document
    * are to be interpreted as described in RFC 2119.
    """
    OPTIONAL = RequirementLevel('OPTIONAL', Severity.OPTIONAL)
    MAY = RequirementLevel('MAY', Severity.OPTIONAL)

    REQUIRED = RequirementLevel('REQUIRED', Severity.REQUIRED)
    SHOULD = RequirementLevel('SHOULD', Severity.RECOMMENDED)
    SHOULD_NOT = RequirementLevel('SHOULD_NOT', Severity.RECOMMENDED)
    RECOMMENDED = RequirementLevel('RECOMMENDED', Severity.RECOMMENDED)

    MUST = RequirementLevel('MUST', Severity.REQUIRED)
    MUST_NOT = RequirementLevel('MUST_NOT', Severity.REQUIRED)
    SHALL = RequirementLevel('SHALL', Severity.REQUIRED)
    SHALL_NOT = RequirementLevel('SHALL_NOT', Severity.REQUIRED)

    def __init__(self):
        raise NotImplementedError(f"{type(self)} can't be instantiated")

    @staticmethod
    def all() -> list[RequirementLevel]:
        return [level for name, level in inspect.getmembers(LevelCollection)
                if not inspect.isroutine(level)
                and not inspect.isdatadescriptor(level) and not name.startswith('__')]

    @staticmethod
    def get(name: str) -> RequirementLevel:
        return getattr(LevelCollection, name.upper())


@total_ordering
class Profile:
    def __init__(self, name: str, path: Path,
                 requirements: Optional[list[Requirement]] = None,
                 publicID: Optional[str] = None):
        self._path = path
        self._name = name
        self._description: Optional[str] = None
        self._requirements: list[Requirement] = requirements if requirements is not None else []
        self._publicID = publicID

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name

    @property
    def readme_file_path(self) -> Path:
        return self.path / DEFAULT_PROFILE_README_FILE

    @property
    def publicID(self) -> Optional[str]:
        return self._publicID

    @property
    def description(self) -> str:
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with open(self.readme_file_path, "r") as f:
                    self._description = f.read()
            else:
                self._description = "RO-Crate profile"
        return self._description

    def _load_requirements(self) -> None:
        """
        Load the requirements from the profile directory
        """
        def ok_file(p: Path) -> bool:
            return p.is_file() \
                and p.suffix in PROFILE_FILE_EXTENSIONS \
                and not p.name == DEFAULT_ONTOLOGY_FILE \
                and not p.name.startswith('.') \
                and not p.name.startswith('_')

        files = sorted((p for p in self.path.rglob('*.*') if ok_file(p)),
                       key=lambda x: (not x.suffix == '.py', x))

        req_id = 0
        self._requirements = []
        for requirement_path in files:
            requirement_level = requirement_path.parent.name
            for requirement in Requirement.load(
                    self, LevelCollection.get(requirement_level),
                    requirement_path, publicID=self.publicID):
                req_id += 1
                requirement._order_number = req_id
                self.add_requirement(requirement)
        logger.debug("Profile %s loaded %s requirements: %s",
                     self.name, len(self._requirements), self._requirements)

    @property
    def requirements(self) -> list[Requirement]:
        if not self._requirements:
            self._load_requirements()
        return self._requirements

    def get_requirements(
            self, severity: Severity = Severity.REQUIRED,
            exact_match: bool = False) -> list[Requirement]:
        return [requirement for requirement in self.requirements
                if (not exact_match and requirement.severity >= severity) or
                (exact_match and requirement.severity == severity)]

    @property
    def inherited_profiles(self) -> list[Profile]:
        profiles = [
            _ for _ in sorted(
                Profile.load_profiles(self.path.parent).values(), key=lambda x: x, reverse=True)
            if _ < self]
        logger.debug("Inherited profiles: %s", profiles)
        return profiles

    def add_requirement(self, requirement: Requirement):
        self._requirements.append(requirement)

    def remove_requirement(self, requirement: Requirement):
        self._requirements.remove(requirement)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Profile) \
            and self.name == other.name \
            and self.path == other.path \
            and self.requirements == other.requirements

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Profile):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.name < other.name

    def __hash__(self) -> int:
        return hash((self.name, self.path, self.requirements))

    def __repr__(self) -> str:
        return (
            f'Profile(name={self.name}, '
            f'path={self.path}, ' if self.path else ''
            f'requirements={self.requirements})'
        )

    def __str__(self) -> str:
        return self.name

    # def get_requirement(self, name: str) -> Requirement:
    #     for requirement in self.requirements:
    #         if requirement.name == name:
    #             return requirement
    #     return None

    # @property
    # def requirements_by_severity_map(self) -> dict[Severity, list[Requirement]]:
    #     return {level.severity: self.get_requirements_by_type(level.severity)
    #             for level in LevelCollection.all()}

    # def has_requirement(self, name: str) -> bool:
    #     return self.get_requirement(name) is not None

    # def get_requirements_by_type(self, type: RequirementLevel) -> list[Requirement]:
    #     return [requirement for requirement in self.requirements if requirement.severity == type]

    @staticmethod
    def load(path: Union[str, Path], publicID: Optional[str] = None) -> Profile:
        # if the path is a string, convert it to a Path
        if isinstance(path, str):
            path = Path(path)
        # check if the path is a directory
        assert path.is_dir(), f"Invalid profile path: {path}"
        # create a new profile
        profile = Profile(name=path.name, path=path, publicID=publicID)
        logger.debug("Loaded profile: %s", profile)
        return profile

    @staticmethod
    def load_profiles(profiles_path: Union[str, Path], publicID: Optional[str] = None) -> dict[str, Profile]:
        # if the path is a string, convert it to a Path
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        # check if the path is a directory
        assert profiles_path.is_dir(), f"Invalid profiles path: {profiles_path}"
        # initialize the profiles
        profiles = {}
        # iterate through the directories
        for profile_path in profiles_path.iterdir():
            logger.debug("Checking profile path: %s %s %r", profile_path,
                         profile_path.is_dir(), IGNORED_PROFILE_DIRECTORIES)
            if profile_path.is_dir() and profile_path not in IGNORED_PROFILE_DIRECTORIES:
                profile = Profile.load(profile_path, publicID=publicID)
                profiles[profile.name] = profile
        return profiles


@total_ordering
class Requirement(ABC):

    def __init__(self,
                 level: RequirementLevel,
                 profile: Profile,
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None,
                 initialize_checks: bool = True):
        self._order_number: Optional[int] = None
        self._level = level
        self._profile = profile
        self._description = description
        self._path = path  # path of code implementing the requirement
        self._checks: list[RequirementCheck] = []

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
        assert self._order_number is not None
        return self._order_number

    @property
    def identifier(self) -> str:
        return f"{self.level.name} {self.order_number}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> RequirementLevel:
        return self._level

    @property
    def severity(self) -> Severity:
        return self.level.severity

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def description(self) -> str:
        if not self._description:
            self._description = self.__class__.__doc__.strip(
            ) if self.__class__.__doc__ else f"Profile Requirement {self.name}"
        return self._description

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @abstractmethod
    def __init_checks__(self) -> list[RequirementCheck]:
        pass

    def get_checks(self) -> list[RequirementCheck]:
        return self._checks.copy()

    def get_check(self, name: str) -> Optional[RequirementCheck]:
        for check in self._checks:
            if check.name == name:
                return check
        return None

    def __reorder_checks__(self) -> None:
        for i, check in enumerate(self._checks):
            check.order_number = i + 1

    def __do_validate__(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the validation
        Returns whether all checks in this requirement passed.
        """
        logger.debug("Validating Requirement %s (level=%s) with %s checks",
                     self.name, self.level, len(self._checks))

        logger.debug("Running %s checks for Requirement '%s'", len(self._checks), self.name)
        all_passed = True
        for check in self._checks:
            try:
                logger.debug("Running check '%s' - Desc: %s", check.name, check.description)
                check_result = check.execute_check(context)
                logger.debug("Ran check '%s'. Got result %s", check.name, check_result)
                if not isinstance(check_result, bool):
                    logger.warning("Ignoring the check %s as it returned the value %r instead of a boolean", check.name)
                    raise RuntimeError(f"Ignoring invalid result from check {check.name}")
                all_passed = all_passed and check_result
            except Exception as e:
                # Ignore the fact that the check failed as far as the validation result is concerned.
                logger.warning("Unexpected error during check %s.  Exception: %s", check, e)
                logger.warning("Consider reporting this as a bug.")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)

        logger.debug("Checks for Requirement '%s' completed. Checks passed? %s", self.name, all_passed)
        return all_passed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.name == other.name \
            and self.severity == other.severity and self.description == other.description \
            and self.path == other.path

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.severity, self.description, self.path))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return (self.level, self._order_number, self.name) < (other.level, other._order_number, other.name)

    def __repr__(self):
        return (
            f'ProfileRequirement('
            f'_order_number={self._order_number}, '
            f'name={self.name}, '
            f'level={self.level}, '
            f'description={self.description}'
            f', path={self.path}, ' if self.path else ''
            ')'
        )

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def load(profile: Profile,
             requirement_level: RequirementLevel,
             file_path: Path,
             publicID: Optional[str] = None) -> list[Requirement]:
        # initialize the set of requirements
        requirements: list[Requirement] = []

        # if the path is a string, convert it to a Path
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # TODO: implement a better way to identify the requirement level and class
        # check if the file is a python file
        if file_path.suffix == ".py":
            from rocrate_validator.requirements.python import PyRequirement
            py_requirements = PyRequirement.load(profile, requirement_level, file_path)
            requirements.extend(py_requirements)
            logger.debug("Loaded Python requirements: %r", py_requirements)
        elif file_path.suffix == ".ttl":
            # from rocrate_validator.requirements.shacl.checks import SHACLCheck
            from rocrate_validator.requirements.shacl.requirements import \
                SHACLRequirement
            shapes_requirements = SHACLRequirement.load(profile, requirement_level,
                                                        file_path, publicID=publicID)
            requirements.extend(shapes_requirements)
            logger.debug("Loaded SHACL requirements: %r", shapes_requirements)
        else:
            logger.warning("Requirement type not supported: %s. Ignoring file %s", file_path.suffix, file_path)

        return requirements


@total_ordering
class RequirementCheck(ABC):

    def __init__(self,
                 requirement: Requirement,
                 name: str,
                 description: Optional[str] = None):
        self._requirement: Requirement = requirement
        self._order_number = 0
        self._name = name
        self._description = description

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
        return self.requirement.level

    @property
    def severity(self) -> Severity:
        return self.requirement.level.severity

    @abstractmethod
    def execute_check(self, context: ValidationContext) -> bool:
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise ValueError(f"Cannot compare RequirementCheck with {type(other)}")
        return self.requirement == other.requirement and self.name == other.name

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise ValueError(f"Cannot compare RequirementCheck with {type(other)}")
        return (self.requirement, self.name) < (other.requirement, other.name)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.requirement, self.name or ""))

    # TODO: delete these?
    #
    # @property
    # def issues(self) -> list[CheckIssue]:
    #    """Return the issues found during the check"""
    #    assert self.result, "Issues not set before the check"
    #    return self.result.get_issues_by_check(self, Severity.OPTIONAL)

    # def get_issues_by_severity(self, severity: Severity = Severity.RECOMMENDED) -> list[CheckIssue]:
    #    return self.result.get_issues_by_check_and_severity(self, severity)


# TODO: delete this?

# def issue_types(issues: list[Type[CheckIssue]]) -> Type[RequirementCheck]:
#     def class_decorator(cls):
#         cls.issue_types = issues
#         return cls
#     return class_decorator


@total_ordering
class CheckIssue:
    """
    Class to store an issue found during a check

    Attributes:
        severity (IssueSeverity): The severity of the issue
        message (str): The message
        code (int): The code
        check (RequirementCheck): The check that generated the issue
    """

    # TODO:
    # 2. CheckIssue has the check, so it is able to determine the level and the Severity
    #    without having it provided through an additional argument.
    def __init__(self, severity: Severity,
                 check: RequirementCheck,
                 message: Optional[str] = None):
        if not isinstance(severity, Severity):
            raise TypeError(f"CheckIssue constructed with a severity '{severity}' of type {type(severity)}")
        self._severity = severity
        self._message = message
        self._check: RequirementCheck = check

    @property
    def message(self) -> Optional[str]:
        """The message associated with the issue"""
        return self._message

    @property
    def level(self) -> RequirementLevel:
        """The level of the issue"""
        return self._check.level

    @property
    def severity(self) -> Severity:
        """Severity of the RequirementLevel associated with this check."""
        return self._severity

    @property
    def level_name(self) -> str:
        return self.level.name

    @property
    def check(self) -> RequirementCheck:
        """The check that generated the issue"""
        return self._check

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CheckIssue) and \
            self._check == other._check and \
            self._severity == other._severity and \
            self._message == other._message

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CheckIssue):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return (self._check, self._severity, self._message) < (other._check, other._severity, other._message)

    # @property
    # def code(self) -> int:
    #     breakpoint()
    #     # If the code has not been set, calculate it
    #     if not self._code:
    #         """
    #         Calculate the code based on the severity, the class name and the message.
    #         - All issues with the same severity, class name and message will have the same code.
    #         - All issues with the same severity and class name but different message will have different codes.
    #         - All issues with the same severity but different class name and message will have different codes.
    #         - All issues with the same severity should start with the same number.
    #         - All codes should be positive numbers.
    #         """
    #         # Concatenate the level, class name and message into a single string
    #         issue_string = self.level.name + self.__class__.__name__ + str(self.message)
    #
    #         # Use the built-in hash function to generate a unique code for this string
    #         # The modulo operation ensures that the code is a positive number
    #         self._code = hash(issue_string) % ((1 << 31) - 1)
    #     # Return the code
    #     return self._code


class ValidationResult:

    def __init__(self, rocrate_path: Path, validation_settings: Optional[dict[str, BaseTypes]] = None):
        # reference to the ro-crate path
        self._rocrate_path = rocrate_path
        # reference to the validation settings
        self._validation_settings: dict[str, BaseTypes] = \
            validation_settings if validation_settings is not None else {}
        # keep track of the issues found during the validation
        self._issues: list[CheckIssue] = []

    @property
    def rocrate_path(self):
        return self._rocrate_path

    @property
    def validation_settings(self):
        return self._validation_settings

    #  --- Issues ---
    @property
    def issues(self) -> list[CheckIssue]:
        return self._issues

    def get_issues(self, min_severity: Severity) -> list[CheckIssue]:
        return [issue for issue in self._issues if issue.severity >= min_severity]

    def get_issues_by_check(self,
                            check: RequirementCheck,
                            min_severity: Severity = Severity.OPTIONAL) -> list[CheckIssue]:
        return [issue for issue in self._issues if issue.check == check and issue.severity >= min_severity]

    # def get_issues_by_check_and_severity(self, check: RequirementCheck, severity: Severity) -> list[CheckIssue]:
    #     return [issue for issue in self.issues if issue.check == check and issue.severity == severity]

    def has_issues(self, severity: Severity = Severity.OPTIONAL) -> bool:
        return any(issue.severity >= severity for issue in self._issues)

    def passed(self, severity: Severity = Severity.OPTIONAL) -> bool:
        return not any(issue.severity >= severity for issue in self._issues)

    def add_issue(self, issue: CheckIssue):
        self._issues.append(issue)

    def add_check_issue(self,
                        message: str,
                        check: RequirementCheck,
                        severity: Optional[Severity] = None) -> CheckIssue:
        sev_value = severity if severity is not None else check.requirement.severity
        c = CheckIssue(sev_value, check, message)
        self._issues.append(c)
        return c

    def add_error(self, message: str, check: RequirementCheck) -> CheckIssue:
        return self.add_check_issue(message, check, Severity.REQUIRED)

    #  --- Requirements ---
    @property
    def failed_requirements(self) -> Collection[Requirement]:
        return set(issue.check.requirement for issue in self._issues)

    #  --- Checks ---
    @property
    def failed_checks(self) -> Collection[RequirementCheck]:
        return set(issue.check for issue in self._issues)

    def get_failed_checks_by_requirement(self, requirement: Requirement) -> Collection[RequirementCheck]:
        return [check for check in self.failed_checks if check.requirement == requirement]

    def get_failed_checks_by_requirement_and_severity(
            self, requirement: Requirement, severity: Severity) -> Collection[RequirementCheck]:
        return [check for check in self.failed_checks
                if check.requirement == requirement
                and check.severity == severity]

    def __str__(self) -> str:
        return f"Validation result: {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(issues={self._issues})"


class Validator:
    """
    Can validate conformance to a single Profile (including any requirements
    inherited by parent profiles).
    """

    def __init__(self,
                 rocrate_path: Path,
                 profiles_path: Path = DEFAULT_PROFILES_PATH,
                 profile_name: str = DEFAULT_PROFILE_NAME,
                 disable_profile_inheritance: bool = False,
                 requirement_severity: Severity = Severity.REQUIRED,
                 requirement_severity_only: bool = False,
                 ontology_path: Optional[Path] = None,
                 advanced: Optional[bool] = False,
                 inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
                 inplace: Optional[bool] = False,
                 abort_on_first: Optional[bool] = True,
                 allow_infos: Optional[bool] = False,
                 allow_warnings: Optional[bool] = False,
                 serialization_output_path: Optional[Path] = None,
                 serialization_output_format: RDF_SERIALIZATION_FORMATS_TYPES = "turtle",
                 **kwargs):
        self.rocrate_path = rocrate_path
        self.profiles_path = profiles_path
        self.profile_name = profile_name
        self.requirement_severity = requirement_severity
        self.requirement_severity_only = requirement_severity_only
        self.disable_profile_inheritance = disable_profile_inheritance

        self._validation_settings: dict[str, BaseTypes] = {
            'advanced': advanced,
            'inference': inference,
            'inplace': inplace,
            'abort_on_first': abort_on_first,
            'allow_infos': allow_infos,
            'allow_warnings': allow_warnings,
            'serialization_output_path': serialization_output_path,
            'serialization_output_format': serialization_output_format,
            'publicID': rocrate_path,
            **kwargs,
        }

        # TODO: implement custom ontology file ???
        supported_path = f"{self.profiles_path}/{self.profile_name}/{DEFAULT_ONTOLOGY_FILE}"
        if ontology_path:
            logger.warning("Detected an ontology path. Custom ontology file is not yet supported."
                           f"Use {supported_path} to provide an ontology for your profile.")
        # overwrite the ontology path if the custom ontology file is provided
        ontology_path = supported_path

        # reference to the data graph
        self._data_graph = None
        # reference to the list of profiles to load
        self._profiles: list[Profile] = None
        # reference to the path of the ontologies
        self._ontology_path = ontology_path
        # reference to the graph of shapes
        self._ontologies_graph = None
        # flag to indicate if the ontologies graph has been initialized
        self._ontology_graph_initialized = False

    @property
    def validation_settings(self) -> dict[str, BaseTypes]:
        return self._validation_settings

    @property
    def rocrate_metadata_path(self):
        return f"{self.rocrate_path}/{ROCRATE_METADATA_FILE}"

    @property
    def profile_path(self):
        return f"{self.profiles_path}/{self.profile_name}"

    @property
    def ontology_path(self):
        return self._ontology_path

    def load_data_graph(self):
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata: %s", self.rocrate_metadata_path)
        _ = data_graph.parse(self.rocrate_metadata_path,
                             format="json-ld", publicID=self.publicID)
        logger.debug("RO-Crate metadata loaded: %s", data_graph)
        return data_graph

    def get_data_graph(self, refresh: bool = False):
        # load the data graph
        if not self._data_graph or refresh:
            self._data_graph = self.load_data_graph()
        return self._data_graph

    @property
    def data_graph(self) -> Graph:
        return self.get_data_graph()

    @property
    def profiles(self) -> list[Profile]:
        if not self._profiles:
            profile = Profile.load(self.profile_path, publicID=self.publicID)
            self._profiles = [profile]
            if not self.disable_profile_inheritance:
                logger.debug("disabling profile inheritance not active. Loading inherited profiles.")
                self._profiles.extend(profile.inherited_profiles)
                logger.debug("Inherited profiles: %s", self._profiles)
        return self._profiles

    @property
    def publicID(self) -> str:
        path = str(self.rocrate_path)
        if not path.endswith("/"):
            return f"{path}/"
        return path

    def load_ontology_graph(self):
        # load the graph of ontologies
        ontologies_graph = None
        if self._ontology_path:
            if os.path.exists(self.ontology_path):
                logger.debug("Loading ontologies: %s", self.ontology_path)
                ontologies_graph = Graph()
                ontologies_graph.parse(self.ontology_path, format="ttl",
                                       publicID=self.publicID)
        return ontologies_graph

    @property
    def ontology_graph(self) -> Graph:
        if not self._ontology_graph_initialized:
            # load the graph of ontologies
            self._ontologies_graph = self.load_ontology_graph()
            self._ontology_graph_initialized = True
        return self._ontologies_graph

    def validate_requirements(self, requirements: list[Requirement]) -> ValidationResult:
        # check if requirement is an instance of Requirement
        assert all(isinstance(requirement, Requirement) for requirement in requirements), \
            "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def validate(self) -> ValidationResult:
        return self.__do_validate__()

    def __do_validate__(self, requirements: Optional[list[Requirement]] = None) -> ValidationResult:
        # set the profiles to validate against
        profiles = self.profiles
        logger.debug("Profiles to validate: %s", profiles)

        # initialize the validation context
        validation_result = ValidationResult(
            rocrate_path=self.rocrate_path, validation_settings=self.validation_settings)
        context = ValidationContext(self, validation_result)

        for profile in profiles:
            logger.debug("Validating profile %s", profile.name)
            # perform the requirements validation
            if not requirements:
                requirements = profile.get_requirements(
                    self.requirement_severity, exact_match=self.requirement_severity_only)
            logger.debug("For profile %s, validating these %s requirements: %s",
                         profile.name, len(requirements), requirements)
            for requirement in requirements:
                passed = requirement.__do_validate__(context)
                logger.debug("Number of issues: %s", len(context.result.issues))
                if passed:
                    logger.debug("Validation Requirement passed")
                else:
                    logger.debug(f"Validation Requirement {requirement} failed ")
                    if self.validation_settings.get("abort_on_first") is True:
                        logger.debug("Aborting on first requirement failure")
                        return validation_result

        return context.result

    #  ------------ Dead code? ------------
    # @classmethod
    # def load_graph_of_shapes(cls, requirement: Requirement, publicID: Optional[str] = None) -> Graph:
    #     shapes_graph = Graph()
    #     _ = shapes_graph.parse(requirement.path, format="ttl", publicID=publicID)
    #     return shapes_graph

    # def load_graphs_of_shapes(self):
    #     # load the graph of shapes
    #     shapes_graphs = {}
    #     for requirement in self._profile.requirements:
    #         if requirement.path.suffix == ".ttl":
    #             shapes_graph = Graph()
    #             shapes_graph.parse(requirement.path, format="ttl",
    #                                publicID=self.publicID)
    #             shapes_graphs[requirement.name] = shapes_graph
    #     return shapes_graphs

    # def get_graphs_of_shapes(self, refresh: bool = False):
    #     # load the graph of shapes
    #     if not self._shapes_graphs or refresh:
    #         self._shapes_graphs = self.load_graphs_of_shapes()
    #     return self._shapes_graphs

    # @property
    # def shapes_graphs(self) -> dict[str, Graph]:
    #     return self.get_graphs_of_shapes()

    # def get_graph_of_shapes(self, requirement_name: str, refresh: bool = False):
    #     # load the graph of shapes
    #     if not self._shapes_graphs or refresh:
    #         self._shapes_graphs = self.load_graphs_of_shapes()
    #     return self._shapes_graphs.get(requirement_name)


class ValidationContext:

    def __init__(self, validator: Validator, result: ValidationResult):
        self._validator = validator
        self._result = result

    @property
    def validator(self) -> Validator:
        return self._validator

    @property
    def result(self) -> ValidationResult:
        return self._result

    @property
    def settings(self) -> dict:
        return self.validator.validation_settings

    @property
    def rocrate_path(self) -> Path:
        assert isinstance(self.validator.rocrate_path, Path)
        return self.validator.rocrate_path

    @property
    def file_descriptor_path(self) -> Path:
        return self.rocrate_path / ROCRATE_METADATA_FILE

    @property
    def rel_fd_path(self) -> Path:
        return Path(ROCRATE_METADATA_FILE)
