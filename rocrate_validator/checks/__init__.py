from __future__ import annotations

import inspect
import logging
import os
from abc import ABC, abstractmethod
from enum import Enum, auto
from importlib import import_module
from pathlib import Path
from typing import List, Optional, Type

from ..utils import get_config, get_file_descriptor_path

# set up logging
logger = logging.getLogger(__name__)

# current directory
__CURRENT_DIR__ = os.path.dirname(os.path.realpath(__file__))


def issue_types(issues: List[Type[CheckIssue]]) -> Type[Check]:
    def class_decorator(cls):
        cls.issue_types = issues
        return cls
    return class_decorator


class Severity(Enum):
    """
    * The key words MUST, MUST NOT, REQUIRED,
    * SHALL, SHALL NOT, SHOULD, SHOULD NOT,
    * RECOMMENDED, MAY, and OPTIONAL in this document
    * are to be interpreted as described in RFC 2119.
    """
    INFO = auto()
    MAY = auto()
    OPTIONAL = auto()
    SHOULD = auto()
    SHOULD_NOT = auto()
    WARNING = auto()
    ERROR = auto()
    REQUIRED = auto()
    MUST = auto()
    MUST_NOT = auto()
    SHALL = auto()
    SHALL_NOT = auto()
    RECOMMENDED = auto()


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
            issue_string = str(self._severity.value) + self.__class__.__name__ + str(self._message)

            # Use the built-in hash function to generate a unique code for this string
            # The modulo operation ensures that the code is a positive number
            self._code = hash(issue_string) % ((1 << 31) - 1)
        # Return the code
        return self._code


class Check(ABC):
    """
    Base class for checks
    """

    def __init__(self, ro_crate_path: Path) -> None:
        self._ro_crate_path = ro_crate_path
        # create a result object for the check
        self._result: CheckResult = CheckResult(self)

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Check", "")

    @property
    def description(self) -> str:
        return self.__doc__.strip()

    @property
    def ro_crate_path(self) -> Path:
        return self._ro_crate_path

    @property
    def file_descriptor_path(self) -> Path:
        return get_file_descriptor_path(self.ro_crate_path)

    @property
    def result(self) -> CheckResult:
        return self._result

    def __do_check__(self) -> bool:
        """
        Internal method to perform the check
        """
        # Check if the check has issue types defined
        assert self.issue_types, "Check must have issue types defined in the decorator"
        # Perform the check
        try:
            return self.check()
        except Exception as e:
            self.check.result.add_error(str(e))
            logger.error("Unexpected error during check: %s", e)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False

    @abstractmethod
    def check(self) -> bool:
        raise NotImplementedError("Check not implemented")

    def passed(self) -> bool:
        return self.result.passed()

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


def get_checks(directory: str = __CURRENT_DIR__,
               rocrate_path: Path = ".",
               instances: bool = True,
               skip_dirs: List[str] = None) -> List[Type[Check]]:
    """
    Load all the classes from the directory
    """
    logger.debug("Loading checks from %s", directory)
    # create an empty list to store the classes
    classes = {}
    # skip directories that start with a dot
    skip_dirs = skip_dirs or []
    skip_dirs.extend(get_config(property="skip_dirs"))

    # loop through the files in the directory
    for root, dirs, files in os.walk(directory):
        # skip directories that start with a dot
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        # loop through the files
        for file in files:
            # check if the file is a python file
            logger.debug("Checking file %s %s %s", root, dirs, file)
            if file.endswith(".py") and not file.startswith("__init__"):
                # get the file path
                file_path = os.path.join(root, file)
                # FIXME: works only on the main "general" general directory
                m = '{}.{}'.format(
                    'rocrate_validator.checks', os.path.basename(file_path)[:-3])
                logger.debug("Module: %r" % m)
                # import the module
                mod = import_module(m)
                # loop through the objects in the module
                # and store the classes
                for _, obj in inspect.getmembers(mod):
                    logger.debug("Checking object %s", obj)
                    if inspect.isclass(obj) \
                            and inspect.getmodule(obj) == mod \
                            and issubclass(obj, Check) \
                            and obj.__name__.endswith('Check'):
                        classes[obj.__name__] = obj
                        logger.debug("Loaded class %s", obj.__name__)
                return [v(rocrate_path) if instances else v for v in classes.values()]

    # return the list of classes
    return classes
