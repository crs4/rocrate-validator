import inspect
import logging
from pathlib import Path
from typing import List

from ...models import Profile, Requirement, RequirementCheck, RequirementType
from ...utils import get_classes_from_file

# set up logging
logger = logging.getLogger(__name__)


class PyRequirement(Requirement):

    def __init__(self,
                 type: RequirementType,
                 profile: Profile,
                 name: str = None,
                 description: str = None,
                 path: Path = None,
                 requirement_check_class=None):
        self.requirement_check_class = requirement_check_class
        super().__init__(type, profile, name, description, path, initialize_checks=True)

    def __init_checks__(self):
        # initialize the list of checks
        checks = []
        for name, member in inspect.getmembers(self.requirement_check_class, inspect.isfunction):
            if hasattr(member, "check"):
                check_name = member.name if hasattr(member, "name") else name
                check_description = member.__doc__ if member.__doc__ else ""
                check = RequirementCheck(self, check_name, member, check_description)
                self._checks.append(check)
                logger.debug("Added check: %s", check_name, check)
        # return the checks
        return checks

    @classmethod
    def load(cls, profile: Profile, requirement_type: RequirementType, file_path: Path):
        # instantiate a list to store the requirements
        requirements: List[Requirement] = []

        # get the classes from the file
        classes = get_classes_from_file(file_path, filter_class=RequirementCheck)
        logger.debug("Classes: %r" % classes)

        # instantiate a requirement for each class
        for requirement_name, requirement_class in classes.items():
            logger.debug("Processing requirement: %r" % requirement_name)
            r = PyRequirement(
                requirement_type, profile,
                name=requirement_name,
                description=requirement_class.__doc__,
                path=file_path,
                requirement_check_class=requirement_class
            )
            logger.debug("Created requirement: %r" % r)
            requirements.append(r)

        return requirements
