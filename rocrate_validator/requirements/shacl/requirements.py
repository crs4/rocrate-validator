import logging
from pathlib import Path

from ...models import Profile, Requirement, RequirementCheck, RequirementLevel
from .checks import SHACLCheck
from .models import Shape

# set up logging
logger = logging.getLogger(__name__)


class SHACLRequirement(Requirement):

    def __init__(self,
                 level: RequirementLevel,
                 shape: Shape,
                 profile: Profile,
                 path: Path):
        self._shape = shape
        super().__init__(level, profile,
                         shape.name if shape.name else "",
                         shape.description if shape.description else "",
                         path)
        # init checks
        self._checks = self.__init_checks__()
        # assign check IDs
        self.__reorder_checks__()

    def __init_checks__(self) -> list[RequirementCheck]:
        # assign a check to each property of the shape
        checks = []
        for prop in self._shape.get_properties():
            logger.debug("Creating check for property %s %s", prop.name, prop.description)
            property_check = SHACLCheck(self, prop)
            logger.debug("Property check %s: %s", property_check.name, property_check.description)
            checks.append(property_check)

        # if no property checks, add a generic one
        if len(checks) == 0:
            checks.append(SHACLCheck(self))
        # return checks
        return checks

    @property
    def shape(self) -> Shape:
        return self._shape

    @staticmethod
    def load(profile: Profile, requirement_level: RequirementLevel,
             file_path: Path, publicID: str = None) -> list[Requirement]:
        shapes: dict[str, Shape] = Shape.load(file_path, publicID=publicID)
        logger.debug("Loaded %s shapes: %s", len(shapes), shapes)
        requirements = []
        for shape in shapes.values():
            requirements.append(SHACLRequirement(requirement_level, shape, profile, file_path))
        return requirements
