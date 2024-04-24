import logging
import os
from typing import Optional

from rdflib import Literal, Namespace

from rocrate_validator.constants import SHACL_NS
from rocrate_validator.models import (Requirement, RequirementCheck,
                                      ValidationContext)
from rocrate_validator.requirements.shacl.models import Shape

from .validator import SHACLValidator

logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):
    """
    A SHACL check for a specific shape property
    """

    def __init__(self,
                 requirement: Requirement,
                 shape: Optional[Shape]) -> None:
        self._shape = shape
        super().__init__(requirement,
                         shape.name
                         if shape and shape.name else None,
                         shape.description
                         if shape and shape.description else None)

    @property
    def shape(self) -> Shape:
        return self._shape

    def execute_check(self, context: ValidationContext):
        # set up the input data for the validator
        ontology_graph = context.validator.ontologies_graph
        data_graph = context.validator.data_graph
        shapes_graph = self.shape.graph

        # temporary fix to replace the ex: prefix with the rocrate path
        if os.path.isdir(context.validator.rocrate_path):
            shacl_ns = Namespace(SHACL_NS)
            selects = shapes_graph.triples((None, shacl_ns.select, None))
            for s, p, o in selects:
                shapes_graph.remove((s, p, o))
                # FIXME: write a better regex ??
                updated_node_value = str(o).replace("ex:", f"<file://{context.validator.rocrate_path}/>")
                shapes_graph.add((s, p, Literal(updated_node_value)))

        # validate the data graph
        shacl_validator = SHACLValidator(shapes_graph=shapes_graph, ont_graph=ontology_graph)
        result = shacl_validator.validate(
            data_graph=data_graph, ontology_graph=ontology_graph, **context.validator.validation_settings)
        # parse the validation result
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
        return super().__str__() + (f" - {self._shape}" if self._shape else "")

    def __repr__(self) -> str:
        return super().__repr__() + (f" - {self._shape}" if self._shape else "")

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, type(self)):
            return NotImplemented
        return super().__eq__(__value) and self._shape == getattr(__value, '_shape', None)

    def __hash__(self) -> int:
        return super().__hash__() + (hash(self._shape) if self._shape else 0)

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
