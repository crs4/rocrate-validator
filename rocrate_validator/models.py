from __future__ import annotations

import inspect
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Type, Union

from rdflib import Graph

from rocrate_validator.constants import (RDF_SERIALIZATION_FORMATS_TYPES, ROCRATE_METADATA_FILE,
                                         VALID_INFERENCE_OPTIONS_TYPES)
from rocrate_validator.utils import (get_classes_from_file,
                                     get_file_descriptor_path,
                                     get_requirement_name_from_file)

logger = logging.getLogger(__name__)


@dataclass
class RequirementType:
    name: str
    value: int

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __ne__(self, other):
        return self.name != other.name or self.value != other.value

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __hash__(self):
        return hash((self.name, self.value))

    def __repr__(self):
        return f'RequirementType(name={self.name}, severity={self.value})'


class RequirementLevels:
    """
    * The key words MUST, MUST NOT, REQUIRED,
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


class Profile:
    def __init__(self, name: str, path: Path = None,
                 requirements: Set[Requirement] = None):
        self._path = path
        self._name = name
        self._requirements = requirements if requirements else []

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name

    @property
    def requirements(self) -> List[Requirement]:
        return self._requirements

    def get_requirement(self, name: str) -> Requirement:
        for requirement in self.requirements:
            if requirement.name == name:
                return requirement
        return None

    def load_requirements(self) -> List[Requirement]:
        """
        Load the requirements from the profile directory
        """
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
                    self.add_requirement(requirement)
        return self._requirements

    @property
    def requirements(self) -> List[Requirement]:
        if not self._requirements:
            self.load_requirements()
        return self._requirements
    def has_requirement(self, name: str) -> bool:
        return self.get_requirement(name) is not None

    def get_requirements_by_type(self, type: RequirementType) -> List[Requirement]:
        return [requirement for requirement in self.requirements if requirement.type == type]

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

        return profile


class Requirement:

    def __init__(self,
                 check_class: Type[Check],
                 type: RequirementType,
                 profile: Profile,
                 name: str = None,
                 description: str = None,
                 path: Path = None):
        self._name = name
        self._type = type
        self._profile = profile
        self._description = description
        self._path = path
        self._check_class = check_class

        if not self._name and self._path:
            self._name = get_requirement_name_from_file(self._path)

    @property
    def name(self) -> str:
        if not self._name and self._path:
            return get_requirement_name_from_file(self._path)
        return self._name

    @property
    def type(self) -> RequirementType:
        return self._type

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def description(self) -> str:
        return self._description

    @property
    def path(self) -> Path:
        return self._path

    @property
    def check_class(self) -> Type[Check]:
        return self._check_class

    # def validate(self, rocrate_path: Path) -> CheckResult:
    #     assert self.check_class, "Check class not associated with requirement"
    #     # instantiate the check class
    #     check = self.check_class(self, rocrate_path)
    #     # run the check
    #     check.__do_check__()
    #     # return the result
    #     return check.result

    def __eq__(self, other):
        return self.name == other.name \
            and self.type == other.type and self.description == other.description \
            and self.path == other.path

    def __ne__(self, other):
        return self.name != other.name \
            or self.type != other.type \
            or self.description != other.description \
            or self.path != other.path

    def __hash__(self):
        return hash((self.name, self.type, self.description, self.path))

    def __repr__(self):
        return (
            f'ProfileRequirement('
            f'name={self.name}, '
            f'type={self.type}, '
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

        # check if the file is a python file
        if file_path.suffix == ".py":
            classes = get_classes_from_file(file_path, filter_class=Check)
            logger.debug("Classes: %r" % classes)

            # instantiate a requirement for each class
            for check_name, check_class in classes.items():
                r = Requirement(
                    check_class, requirement_type, profile, path=file_path,
                    name=get_requirement_name_from_file(file_path, check_name=check_name)
                )
                logger.debug("Added Requirement: %r" % r)
                requirements.append(r)
        elif file_path.suffix == ".ttl":
            from rocrate_validator.requirements.shacl.checks import SHACLCheck
            r = Requirement(SHACLCheck, requirement_type,
                            profile, path=file_path)
            requirements.append(r)
            logger.debug("Added Requirement: %r" % r)
        else:
            logger.warning("Requirement type not supported: %s", file_path.suffix)

        return requirements


def issue_types(issues: List[Type[CheckIssue]]) -> Type[Check]:
    def class_decorator(cls):
        cls.issue_types = issues
        return cls
    return class_decorator


class Severity(RequirementLevels):
    """Extends the RequirementLevels enum with additional values"""
    INFO = RequirementType('INFO', 0)
    WARNING = RequirementType('WARNING', 2)
    ERROR = RequirementType('ERROR', 4)


class CheckResult:
    """
    Class to store the result of a check

    Attributes:
        check (Check): The check that was performed
        code (int): The result code
        message (str): The message
    """

    def __init__(self, check: Check):
        self.check = check
        self._issues: List[CheckIssue] = []

    @property
    def issues(self) -> List[CheckIssue]:
        return self._issues

    def add_issue(self, issue: CheckIssue):
        issue._check = self.check
        self._issues.append(issue)

    def add_error(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.ERROR, message, code, self.check))

    def add_warning(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.WARNING, message, code, self.check))

    def add_info(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.INFO, message, code, self.check))

    def add_optional(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.OPTIONAL, message, code, self.check))

    def add_may(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.MAY, message, code, self.check))

    def add_should(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.SHOULD, message, code, self.check))

    def add_should_not(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.SHOULD_NOT, message, code, self.check))

    def add_must(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.MUST, message, code, self.check))

    def add_must_not(self, message: str, code: int = None):
        self._issues.append(CheckIssue(Severity.MUST_NOT, message, code, self.check))

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.severity.value >= severity.value]

    def get_issues_by_severity(self, severity: Severity) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.severity == severity]

    def passed(self, severity: Severity = Severity.WARNING) -> bool:
        return not any(issue.severity.value >= severity.value for issue in self.issues)


class Check(ABC):
    """
    Base class for checks
    """

    def __init__(self,
                 requirement: Requirement,
                 validator: Validator,
                 name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        self._requirement = requirement
        self._validator = validator
        self._name = name
        self._description = description
        # create a result object for the check
        self._result: CheckResult = CheckResult(self)

    @property
    def requirement(self) -> Requirement:
        return self._requirement

    @property
    def severity(self) -> Severity:
        return self._requirement.type

    @property
    def name(self) -> str:
        if not self._name:
            return self.__class__.__name__.replace("Check", "")
        return self._name

    @property
    def description(self) -> str:
        if not self._description:
            return self.__doc__.strip()
        return self._description

    @property
    def ro_crate_path(self) -> Path:
        return self._validator.rocrate_path

    @property
    def file_descriptor_path(self) -> Path:
        return get_file_descriptor_path(self.ro_crate_path)

    @property
    def result(self) -> CheckResult:
        return self._result

    @property
    def validator(self) -> Validator:
        return self._validator

    def __do_check__(self) -> bool:
        """
        Internal method to perform the check
        """
        # Check if the check has issue types defined
        # TODO: check if this is necessary
        # assert self.issue_types, "Check must have issue types defined in the decorator"
        # Perform the check
        try:
            return self.check()
        except Exception as e:
            self.result.add_error(str(e))
            logger.error("Unexpected error during check: %s", e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False

    @abstractmethod
    def check(self) -> bool:
        raise NotImplementedError("Check not implemented")

    def passed(self, severity: Severity = Severity.WARNING) -> bool:
        return self.result.passed(severity)

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return self.result.get_issues(severity)

    def get_issues_by_severity(self, severity: Severity) -> List[CheckIssue]:
        return self.result.get_issues_by_severity(severity)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}Check()"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Check):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


class CheckIssue:
    """
    Class to store an issue found during a check

    Attributes:
        severity (IssueSeverity): The severity of the issue
        message (str): The message
        code (int): The code
    """

    def __init__(self, severity: Severity,
                 message: Optional[str] = None,
                 code: int = None,
                 check: Check = None):
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
    def check(self) -> Check:
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
        self._issues: List[CheckIssue] = []
        self._rocrate_path = rocrate_path
        self._validation_settings = validation_settings

    def get_rocrate_path(self):
        return self._rocrate_path

    def get_validation_settings(self):
        return self._validation_settings

    def get_failed_checks(self) -> Set[Check]:
        # return the set of checks that failed
        return set([issue.check for issue in self._issues])

    def add_issue(self, issue: CheckIssue):
        self._issues.append(issue)

    def add_issues(self, issues: List[CheckIssue]):
        self._issues.extend(issues)

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity.value >= severity.value]

    def get_issues_by_severity(self, severity: Severity) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity == severity]

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
                 requirement_level="MUST",
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
        self.requirement_level = requirement_level
        self.requirement_level_only = requirement_level_only
        self.ontologies_path = ontologies_path

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

    def validate_requirement(self, requirement: Requirement) -> CheckResult:
        # check if requirement is an instance of Requirement
        assert isinstance(requirement, Requirement), "Invalid requirement"
        # check if the requirement has a check class
        assert requirement.check_class, "Check class not associated with requirement"
        # instantiate the check class
        check = requirement.check_class(requirement, self)
        # run the check
        check.__do_check__()
        # return the result
        return check.result

    def validate(self) -> ValidationResult:

        # initialize the validation result
        validation_result = ValidationResult(
            rocrate_path=self.rocrate_path, validation_settings=self.validation_settings)

        # perform the requirements validation
        for requirement in self.profile.requirements:
            logger.debug("Validating Requirement: %s", requirement)
            result = self.validate_requirement(requirement)
            logger.debug("Issues: %r", result.get_issues())
            if result and result.passed():
                logger.debug("Validation Requirement passed: %s", requirement)
            else:
                logger.debug(f"Validation Requirement {requirement} failed ")
                validation_result.add_issues(result.get_issues())
                if self.validation_settings.get("abort_on_first"):
                    logger.debug("Aborting on first failure")
                    return validation_result

        return validation_result
