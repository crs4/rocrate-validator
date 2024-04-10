
import logging
from typing import Optional

from rocrate_validator.models import (Requirement, RequirementCheck,
                                      ValidationContext)
from rocrate_validator.requirements.shacl.models import ShapeProperty

from .validator import SHACLValidator

logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):
    """
    A SHACL check for a specific shape property
    """

    def __init__(self,
                 requirement: Requirement,
                 shapeProperty: Optional[ShapeProperty] = None) -> None:
        self._shapeProperty = shapeProperty
        super().__init__(requirement,
                         shapeProperty.name
                         if shapeProperty and shapeProperty.name else None,
                         shapeProperty.description
                         if shapeProperty and shapeProperty.description else None)

    @property
    def shapeProperty(self) -> ShapeProperty:
        return self._shapeProperty

    def execute_check(self, context: ValidationContext):
        ontology_graph = context.validator.ontologies_graph
        data_graph = context.validator.data_graph

        # constraint the shapes graph to the current property shape
        shapes_graph = self.shapeProperty.shape_property_graph \
            if self.shapeProperty else self.requirement.shape.shape_graph

        shacl_validator = SHACLValidator(shapes_graph=shapes_graph, ont_graph=ontology_graph)
        result = shacl_validator.validate(data_graph=data_graph, **context.validator.validation_settings)

        logger.debug("Validation '%s' conforms: %s", self.name, result.conforms)
        if not result.conforms:
            logger.debug("Validation failed")
            logger.debug("Validation result: %s", result)
            for violation in result.violations:
                c = context.result.add_check_issue(message=violation.get_result_message(context.rocrate_path),
                                                   check=self,
                                                   severity=violation.get_result_severity())
                logger.debug("Validation issue: %s", c.message)

            return False
        return True

    def __str__(self) -> str:
        return super().__str__() + (f" - {self._shapeProperty}" if self._shapeProperty else "")

    def __repr__(self) -> str:
        return super().__repr__() + (f" - {self._shapeProperty}" if self._shapeProperty else "")

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, type(self)):
            return NotImplemented
        return super().__eq__(__value) and self._shapeProperty == getattr(__value, '_shapeProperty', None)

    def __hash__(self) -> int:
        return super().__hash__() + (hash(self._shapeProperty) if self._shapeProperty else 0)

    #  ------------ Dead code? ------------
    # @property
    # def severity(self):
    #     return self.requirement.severity

    # @classmethod
    # def get_description(cls, requirement: Requirement):
    #     from ...models import Validator
    #     graph_of_shapes = Validator.load_graph_of_shapes(requirement)
    #     return cls.query_description(graph_of_shapes)

    # @property
    # def shapes_graph(self):
    #     return self.validator.get_graph_of_shapes(self.requirement.name)


__all__ = ["SHACLCheck"]
