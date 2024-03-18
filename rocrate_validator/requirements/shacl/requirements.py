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
                 path: Path
                 ):
        self._shape = shape
        super().__init__(type, profile,
                         shape.name, shape.description, path)
        # init checks
        self._checks = []
        for prop in shape.get_properties():
            self._checks.append(SHACLCheck(self, prop))

    @staticmethod
    def load(profile: Profile, requirement_type: RequirementType, file_path: Path) -> List[Requirement]:
        shapes: Dict[str, Shape] = Shape.load(file_path)
        logger.debug("Loaded shapes: %s" % shapes)
        requirements = []
        for shape in shapes.values():
            requirements.append(SHACLRequirement(requirement_type, shape, profile, file_path))
        return requirements
