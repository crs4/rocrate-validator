from __future__ import annotations

import bisect
import enum
import inspect
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Collection
from dataclasses import asdict, dataclass
from functools import total_ordering
from pathlib import Path
from typing import Optional, Union

from rdflib import Graph

import rocrate_validator.log as logging
from rocrate_validator.constants import (DEFAULT_ONTOLOGY_FILE,
                                         DEFAULT_PROFILE_NAME,
                                         DEFAULT_PROFILE_README_FILE,
                                         IGNORED_PROFILE_DIRECTORIES,
                                         PROFILE_FILE_EXTENSIONS,
                                         RDF_SERIALIZATION_FORMATS_TYPES,
                                         ROCRATE_METADATA_FILE,
                                         VALID_INFERENCE_OPTIONS_TYPES)
from rocrate_validator.errors import (DuplicateRequirementCheck,
                                      InvalidProfilePath, ProfileNotFound)
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
                 publicID: Optional[str] = None,
                 severity: Severity = Severity.REQUIRED):
        self._path = path
        self._name = name
        self._description: Optional[str] = None
        self._requirements: list[Requirement] = requirements if requirements is not None else []
        self._publicID = publicID
        self._severity = severity

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
    def severity(self) -> Severity:
        return self._severity

    @property
    def description(self) -> str:
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with open(self.readme_file_path, "r") as f:
                    self._description = f.read()
            else:
                self._description = "RO-Crate profile"
        return self._description

    @property
    def requirements(self) -> list[Requirement]:
        if not self._requirements:
            self._requirements = \
                RequirementLoader.load_requirements(self, severity=self.severity)
        return self._requirements

    def get_requirements(
            self, severity: Severity = Severity.REQUIRED,
            exact_match: bool = False) -> list[Requirement]:
        return [requirement for requirement in self.requirements
                if (not exact_match and requirement.severity >= severity) or
                (exact_match and requirement.severity == severity)]

    @property
    def inherited_profiles(self) -> list[Profile]:
        profiles = [_ for _ in Profile.load_profiles(self.path.parent).values() if _ < self]
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
    def load(path: Union[str, Path],
             publicID: Optional[str] = None,
             severity:  Severity = Severity.REQUIRED) -> Profile:
        # if the path is a string, convert it to a Path
        if isinstance(path, str):
            path = Path(path)
        # check if the path is a directory
        if not path.is_dir():
            raise InvalidProfilePath(path)
        # create a new profile
        profile = Profile(name=path.name, path=path, publicID=publicID, severity=severity)
        logger.debug("Loaded profile: %s", profile)
        return profile

    @staticmethod
    def load_profiles(profiles_path: Union[str, Path],
                      publicID: Optional[str] = None,
                      severity:  Severity = Severity.REQUIRED,
                      reverse_order: bool = False) -> OrderedDict[str, Profile]:
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
                profile = Profile.load(profile_path, publicID=publicID, severity=severity)
                profiles[profile.name] = profile

        return OrderedDict(sorted(profiles.items(), key=lambda x: x, reverse=reverse_order))


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
    @abstractmethod
    def hidden(self) -> bool:
        pass

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

    def get_checks_by_level(self, level: RequirementLevel) -> list[RequirementCheck]:
        return [check for check in self._checks if check.level.severity == level.severity]

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
                logger.debug("Running check '%s' - Desc: %s - overridden: %s.%s",
                             check.name, check.description, check.overridden_by,
                             check.overridden_by.requirement.profile if check.overridden_by else None)
                if check.overridden:
                    logger.debug("Skipping check '%s' because overridden by '%s'", check.name, check.overridden_by.name)
                    continue
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
        elif requirement_path.suffix == ".ttl":
            return "shacl"
        else:
            raise ValueError(f"Unsupported requirement type: {requirement_path.suffix}")

    @classmethod
    def __get_requirement_loader__(cls, profile: Profile, requirement_path: Path) -> RequirementLoader:
        import importlib
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
    def load_requirements(profile: Profile, severity: Severity = None) -> list[Requirement]:
        """
        Load the requirements related to the profile
        """
        def ok_file(p: Path) -> bool:
            return p.is_file() \
                and p.suffix in PROFILE_FILE_EXTENSIONS \
                and not p.name == DEFAULT_ONTOLOGY_FILE \
                and not p.name.startswith('.') \
                and not p.name.startswith('_')

        files = sorted((p for p in profile.path.rglob('*.*') if ok_file(p)),
                       key=lambda x: (not x.suffix == '.py', x))

        requirements = []
        for requirement_path in files:
            requirement_level = None
            try:
                requirement_level = LevelCollection.get(requirement_path.parent.name)
                if requirement_level.severity < severity:
                    continue
            except AttributeError:
                logger.debug("The requirement level could not be determined from the path: %s", requirement_path)
            requirement_loader = RequirementLoader.__get_requirement_loader__(profile, requirement_path)
            for requirement in requirement_loader.load(
                    profile, requirement_level,
                    requirement_path, publicID=profile.publicID):
                requirements.append(requirement)
        # sort the requirements by severity
        requirements = sorted(requirements, key=lambda x: x.level.severity, reverse=True)
        # assign order numbers to requirements
        for i, requirement in enumerate(requirements):
            requirement._order_number = i + 1
        # log and return the requirements
        logger.debug("Profile %s loaded %s requirements: %s",
                     profile.name, len(requirements), requirements)
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
        self._overridden_by: RequirementCheck = None

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

    @property
    def overridden_by(self) -> RequirementCheck:
        return self._overridden_by

    @overridden_by.setter
    def overridden_by(self, value: RequirementCheck) -> None:
        assert value is None or isinstance(value, RequirementCheck) and value != self, \
            f"Invalid value for overridden_by: {value}"
        self._overridden_by = value

    @property
    def overridden(self) -> bool:
        return self._overridden_by is not None

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
        return (self.requirement, self.identifier) < (other.requirement, other.identifier)

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
                 message: Optional[str] = None,
                 resultPath: Optional[str] = None,
                 focusNode: Optional[str] = None,
                 value: Optional[str] = None):
        if not isinstance(severity, Severity):
            raise TypeError(f"CheckIssue constructed with a severity '{severity}' of type {type(severity)}")
        self._severity = severity
        self._message = message
        self._check: RequirementCheck = check
        self._resultPath = resultPath
        self._focusNode = focusNode
        self._value = value

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

    @property
    def resultPath(self) -> Optional[str]:
        return self._resultPath

    @property
    def focusNode(self) -> Optional[str]:
        return self._focusNode

    @property
    def value(self) -> Optional[str]:
        return self._value

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

    def __init__(self, context: ValidationContext):
        # reference to the validation context
        self._context = context
        # reference to the ro-crate path
        self._rocrate_path = context.rocrate_path
        # reference to the validation settings
        self._validation_settings: dict[str, BaseTypes] = context.settings
        # keep track of the issues found during the validation
        self._issues: list[CheckIssue] = []

    @property
    def context(self) -> ValidationContext:
        return self._context

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
        bisect.insort(self._issues, issue)

    def add_check_issue(self,
                        message: str,
                        check: RequirementCheck,
                        severity: Optional[Severity] = None,
                        resultPath: Optional[str] = None,
                        focusNode: Optional[str] = None,
                        value: Optional[str] = None) -> CheckIssue:
        sev_value = severity if severity is not None else check.requirement.severity
        c = CheckIssue(sev_value, check, message, resultPath=resultPath, focusNode=focusNode, value=value)
        # self._issues.append(c)
        bisect.insort(self._issues, c)
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


@dataclass
class ValidationSettings:

    # Data settings
    data_path: Path
    # Profile settings
    profiles_path: Path = DEFAULT_PROFILES_PATH
    profile_name: str = DEFAULT_PROFILE_NAME
    inherit_profiles: bool = True
    allow_shapes_override: bool = True
    # Ontology and inference settings
    ontology_path: Optional[Path] = None
    inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None
    # Validation strategy settings
    advanced: bool = True  # enable SHACL Advanced Validation
    inplace: Optional[bool] = False
    abort_on_first: Optional[bool] = True
    inplace: Optional[bool] = False
    meta_shacl: bool = False
    iterate_rules: bool = True
    target_only_validation: bool = True
    # Requirement severity settings
    requirement_severity: Union[str, Severity] = Severity.REQUIRED
    requirement_severity_only: bool = False
    allow_infos: Optional[bool] = False
    allow_warnings: Optional[bool] = False
    # Output serialization settings
    serialization_output_path: Optional[Path] = None
    serialization_output_format: RDF_SERIALIZATION_FORMATS_TYPES = "turtle"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # if requirement_severity is a str, convert to Severity
        severity = getattr(self, "requirement_severity")
        if isinstance(severity, str):
            setattr(self, "requirement_severity", Severity[severity])

    def to_dict(self):
        return asdict(self)

    @classmethod
    def parse(cls, settings: Union[dict, ValidationSettings]) -> ValidationSettings:
        """
        Parse the settings into a ValidationSettings object

        Args:
            settings (Union[dict, ValidationSettings]): The settings to parse

        Returns:
            ValidationSettings: The parsed settings

        Raises:
            ValueError: If the settings type is invalid
        """
        if isinstance(settings, dict):
            return cls(**settings)
        elif isinstance(settings, ValidationSettings):
            return settings
        else:
            raise ValueError(f"Invalid settings type: {type(settings)}")


class Validator:
    """
    Can validate conformance to a single Profile (including any requirements
    inherited by parent profiles).
    """

    def __init__(self, settings: Union[str, ValidationSettings]):
        self._validation_settings = ValidationSettings.parse(settings)

    @property
    def validation_settings(self) -> ValidationSettings:
        return self._validation_settings

    def validate(self) -> ValidationResult:
        return self.__do_validate__()

    def validate_requirements(self, requirements: list[Requirement]) -> ValidationResult:
        # check if requirement is an instance of Requirement
        assert all(isinstance(requirement, Requirement) for requirement in requirements), \
            "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def __do_validate__(self,
                        requirements: Optional[list[Requirement]] = None) -> ValidationResult:

        # initialize the validation context
        context = ValidationContext(self, self.validation_settings.to_dict())

        # set the profiles to validate against
        profiles = context.profiles.values()
        logger.debug("Profiles to validate: %r", profiles)

        for profile in profiles:
            logger.debug("Validating profile %s", profile.name)
            # perform the requirements validation
            requirements = profile.get_requirements(
                context.requirement_severity, exact_match=context.requirement_severity_only)
            logger.debug("Validating profile %s with %s requirements", profile.name, len(requirements))
            logger.debug("For profile %s, validating these %s requirements: %s",
                         profile.name, len(requirements), requirements)
            for requirement in requirements:
                passed = requirement.__do_validate__(context)
                logger.debug("Number of issues: %s", len(context.result.issues))
                if passed:
                    logger.debug("Validation Requirement passed")
                else:
                    logger.debug(f"Validation Requirement {requirement} failed ")
                    if context.settings.get("abort_on_first") is True and context.profile_name == profile.name:
                        logger.debug("Aborting on first requirement failure")
                        return context.result

        return context.result


class ValidationContext:

    def __init__(self, validator: Validator, settings: dict[str, object]):
        # reference to the validator
        self._validator = validator
        # reference to the settings
        self._settings = settings
        # reference to the data graph
        self._data_graph = None
        # reference to the profiles
        self._profiles = None
        # reference to the validation result
        self._result = None
        # additional properties for the context
        self._properties = {}

    @property
    def validator(self) -> Validator:
        return self._validator

    @property
    def result(self) -> ValidationResult:
        if self._result is None:
            self._result = ValidationResult(self)
        return self._result

    @property
    def settings(self) -> dict[str, object]:
        return self._settings

    @property
    def publicID(self) -> str:
        path = str(self.rocrate_path)
        if not path.endswith("/"):
            return f"{path}/"
        return path

    @property
    def profiles_path(self) -> Path:
        profiles_path = self.settings.get("profiles_path")
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        return profiles_path

    @property
    def requirement_severity(self) -> Severity:
        return self.settings.get("requirement_severity", Severity.REQUIRED)

    @property
    def requirement_severity_only(self) -> bool:
        return self.settings.get("requirement_severity_only", False)

    @property
    def rocrate_path(self) -> Path:
        return self.settings.get("data_path")

    @property
    def file_descriptor_path(self) -> Path:
        return self.rocrate_path / ROCRATE_METADATA_FILE

    @property
    def fail_fast(self) -> bool:
        return self.settings.get("abort_on_first", True)

    @property
    def rel_fd_path(self) -> Path:
        return Path(ROCRATE_METADATA_FILE)

    def __load_data_graph__(self):
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata: %s", self.file_descriptor_path)
        _ = data_graph.parse(self.file_descriptor_path,
                             format="json-ld", publicID=self.publicID)
        logger.debug("RO-Crate metadata loaded: %s", data_graph)
        return data_graph

    def get_data_graph(self, refresh: bool = False):
        # load the data graph
        if not self._data_graph or refresh:
            self._data_graph = self.__load_data_graph__()
        return self._data_graph

    @property
    def data_graph(self) -> Graph:
        return self.get_data_graph()

    @property
    def inheritance_enabled(self) -> bool:
        return self.settings.get("inherit_profiles", False)

    @property
    def profile_name(self) -> str:
        return self.settings.get("profile_name")

    def __load_profiles__(self) -> OrderedDict[str, Profile]:
        if not self.inheritance_enabled:
            profile = Profile.load(
                self.profiles_path / self.profile_name,
                publicID=self.publicID,
                severity=self.requirement_severity)
            return {profile.name: profile}
        profiles = {pn: p for pn, p in Profile.load_profiles(
            self.profiles_path,
            publicID=self.publicID,
            severity=self.requirement_severity,
            reverse_order=False).items() if pn <= self.profile_name}
        # Check if the target profile is in the list of profiles
        if self.profile_name not in profiles:
            raise ProfileNotFound(f"Profile '{self.profile_name}' not found in '{self.profiles_path}'")

        # navigate the profiles and check for overridden checks
        # if the override is enabled in the settings
        # overridden checks should be marked as such
        # otherwise, raise an error
        profiles_checks = {}
        # visit the profiles in reverse order
        # (the order is important to visit the most specific profiles first)
        for profile in sorted(profiles.values(), reverse=True):
            profile_checks = [_ for r in profile.get_requirements() for _ in r.get_checks()]
            profile_check_names = []
            for check in profile_checks:
                #  find duplicated checks and raise an error
                if check.name in profile_check_names:
                    raise DuplicateRequirementCheck(check.name, profile.name)
                #  add check to the list
                profile_check_names.append(check.name)
                #  mark overridden checks
                check_chain = profiles_checks.get(check.name, None)
                if not check_chain:
                    profiles_checks[check.name] = [check]
                elif self.settings.get("allow_shapes_override", True):
                    check.overridden_by = check_chain[-1]
                    check_chain.append(check)
                else:
                    raise DuplicateRequirementCheck(check.name, profile.name)

        return profiles

    @property
    def profiles(self) -> OrderedDict[str, Profile]:
        if not self._profiles:
            self._profiles = self.__load_profiles__()
        return self._profiles.copy()
