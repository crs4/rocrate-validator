import inspect
import logging
from pathlib import Path
from typing import Optional

from ...models import Profile, Requirement, RequirementCheck, RequirementLevel
from ...utils import get_classes_from_file

# set up logging
logger = logging.getLogger(__name__)


class PyRequirement(Requirement):

    def __init__(self,
                 level: RequirementLevel,
                 profile: Profile,
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None,
                 requirement_check_class=None):
        self.requirement_check_class = requirement_check_class
        super().__init__(level, profile, name, description, path, initialize_checks=True)

    def __init_checks__(self):
        # initialize the list of checks
        checks = []
        for name, member in inspect.getmembers(self.requirement_check_class, inspect.isfunction):
            if hasattr(member, "check"):
                check_name = None
                try:
                    check_name = member.name.strip()
                except Exception:
                    check_name = name.strip()
                check_description = member.__doc__.strip() if member.__doc__ else ""
                check = self.requirement_check_class(self, check_name, member, check_description)
                self._checks.append(check)
                logger.debug("Added check: %s %r", check_name, check)

        return checks

    @staticmethod
    def load(profile: Profile, requirement_level: RequirementLevel, file_path: Path) -> list[Requirement]:
        # instantiate a list to store the requirements
        requirements: list[Requirement] = []

        # get the classes from the file
        classes = get_classes_from_file(file_path, filter_class=RequirementCheck)
        logger.debug("Classes: %r", classes)

        # instantiate a requirement for each class
        for requirement_name, requirement_class in classes.items():
            logger.debug("Processing requirement: %r", requirement_name)
            r = PyRequirement(
                requirement_level, profile,
                name=requirement_name.strip() if requirement_name else "",
                description=requirement_class.__doc__.strip() if requirement_class.__doc__ else "",
                path=file_path,
                requirement_check_class=requirement_class
            )
            logger.debug("Created requirement: %r", r)
            requirements.append(r)

        return requirements
