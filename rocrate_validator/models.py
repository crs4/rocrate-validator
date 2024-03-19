from __future__ import annotations

import inspect
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Type, Union

from rdflib import Graph

from rocrate_validator.constants import (DEFAULT_PROFILE_README_FILE,
                                         IGNORED_PROFILE_DIRECTORIES,
                                         PROFILE_FILE_EXTENSIONS,
                                         RDF_SERIALIZATION_FORMATS_TYPES,
                                         ROCRATE_METADATA_FILE,
                                         VALID_INFERENCE_OPTIONS_TYPES)
from rocrate_validator.utils import (get_classes_from_file,
                                     get_requirement_name_from_file)

from .errors import OutOfValidationContext

logger = logging.getLogger(__name__)


@dataclass
class RequirementType:
    name: str
    value: int

    def __eq__(self, other):
        if not isinstance(other, RequirementType):
            return False
        return self.name == other.name and self.value == other.value

    def __ne__(self, other):
        if not isinstance(other, RequirementType):
            return True
        return self.name != other.name or self.value != other.value

    def __lt__(self, other):
        if not isinstance(other, RequirementType):
            raise ValueError(f"Cannot compare RequirementType with {type(other)}")
        return self.value < other.value

    def __le__(self, other):
        if not isinstance(other, RequirementType):
            raise ValueError(f"Cannot compare RequirementType with {type(other)}")
        return self.value <= other.value

    def __gt__(self, other):
        if not isinstance(other, RequirementType):
            raise ValueError(f"Cannot compare RequirementType with {type(other)}")
        return self.value > other.value

    def __ge__(self, other):
        if not isinstance(other, RequirementType):
            raise ValueError(f"Cannot compare RequirementType with {type(other)}")
        return self.value >= other.value

    def __hash__(self):
        return hash((self.name, self.value))

    def __repr__(self):
        return f'RequirementType(name={self.name}, severity={self.value})'

    def __str__(self):
        return self.name

    def __int__(self):
        return self.value

    def __index__(self):
        return self.value


class RequirementLevels:
    """
    * The keywords MUST, MUST NOT, REQUIRED,
    * SHALL, SHALL NOT, SHOULD, SHOULD NOT,
    * RECOMMENDED, MAY, and OPTIONAL in this document
    * are to be interpreted as described in RFC 2119.
    """
    MAY = RequirementType('MAY', 1)
    OPTIONAL = RequirementType('OPTIONAL', 1)
    SHOULD = RequirementType('SHOULD', 2)
    SHOULD_NOT = RequirementType('SHOULD_NOT', 2)
    REQUIRED = RequirementType('REQUIRED', 3)
    MUST = RequirementType('MUST', 3)
    MUST_NOT = RequirementType('MUST_NOT', 3)
    SHALL = RequirementType('SHALL', 3)
    SHALL_NOT = RequirementType('SHALL_NOT', 3)
    RECOMMENDED = RequirementType('RECOMMENDED', 3)

    def all() -> Dict[str, RequirementType]:
        return {name: member for name, member in inspect.getmembers(RequirementLevels)
                if not inspect.isroutine(member)
                and not inspect.isdatadescriptor(member) and not name.startswith('__')}

    @staticmethod
    def get(name: str) -> RequirementType:
        return RequirementLevels.all()[name.upper()]


class Severity(RequirementLevels):
    """Extends the RequirementLevels enum with additional values"""
    INFO = RequirementType('INFO', 0)
    WARNING = RequirementType('WARNING', 2)
    ERROR = RequirementType('ERROR', 4)


class Profile:
    def __init__(self, name: str, path: Path = None,
                 requirements: Set[Requirement] = None):
        self._path = path
        self._name = name
        self._description = None
        self._requirements = requirements if requirements else []

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
    def description(self) -> str:
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with open(self.readme_file_path, "r") as f:
                    self._description = f.read()
            else:
                self._description = "RO-Crate profile"
        return self._description

    def get_requirement(self, name: str) -> Requirement:
        for requirement in self.requirements:
            if requirement.name == name:
                return requirement
        return None

    def load_requirements(self) -> List[Requirement]:
        """
        Load the requirements from the profile directory
        """
        req_id = 0
        self._requirements = []
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs
                       if not d.startswith('.') and not d.startswith('_')]
            requirement_root = Path(root)
            requirement_level = requirement_root.name
            # Filter out files that start with a dot or underscore
            files = [_ for _ in files if not _.startswith('.')
                     and not _.startswith('_')
                     and Path(_).suffix in PROFILE_FILE_EXTENSIONS]
            for file in sorted(files, key=lambda x: (not x.endswith('.py'), x)):
                requirement_path = requirement_root / file
                for requirement in Requirement.load(
                        self, RequirementLevels.get(requirement_level), requirement_path):
                    req_id += 1
                    requirement._order_number = req_id
                    self.add_requirement(requirement)
        return self._requirements

    @property
    def requirements(self) -> List[Requirement]:
        if not self._requirements:
            self.load_requirements()
        return self._requirements

    def get_requirements(
            self, severity: RequirementType = RequirementLevels.MUST,
            exact_match: bool = False) -> List[Requirement]:
        return [requirement for requirement in self.requirements
                if not exact_match and requirement.severity >= severity or
                exact_match and requirement.severity == severity]

    @property
    def requirements_by_severity_map(self) -> Dict[RequirementType, List[Requirement]]:
        return {severity: self.get_requirements_by_type(severity)
                for severity in RequirementLevels.all().values()}

    @property
    def inherited_profiles(self) -> List[Profile]:
        profiles = [
            _ for _ in sorted(
                Profile.load_profiles(self.path.parent).values(), key=lambda x: x, reverse=True)
            if _ < self]
        logger.debug("Inherited profiles: %s", profiles)
        return profiles

    def has_requirement(self, name: str) -> bool:
        return self.get_requirement(name) is not None

    def get_requirements_by_type(self, type: RequirementType) -> List[Requirement]:
        return [requirement for requirement in self.requirements if requirement.severity == type]

    def add_requirement(self, requirement: Requirement):
        self._requirements.append(requirement)

    def remove_requirement(self, requirement: Requirement):
        self._requirements.remove(requirement)

    def validate(self, rocrate_path: Path) -> ValidationResult:
        pass

    def __eq__(self, other) -> bool:
        return self.name == other.name and self.path == other.path and self.requirements == other.requirements

    def __ne__(self, other) -> bool:
        return self.name != other.name or self.path != other.path or self.requirements != other.requirements

    def __lt__(self, other) -> bool:
        return self.name < other.name

    def __le__(self, other) -> bool:
        return self.name <= other.name

    def __gt__(self, other) -> bool:
        return self.name > other.name

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

    @staticmethod
    def load(path: Union[str, Path]) -> Profile:
        # if the path is a string, convert it to a Path
        if isinstance(path, str):
            path = Path(path)
        # check if the path is a directory
        assert path.is_dir(), f"Invalid profile path: {path}"
        # create a new profile
        profile = Profile(name=path.name, path=path)
        logger.debug("Loaded profile: %s", profile)
        return profile

    @staticmethod
    def load_profiles(profiles_path: Union[str, Path]) -> Dict[str, Profile]:
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
                profile = Profile.load(profile_path)
                profiles[profile.name] = profile
        return profiles


def check(name=None):
    def decorator(func):
        func.check = True
        func.name = name if name else func.__name__
        return func
    return decorator


class RequirementCheck(ABC):

    def __init__(self,
                 requirement: Requirement,
                 name: str,
                 check: Callable,
                 description: str = None):
        self._requirement: Requirement = requirement
        self._order_number = None
        self._name = name
        self._description = description
        self._check = check
        # declare the reference to the validation context
        self._validation_context: ValidationContext = None
        # declare the reference to the validator
        self._validator: Validator = None
        # declare the result of the check
        self._result: ValidationResult = None

    @property
    def order_number(self) -> int:
        return self._order_number

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
    def validation_context(self) -> ValidationContext:
        assert self._validation_context, "Validation context not set before the check"
        return self._validation_context

    @property
    def validator(self) -> Validator:
        assert self._validator, "Validator not set before the check"
        return self._validator

    @property
    def result(self) -> ValidationResult:
        assert self._result, "Result not set before the check"
        return self._result

    @property
    def ro_crate_path(self) -> Path:
        assert self.validator, "ro-crate path not set before the check"
        return self.validator.rocrate_path

    @property
    def issues(self) -> List[CheckIssue]:
        """Return the issues found during the check"""
        assert self._result, "Issues not set before the check"
        return self._result.get_issues_by_check(self, Severity.INFO)

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return self._result.get_issues_by_check(self, severity)

    def get_issues_by_severity(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return self._result.get_issues_by_check_and_severity(self, severity)

    @abstractmethod
    def check(self) -> bool:
        raise NotImplementedError("Check not implemented")

    def __do_check__(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the check
        """
        # Set the validation context
        self._validation_context = context
        # Set the validator
        self._validator = context.validator
        # Set the result
        self._result = context.result
        # Perform the check
        return self.check()


class Requirement:

    def __init__(self,
                 severity: RequirementType,
                 profile: Profile,
                 name: str = None,
                 description: str = None,
                 path: Path = None):
        self._order_number = None
        self._name = name
        self._severity = severity
        self._profile = profile
        self._description = description
        self._path = path
        self._checks: List[RequirementCheck] = []

        # reference to the current validation context
        self._validation_context: ValidationContext = None

        if not self._name and self._path:
            self._name = get_requirement_name_from_file(self._path)

    @property
    def order_number(self) -> int:
        return self._order_number

    @property
    def identifier(self) -> str:
        return f"{self.severity}.{self.order_number}"

    @property
    def name(self) -> str:
        if not self._name and self._path:
            return get_requirement_name_from_file(self._path)
        return self._name

    @property
    def severity(self) -> RequirementType:
        return self._severity

    @property
    def color(self) -> str:
        from .colors import get_severity_color
        return get_severity_color(self.severity)

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def description(self) -> str:
        if not self._description:
            # set docs equal to docstring
            docs = self.__class__.__doc__
            self._description = docs.strip() if docs else f"Profile Requirement {self.name}"
        return self._description

    @property
    def path(self) -> Path:
        return self._path

    # write a method to collect the list of decorated check methods
    def __init_checks__(self):
        # initialize the list of checks
        checks = []
        for name, member in inspect.getmembers(self._check_class, inspect.isfunction):
            if hasattr(member, "check"):
                check_name = member.name if hasattr(member, "name") else name
                self._checks.append(RequirementCheck(self, check_name, member, member.__doc__))
        # assign the check ids
        self.__reorder_checks__()
        # return the checks
        return checks

    def get_checks(self) -> List[RequirementCheck]:
        return self._checks.copy()

    def get_check(self, name: str) -> RequirementCheck:
        for check in self._checks:
            if check.name == name:
                return check
        return None

    def __reorder_checks__(self):
        for i, check in enumerate(self._checks):
            check._order_number = i + 1

    def __do_validate__(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the validation
        """
        # Set the validation context
        self._validation_context = context
        logger.debug("Validation context initialized: %r", context)
        # Perform the validation
        try:
            for check in self._checks:
                try:
                    check.__do_check__(context)
                except Exception as e:
                    self.validation_result.add_error("Unexpected error during check: %s" % e, check=check)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception(e)
            # Return the result
            return self.validation_result.passed()
        finally:
            # Clear the validation context
            self._validation_context = None
            logger.debug("Clearing validation context")

    @property
    def validator(self):
        if self._validation_context is None:
            raise OutOfValidationContext("Validation context has not been initialized")
        return self._validation_context.validator

    @property
    def validation_result(self):
        if self._validation_context is None:
            raise OutOfValidationContext("Validation context has not been initialized")
        return self._validation_context.result

    @property
    def validation_context(self):
        if self._validation_context is None:
            raise OutOfValidationContext("Validation context has not been initialized")
        return self._validation_context

    @property
    def validation_settings(self):
        if self._validation_context is None:
            raise OutOfValidationContext("Validation context has not been initialized")
        return self._validation_context.settings

    def __eq__(self, other: Requirement):
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.name == other.name \
            and self.severity == other.severity and self.description == other.description \
            and self.path == other.path

    def __ne__(self, other: Requirement):
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.name != other.name \
            or self.severity != other.type \
            or self.description != other.description \
            or self.path != other.path

    def __hash__(self):
        return hash((self.name, self.severity, self.description, self.path))

    def __lt__(self, other: Requirement) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.severity < other.severity or self.name < other.name

    def __le__(self, other: Requirement) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.severity <= other.severity or self.name <= other.name

    def __gt__(self, other: Requirement) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.severity > other.severity or self.name > other.name

    def __ge__(self, other: Requirement) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return self.severity >= other.severity or self.name >= other.name

    def __repr__(self):
        return (
            f'ProfileRequirement('
            f'name={self.name}, '
            f'severity={self.severity}, '
            f'description={self.description}'
            f', path={self.path}, ' if self.path else ''
            ')'
        )

    def __str__(self):
        return self.name

    @staticmethod
    def load(profile: Profile, requirement_type: RequirementType, file_path: Path) -> List[Requirement]:
        # initialize the set of requirements
        requirements = []

        # TODO: implement a better way to identify the requirement and check classes
        # check if the file is a python file
        if file_path.suffix == ".py":
            classes = get_classes_from_file(file_path, filter_class=RequirementCheck)
            logger.debug("Classes: %r" % classes)

            # instantiate a requirement for each class
            for check_name, check_class in classes.items():
                r = Requirement(
                    requirement_type, profile, path=file_path,
                    name=get_requirement_name_from_file(file_path, check_name=check_name)
                )
                logger.debug("Added Requirement: %r" % r)
                requirements.append(r)
        elif file_path.suffix == ".ttl":
            # from rocrate_validator.requirements.shacl.checks import SHACLCheck
            from rocrate_validator.requirements.shacl.requirements import \
                SHACLRequirement
            shapes_requirements = SHACLRequirement.load(profile, requirement_type, file_path)
            logger.debug("Loaded SHACL requirements: %r" % shapes_requirements)
            requirements.extend(shapes_requirements)
            logger.debug("Added Requirement: %r" % shapes_requirements)
        else:
            logger.warning("Requirement type not supported: %s", file_path.suffix)

        return requirements


def issue_types(issues: List[Type[CheckIssue]]) -> Type[RequirementCheck]:
    def class_decorator(cls):
        cls.issue_types = issues
        return cls
    return class_decorator


class Severity(RequirementLevels):
    """Extends the RequirementLevels enum with additional values"""
    INFO = RequirementType('INFO', 0)
    WARNING = RequirementType('WARNING', 2)
    ERROR = RequirementType('ERROR', 4)


class CheckIssue:
    """
    Class to store an issue found during a check

    Attributes:
        severity (IssueSeverity): The severity of the issue
        message (str): The message
        code (int): The code
        check (RequirementCheck): The check that generated the issue
    """

    def __init__(self, severity: Severity,
                 message: Optional[str] = None,
                 code: int = None,
                 check: RequirementCheck = None):
        self._severity = severity
        self._message = message
        self._code = code
        self._check = check

    @property
    def message(self) -> str:
        """The message associated with the issue"""
        return self._message

    @property
    def severity(self) -> str:
        """The severity of the issue"""
        return self._severity

    @property
    def check(self) -> RequirementCheck:
        """The check that generated the issue"""
        return self._check

    @property
    def code(self) -> int:
        # If the code has not been set, calculate it
        if not self._code:
            """
            Calculate the code based on the severity, the class name and the message.
            - All issues with the same severity, class name and message will have the same code.
            - All issues with the same severity and class name but different message will have different codes.
            - All issues with the same severity but different class name and message will have different codes.
            - All issues with the same severity should start with the same number.
            - All codes should be positive numbers.
            """
            # Concatenate the severity, class name and message into a single string
            issue_string = str(self.severity.value) + self.__class__.__name__ + str(self.message)

            # Use the built-in hash function to generate a unique code for this string
            # The modulo operation ensures that the code is a positive number
            self._code = hash(issue_string) % ((1 << 31) - 1)
        # Return the code
        return self._code


class ValidationResult:

    def __init__(self, rocrate_path: Path, validation_settings: Dict = None):
        # reference to the ro-crate path
        self._rocrate_path = rocrate_path
        # reference to the validation settings
        self._validation_settings = validation_settings
        # keep track of the requirements that have been checked
        self._validated_requirements: Set[Requirement] = set()
        # keep track of the checks that have been performed
        self._checks: Set[RequirementCheck] = set()
        # keep track of the issues found during the validation
        self._issues: List[CheckIssue] = []

    def get_rocrate_path(self):
        return self._rocrate_path

    def get_validation_settings(self):
        return self._validation_settings

    @property
    def validated_requirements(self) -> Set[Requirement]:
        return self._validated_requirements.copy()

    @property
    def failed_requirements(self) -> Set[Requirement]:
        return sorted(set([issue.check.requirement for issue in self._issues]), key=lambda x: x.order_number)

    @property
    def passed_requirements(self) -> Set[Requirement]:
        return sorted(self._validated_requirements - self.failed_requirements, key=lambda req: req.number_order)

    @property
    def checks(self) -> Set[RequirementCheck]:
        return sorted(set(self._checks), key=lambda x: x.order_number)

    @property
    def failed_checks(self) -> Set[RequirementCheck]:
        return sorted(set([issue.check for issue in self._issues]), key=lambda x: x.order_number)

    @property
    def passed_checks(self) -> Set[RequirementCheck]:
        return sorted(self._checks - self.failed_checks, key=lambda x: x.order_number)

    def get_passed_checks_by_requirement(self, requirement: Requirement) -> Set[RequirementCheck]:
        return sorted(
            set([check for check in self.passed_checks if check.requirement == requirement]),
            key=lambda x: x.order_number
        )

    def get_failed_checks_by_requirement(self, requirement: Requirement) -> Set[RequirementCheck]:
        return sorted(
            set([check for check in self.failed_checks if check.requirement == requirement]),
            key=lambda x: x.order_number
        )

    def get_failed_checks_by_requirement_and_severity(
            self, requirement: Requirement, severity: Severity) -> Set[RequirementCheck]:
        return sorted(
            set([check for check in self.failed_checks
                 if check.requirement == requirement
                 and check.severity == severity]),
            key=lambda x: x.order_number
        )

    def add_issue(self, issue: CheckIssue):
        # TODO: check if the issue belongs to the current validation context
        self._issues.append(issue)

    def add_issues(self, issues: List[CheckIssue]):
        # TODO: check if the issues belong to the current validation context
        self._issues.extend(issues)

    def add_error(self, message: str, check: RequirementCheck, code: int = None):
        self._issues.append(CheckIssue(Severity.ERROR, message, code, check=check))

    def add_warning(self, message: str, check: RequirementCheck,  code: int = None):
        self._issues.append(CheckIssue(Severity.WARNING, message, code, check=check))

    def add_info(self, message: str, check: RequirementCheck, code: int = None):
        self._issues.append(CheckIssue(Severity.INFO, message, code, check=check))

    def add_optional(self, message: str, check: RequirementCheck, code: int = None):
        self._issues.append(CheckIssue(Severity.OPTIONAL, message, code, check=check))

    def add_may(self, message: str, check: RequirementCheck, code: int = None):
        self._issues.append(CheckIssue(Severity.MAY, message, code, check=check))

    def add_should(self, message: str, check: RequirementCheck, code: int = None):
        self._issues.append(CheckIssue(Severity.SHOULD, message, code, check=check))

    def add_should_not(self, message: str, check: RequirementCheck,  code: int = None):
        self._issues.append(CheckIssue(Severity.SHOULD_NOT, message, code, check=check))

    def add_must(self, message: str, check: RequirementCheck,  code: int = None):
        self._issues.append(CheckIssue(Severity.MUST, message, code, check=check))

    def add_must_not(self, message: str, check: RequirementCheck,  code: int = None):
        self._issues.append(CheckIssue(Severity.MUST_NOT, message, code, check=check))

    @property
    def issues(self) -> List[CheckIssue]:
        return self._issues

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity.value >= severity.value]

    def get_issues_by_severity(self, severity: Severity) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity == severity]

    def get_issues_by_check(self, check: RequirementCheck, severity: Severity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.check == check and issue.severity.value >= severity.value]

    def get_issues_by_check_and_severity(self, check: RequirementCheck, severity: Severity) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.check == check and issue.severity.value == severity.value]

    def has_issues(self, severity: Severity = Severity.WARNING) -> bool:
        return any(issue.severity.value >= severity.value for issue in self._issues)

    def passed(self, severity: Severity = Severity.WARNING) -> bool:
        return not any(issue.severity.value >= severity.value for issue in self._issues)

    def __str__(self):
        return f"Validation result: {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(issues={self._issues})"


class Validator:

    def __init__(self,
                 rocrate_path: Path,
                 profiles_path: str = "./profiles",
                 profile_name: str = "ro-crate",
                 disable_profile_inheritance: bool = False,
                 requirement_level: Union[str, RequirementType] = RequirementLevels.MUST,
                 requirement_level_only: bool = False,
                 ontologies_path: Optional[Path] = None,
                 advanced: Optional[bool] = False,
                 inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
                 inplace: Optional[bool] = False,
                 abort_on_first: Optional[bool] = False,
                 allow_infos: Optional[bool] = False,
                 allow_warnings: Optional[bool] = False,
                 serialization_output_path: str = None,
                 serialization_output_format: Optional[RDF_SERIALIZATION_FORMATS_TYPES] = "turtle",
                 **kwargs):
        self.rocrate_path = rocrate_path
        self.profiles_path = profiles_path
        self.profile_name = profile_name
        self.disable_profile_inheritance = disable_profile_inheritance
        self.requirement_level = \
            RequirementLevels.get(requirement_level) if isinstance(requirement_level, str) else \
            requirement_level
        self.requirement_level_only = requirement_level_only
        self.ontologies_path = ontologies_path
        self.requirement_level = requirement_level
        self.requirement_level_only = requirement_level_only

        self._validation_settings = {
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
        # self.advanced = advanced
        # self.inference = inference
        # self.inplace = inplace
        # self.abort_on_first = abort_on_first
        # self.allow_infos = allow_infos
        # self.allow_warnings = allow_warnings
        # self.serialization_output_path = serialization_output_path
        # self.serialization_output_format = serialization_output_format
        # self.kwargs = kwargs

        # reference to the data graph
        self._data_graph = None
        # reference to the profile
        self._profile = None
        # reference to the graph of shapes
        self._shapes_graphs = {}
        # reference to the graph of ontologies
        self._ontologies_graph = None

    @property
    def validation_settings(self) -> Dict[str, Union[str, Path, bool, int]]:
        return self._validation_settings

    @property
    def rocrate_metadata_path(self):
        return f"{self.rocrate_path}/{ROCRATE_METADATA_FILE}"

    @property
    def profile_path(self):
        return f"{self.profiles_path}/{self.profile_name}"

    def load_data_graph(self):
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata: %s", self.rocrate_metadata_path)
        data_graph.parse(self.rocrate_metadata_path,
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

    def load_profile(self):
        # load profile
        profile = Profile.load(self.profile_path)
        logger.debug("Profile: %s", profile)
        return profile

    def get_profile(self, refresh: bool = False):
        # load the profile
        if not self._profile or refresh:
            self._profile = self.load_profile()
        return self._profile

    @property
    def profile(self) -> Profile:
        return self.get_profile()

    @property
    def publicID(self) -> str:
        if not self.rocrate_path.endswith("/"):
            return f"{self.rocrate_path}/"
        return self.rocrate_path

    @classmethod
    def load_graph_of_shapes(cls, requirement: Requirement, publicID: str = None) -> Graph:
        shapes_graph = Graph()
        shapes_graph.parse(str(requirement.path), format="ttl", publicID=publicID)
        return shapes_graph

    def load_graphs_of_shapes(self):
        # load the graph of shapes
        shapes_graphs = {}
        for requirement in self._profile.requirements:
            if requirement.path.suffix == ".ttl":
                shapes_graph = Graph()
                shapes_graph.parse(str(requirement.path), format="ttl",
                                   publicID=self.publicID)
                shapes_graphs[requirement.name] = shapes_graph
        return shapes_graphs

    def get_graphs_of_shapes(self, refresh: bool = False):
        # load the graph of shapes
        if not self._shapes_graphs or refresh:
            self._shapes_graphs = self.load_graphs_of_shapes()
        return self._shapes_graphs

    @property
    def shapes_graphs(self) -> Dict[str, Graph]:
        return self.get_graphs_of_shapes()

    def get_graph_of_shapes(self, requirement_name: str, refresh: bool = False):
        # load the graph of shapes
        if not self._shapes_graphs or refresh:
            self._shapes_graphs = self.load_graphs_of_shapes()
        return self._shapes_graphs.get(requirement_name)

    def load_ontologies_graph(self):
        # load the graph of ontologies
        ontologies_graph = Graph()
        if self.ontologies_path:
            ontologies_graph.parse(self.ontologies_path, format="ttl")
        return ontologies_graph

    def get_ontologies_graph(self, refresh: bool = False):
        # load the graph of ontologies
        if not self._ontologies_graph or refresh:
            self._ontologies_graph = self.load_ontologies_graph()
        return self._ontologies_graph

    @property
    def ontologies_graph(self) -> Graph:
        return self.get_ontologies_graph()

    def validate_requirements(self, requirements: List[Requirement]) -> ValidationResult:
        # check if requirement is an instance of Requirement
        assert all(isinstance(requirement, Requirement) for requirement in requirements), \
            "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def validate(self) -> ValidationResult:
        return self.__do_validate__()

    def __do_validate__(self, requirements: List[Requirement] = None) -> ValidationResult:

        # initialize the validation result
        validation_result = ValidationResult(
            rocrate_path=self.rocrate_path, validation_settings=self.validation_settings)

        # list of profiles to validate
        profiles = [self.profile]
        logger.debug("Disable profile inheritance: %s", self.disable_profile_inheritance)
        if not self.disable_profile_inheritance:
            profiles.extend(self.profile.inherited_profiles)
        logger.debug("Profiles to validate: %s", profiles)

        # initialize the validation context
        context = ValidationContext(self, validation_result)

        #
        for profile in profiles:
            # perform the requirements validation
            if not requirements:
                requirements = profile.get_requirements(
                    self.requirement_level, exact_match=self.requirement_level_only)
            for requirement in requirements:
                logger.debug("Validating Requirement: %s", requirement)
                result = requirement.__do_validate__(context)
                logger.debug("Validation Requirement result: %s", result)
                if result:
                    logger.debug("Validation Requirement passed: %s", requirement)
                else:
                    logger.debug(f"Validation Requirement {requirement} failed ")
                    if self.validation_settings.get("abort_on_first"):
                        logger.debug("Aborting on first failure")
                        return validation_result

        return validation_result


class ValidationContext:

    def __init__(self, validator: Validator, result: ValidationResult):
        self._validator = validator
        self._result = result
        self._settings = validator.validation_settings

    @property
    def validator(self) -> Validator:
        return self._validator

    @property
    def result(self) -> ValidationResult:
        return self._result

    @property
    def settings(self) -> Dict:
        return self._settings
