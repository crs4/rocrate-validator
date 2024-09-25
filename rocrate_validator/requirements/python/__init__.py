# Copyright (c) 2024 CRS4
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

from ...models import (LevelCollection, Profile, Requirement, RequirementCheck,
                       RequirementLevel, RequirementLoader, Severity, ValidationContext)
from ...utils import get_classes_from_file

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
                except Exception:
                    severity = self.severity_from_path or Severity.REQUIRED
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


def requirement(name: str, description: Optional[str] = None):
    """
    A decorator to mark functions as "requirements" (by setting an attribute
    `requirement=True`) and annotating them with a human-legible name.
    """
    def decorator(cls):
        if name:
            cls.__rq_name__ = name
        if description:
            cls.__rq_description__ = description
        return cls

    return decorator


def check(name: Optional[str] = None, severity: Optional[Severity] = None):
    """
    A decorator to mark functions as "checks" (by setting an attribute
    `check=True`) and optionally annotating them with a human-legible name.
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
