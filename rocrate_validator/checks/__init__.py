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


class CheckIssue:
    """
    Class to store an issue found during a check

    Attributes:
        severity (CheckIssue.IssueSeverity): The severity of the issue
        message (str): The message
        code (int): The code
    """
    class IssueSeverity(Enum):
        INFO = auto()
        MAY = auto()
        SHOULD = auto()
        SHOULD_NOT = auto()
        WARNING = auto()
        MUST = auto()
        MUST_NOT = auto()
        ERROR = auto()

    def __init__(self, severity: IssueSeverity, message: Optional[str] = None, code: int = None):
        self._severity = severity
        self._message = message
        self._code = code

    @property
    def message(self) -> str:
        """The message associated with the issue"""
        return self._message

    @property
    def severity(self) -> str:
        """The severity of the issue"""
        return self._severity

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

    def get_issues(self, severity: CheckIssue.IssueSeverity = CheckIssue.IssueSeverity.WARNING) -> List[CheckIssue]:
        return self.result.get_issues(severity)

    def get_issues_by_severity(self, severity: CheckIssue.IssueSeverity) -> List[CheckIssue]:
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
        self._issues.append(issue)

    def add_error(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.ERROR, message, code))

    def add_warning(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.WARNING, message, code))

    def add_info(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.INFO, message, code))

    def add_optional(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.OPTIONAL, message, code))

    def add_may(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.MAY, message, code))

    def add_should(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.SHOULD, message, code))

    def add_should_not(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.SHOULD_NOT, message, code))

    def add_must(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.MUST, message, code))

    def add_must_not(self, message: str, code: int = None):
        self._issues.append(CheckIssue(CheckIssue.IssueSeverity.MUST_NOT, message, code))

    def get_issues(self, severity: CheckIssue.IssueSeverity = CheckIssue.IssueSeverity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.severity.value >= severity.value]

    def get_issues_by_severity(self, severity: CheckIssue.IssueSeverity) -> List[CheckIssue]:
        return [issue for issue in self.issues if issue.severity == severity]

    def passed(self, severity: CheckIssue.IssueSeverity = CheckIssue.IssueSeverity.WARNING) -> bool:
        return not any(issue.severity.value >= severity.value for issue in self.issues)


    """
    Load all the classes from the directory
    """
    logger.debug("Loading checks from %s", directory)
    # create an empty list to store the classes
    classes = {}
    # loop through the files in the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # check if the file is a python file
            logger.debug("Checking file %s", file)
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
                            and obj.__name__.endswith('Check'):
                        classes[obj.__name__] = obj
                        logger.debug("Loaded class %s", obj.__name__)
                return [v() if instances else v for v in classes.values()]

    # return the list of classes
    return classes
