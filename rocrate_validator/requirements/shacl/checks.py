
import logging

from ...models import RequirementCheck
from ...models import Requirement
from .models import ShapeProperty
from .validator import Validator as SHACLValidator

logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):
    def __init__(self,
                 requirement: Requirement,
                 shapeProperty: ShapeProperty) -> None:
        self._shapeProperty = shapeProperty
        super().__init__(requirement, shapeProperty.name, shapeProperty.description)

    @property
    def name(self):
        return self._shapeProperty.name

    @property
    def description(self):
        return self._shapeProperty.description

    @property
    def shapeProperty(self) -> ShapeProperty:
        return self._shapeProperty

    @property
    def severity(self):
        return self.requirement.type

    @classmethod
    def get_description(cls, requirement: Requirement):
        from ...models import Validator
        graph_of_shapes = Validator.load_graph_of_shapes(requirement)
        return cls.query_description(graph_of_shapes)

    @property
    def shapes_graph(self):
        return self.validator.get_graph_of_shapes(self.requirement.name)

    def check(self):
        shapes_graph = self.shapes_graph
        ontology_graph = self.validator.ontologies_graph
        data_graph = self.validator.data_graph

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
