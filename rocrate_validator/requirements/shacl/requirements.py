import logging
from pathlib import Path
from typing import Optional

from ...models import (Profile, Requirement, RequirementCheck,
                       RequirementLevel, RequirementLoader)
from .checks import SHACLCheck
from .models import Shape, ShapesRegistry

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
        # create a check for each property if the shape has nested properties
        if hasattr(self.shape, "properties"):
            for prop in self.shape.properties:
                logger.debug("Creating check for property %s %s", prop.name, prop.description)
                property_check = SHACLCheck(self, prop)
                logger.debug("Property check %s: %s", property_check.name, property_check.description)
                checks.append(property_check)

        # if no property checks, add a generic one
        if len(checks) == 0:
            checks.append(SHACLCheck(self, self.shape))
        return checks

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def level(self) -> RequirementLevel:
        level = super().level
        if level is None:
            return self.shape.level
        return level

    @property
    def hidden(self) -> bool:
        from rdflib import RDF, Namespace
        SHACL = Namespace("http://www.w3.org/ns/shacl#")
        if self.shape.node is not None:
            if (self.shape.node, RDF.type, SHACL.hidden) in self.shape.graph:
                return True
        return False


class SHACLRequirementLoader(RequirementLoader):

    def __init__(self, profile: Profile):
        super().__init__(profile)
        self._shape_registry = ShapesRegistry.get_instance(profile)
        # reset the shapes registry
        self._shape_registry.clear()  # should be removed

    @property
    def shapes_registry(self) -> ShapesRegistry:
        return self._shape_registry

    def load(self, profile: Profile,
             requirement_level: RequirementLevel,
             file_path: Path, publicID: Optional[str] = None) -> list[Requirement]:
        assert file_path is not None, "The file path cannot be None"
        shapes: list[Shape] = self.shapes_registry.load_shapes(file_path, publicID)
        logger.debug("Loaded %s shapes: %s", len(shapes), shapes)
        requirements = []
        for shape in shapes:
            requirements.append(SHACLRequirement(requirement_level, shape, profile, file_path))
        return requirements
