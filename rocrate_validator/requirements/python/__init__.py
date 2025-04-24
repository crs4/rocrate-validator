# Copyright (c) 2024-2025 CRS4
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

import inspect
import re
from pathlib import Path
from typing import Callable, Optional, Type

import rocrate_validator.log as logging
from rocrate_validator.models import (LevelCollection, Profile, Requirement,
                                      RequirementCheck, RequirementLevel,
                                      RequirementLoader, Severity,
                                      ValidationContext)
from rocrate_validator.utils import get_classes_from_file

# set up logging
logger = logging.getLogger(__name__)


class PyFunctionCheck(RequirementCheck):
    """
    Concrete class that implements a check that calls a function.
    """

    def __init__(self,
                 requirement: Requirement,
                 name: str,
                 check_function: Callable[[RequirementCheck, ValidationContext], bool],
                 description: Optional[str] = None,
                 level: Optional[LevelCollection] = LevelCollection.REQUIRED):
        """
        check_function: a function that accepts an instance of PyFunctionCheck and a ValidationContext.
        """
        super().__init__(requirement, name, description=description, level=level)

        sig = inspect.signature(check_function)
        if len(sig.parameters) != 2:
            raise RuntimeError("Invalid PyFunctionCheck function. Checks are expected to accept "
                               f"arguments [RequirementCheck, ValidationContext] but this has signature {sig}")
        if sig.return_annotation not in (bool, inspect.Signature.empty):
            raise RuntimeError("Invalid PyFunctionCheck function. Checks are expected to "
                               f"return bool but this only returns {sig.return_annotation}")

        self._check_function = check_function

    def execute_check(self, context: ValidationContext) -> bool:
        return self._check_function(self, context)


class PyRequirement(Requirement):
    """
    A base class for requirements that are implemented as Python classes.

    This class is used to define a requirement that is implemented as a Python class.

    The class is a subclass of :py:class:`rocrate_validator.models.Requirement`.

    Class instances are automatically initialized by the validator
    providing the profile, the requirement class,
    the name, the description, and the path to the file that contains the requirement check class
    within the profile directory.

    The class is expected to have a docstring that provides a description of the requirement,
    even if the description can be provided through the :py:func:`requirement` decorator.

    The class should define one or more methods that are decorated with the :py:func:`check` decorator.
    """

    def __init__(self,
                 profile: Profile,
                 requirement_check_class: Type[PyFunctionCheck],
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None):
        self.requirement_check_class = requirement_check_class
        super().__init__(profile, name, description, path, initialize_checks=True)

    def __init_checks__(self):
        # initialize the list of checks
        checks = []
        for name, member in inspect.getmembers(self.requirement_check_class, inspect.isfunction):
            # verify that the attribute set by the check decorator is present
            if hasattr(member, "check") and member.check is True:
                check_name = None
                try:
                    check_name = member.name.strip()
                except Exception:
                    check_name = name.strip()
                check_description = member.__doc__.strip() if member.__doc__ else ""
                # init the check with the requirement level
                severity = None
                try:
                    severity = member.severity
                    logger.debug("Severity set for check '%r' from decorator: %r", check_name, severity)
                except Exception:
                    pass
                if not severity:
                    logger.debug(f"No explicit severity set for check '{check_name}' from decorator."
                                 f"Getting severity from path: {self.severity_from_path}")
                    severity = self.severity_from_path or Severity.REQUIRED
                logger.debug("Severity log: %r", severity)
                check = self.requirement_check_class(self,
                                                     check_name,
                                                     member,
                                                     description=check_description,
                                                     level=LevelCollection.get(severity.name) if severity else None)
                self._checks.append(check)
                logger.debug("Added check: %s %r", check_name, check)

        return checks

    @property
    def hidden(self) -> bool:
        return getattr(self.requirement_check_class, "hidden", False)


def requirement(name: str, description: Optional[str] = None, hidden: bool = False):
    """
    A decorator to mark a class as a requirement class.

    The decorator can be used to set the name and description of the requirement.

    :param name: the name of the requirement
    :type name: str

    :param description: the description of the requirement
    :type description: Optional[str]

    :param hidden: a flag to indicate if the requirement
                   should not be displayed in the list of requirements
    :type hidden: bool

    :return: the decorated class
    """
    def decorator(cls):
        if name:
            cls.__rq_name__ = name
        if description:
            cls.__rq_description__ = description
        cls.hidden = hidden
        return cls

    return decorator


def check(name: Optional[str] = None, severity: Optional[Severity] = None):
    """
    A decorator to mark a function as a check.

    The function should accept two arguments:

    - a :py:class:`rocrate_validator.models.RequirementCheck` instance
    - a :py:class:`rocrate_validator.models.ValidationContext` instance

    The function should return a boolean value.

    The decorator can be used to set the name of the check and the severity level.

    :param name: the name of the check
    :type name: Optional[str]

    :param severity: the severity level
    :type severity: Optional[Severity]

    :return: the decorated function
    :rtype: Callable
    """
    def decorator(func):
        check_name = name if name else func.__name__
        sig = inspect.signature(func)
        if len(sig.parameters) != 2:
            raise RuntimeError(f"Invalid check {check_name}. Checks are expected to "
                               f"accept two arguments but this only takes {len(sig.parameters)}")
        if sig.return_annotation not in (bool, inspect.Signature.empty):
            raise RuntimeError(f"Invalid check {check_name}. Checks are expected to "
                               f"return bool but this only returns {sig.return_annotation}")
        func.check = True
        func.name = check_name
        func.severity = severity
        return func
    return decorator


class PyRequirementLoader(RequirementLoader):

    def load(self, profile: Profile,
             requirement_level: RequirementLevel,
             file_path: Path,
             publicID: Optional[str] = None) -> list[Requirement]:
        # instantiate a list to store the requirements
        requirements: list[Requirement] = []

        # Get the classes in the file that are subclasses of RequirementCheck
        classes = get_classes_from_file(file_path, filter_class=PyFunctionCheck)
        logger.debug("Classes: %r", classes)

        # instantiate a requirement for each class
        for requirement_name, check_class in classes.items():
            # set default requirement name and description
            rq = {}
            rq["name"] = " ".join(re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))',
                                             requirement_name.strip())) if requirement_name else ""
            rq["description"] = check_class.__doc__.strip() if check_class.__doc__ else ""
            # handle default overrides via decorators
            for pn in ("name", "description"):
                try:
                    pv = getattr(check_class, f"__rq_{pn}__", None)
                    if pv and isinstance(pv, str):
                        rq[pn] = pv
                except AttributeError:
                    pass
            logger.debug("Processing requirement: %r", requirement_name)
            r = PyRequirement(
                profile,
                requirement_check_class=check_class,
                name=rq["name"],
                description=rq["description"],
                path=file_path)
            logger.debug("Created requirement: %r", r)
            requirements.append(r)

        return requirements
