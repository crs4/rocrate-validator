
import logging

from ...models import RequirementCheck
from ...models import Requirement
from .models import ShapeProperty


logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):

    """
    A SHACL check for a specific shape property
    """

    def __init__(self,
                 requirement: Requirement,
                 shapeProperty: ShapeProperty = None) -> None:
        self._shapeProperty = shapeProperty

        super().__init__(requirement,
                         shapeProperty.name
                         if shapeProperty and shapeProperty.name else None,
                         shapeProperty.description
                         if shapeProperty and shapeProperty.description else None)

    @property
    def shapeProperty(self) -> ShapeProperty:
        return self._shapeProperty

    @property
    def severity(self):
        return self.requirement.severity

    @classmethod
    def get_description(cls, requirement: Requirement):
        from ...models import Validator
        graph_of_shapes = Validator.load_graph_of_shapes(requirement)
        return cls.query_description(graph_of_shapes)

    @property
    def shapes_graph(self):
        return self.validator.get_graph_of_shapes(self.requirement.name)

    def check(self):
        ontology_graph = self.validator.ontologies_graph
        data_graph = self.validator.data_graph

        # constraint the shapes graph to the current property shape
        shapes_graph = self.shapeProperty.shape_property_graph

        from .validator import Validator as SHACLValidator
        shacl_validator = SHACLValidator(
            self, shapes_graph=shapes_graph, ont_graph=ontology_graph)
        result = shacl_validator.validate(
            data_graph=data_graph,
            **self.validator.validation_settings
        )
        logger.debug("Validation conforms: %s", result.conforms)
        if not result.conforms:
            logger.debug("Validation failed")
            logger.debug("Validation result: %s", result)
            for issue in result.violations:
                logger.debug("Validation issue: %s", issue.message)
                self.result.add_issue(issue)

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
