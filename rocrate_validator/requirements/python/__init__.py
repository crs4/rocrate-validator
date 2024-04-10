import inspect
import logging
from pathlib import Path
from typing import Callable, Optional, Type

from ...models import (Profile, Requirement, RequirementCheck,
                       RequirementLevel, ValidationContext)
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
                 description: Optional[str] = None):
        """
        check_function: a function that accepts an instance of PyFunctionCheck and a ValidationContext.
        """
        super().__init__(requirement, name, description)

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
                 level: RequirementLevel,
                 profile: Profile,
                 requirement_check_class: Type[PyFunctionCheck],
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None):
        self.requirement_check_class = requirement_check_class
        super().__init__(level, profile, name, description, path, initialize_checks=True)

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
                check = self.requirement_check_class(requirement=self,
                                                     name=check_name,
                                                     check_function=member,
                                                     description=check_description)
                self._checks.append(check)
                logger.debug("Added check: %s %r", check_name, check)

        return checks

    @staticmethod
    def load(profile: Profile, requirement_level: RequirementLevel, file_path: Path) -> list[Requirement]:
        # instantiate a list to store the requirements
        requirements: list[Requirement] = []

        # Get the classes in the file that are subclasses of RequirementCheck
        classes = get_classes_from_file(file_path, filter_class=PyFunctionCheck)
        logger.debug("Classes: %r", classes)

        # instantiate a requirement for each class
        for requirement_name, check_class in classes.items():
            logger.debug("Processing requirement: %r", requirement_name)
            r = PyRequirement(
                requirement_level,
                profile,
                requirement_check_class=check_class,
                name=requirement_name.strip() if requirement_name else "",
                description=check_class.__doc__.strip() if check_class.__doc__ else "",
                path=file_path)
            logger.debug("Created requirement: %r", r)
            requirements.append(r)

        return requirements


def check(name: Optional[str] = None):
    """
    A decorator to mark functions as "checks" (by setting an attribute
    `check=True`) and optionally annotating them with a human-legible name.
    """
    def decorator(func):
        check_name = name if name else func.__name__
        sig = inspect.signature(func)
        if len(sig.parameters) != 2:
            raise RuntimeError(f"Invalid check {check_name}. Checks are expected to "
                               "accept two arguments but this only takes {len(sig.parameters)}")
        if sig.return_annotation not in (bool, inspect.Signature.empty):
            raise RuntimeError(f"Invalid check {check_name}. Checks are expected to "
                               "return bool but this only returns {sig.return_annotation}")
        func.check = True
        func.name = check_name
        return func
    return decorator
