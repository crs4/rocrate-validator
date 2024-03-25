import logging
from pathlib import Path
from typing import Dict, List

from ...models import Profile, Requirement, RequirementType
from .checks import SHACLCheck
from .models import Shape

# set up logging
logger = logging.getLogger(__name__)


class SHACLRequirement(Requirement):

    def __init__(self,
                 type: RequirementType,
                 shape: Shape,
                 profile: Profile,
                 path: Path):
        self._shape = shape
        super().__init__(type, profile,
                         shape.name if shape.name else "",
                         shape.description if shape.description else "",
                         path)
        # init checks
        self._checks = self.__init_checks__()
        # assign check IDs
        self.__reorder_checks__()

    def __init_checks__(self):
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
    def load(profile: Profile, requirement_type: RequirementType,
             file_path: Path, publicID: str = None) -> List[Requirement]:
        shapes: Dict[str, Shape] = Shape.load(file_path, publicID=publicID)
        logger.debug("Loaded shapes: %s" % shapes)
        requirements = []
        for shape in shapes.values():
            requirements.append(SHACLRequirement(requirement_type, shape, profile, file_path))
        return requirements
