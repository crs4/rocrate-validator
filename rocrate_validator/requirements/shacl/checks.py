import logging
from typing import Optional

from rocrate_validator.models import (Requirement, RequirementCheck,
                                      ValidationContext)
from rocrate_validator.requirements.shacl.models import Shape

from .validator import SHACLValidationContext, SHACLValidator

logger = logging.getLogger(__name__)


class SHACLCheck(RequirementCheck):
    """
    A SHACL check for a specific shape property
    """

    # Map shape to requirement check instances
    __instances__ = {}

    def __init__(self,
                 requirement: Requirement,
                 shape: Optional[Shape]) -> None:
        self._shape = shape
        # init the check
        super().__init__(requirement,
                         shape.name
                         if shape and shape.name else None,
                         shape.description
                         if shape and shape.description else None)
        # store the instance
        SHACLCheck.__add_instance__(shape, self)

    @property
    def shape(self) -> Shape:
        return self._shape

    def execute_check(self, context: ValidationContext):
        # retrieve the SHACLValidationContext
        shacl_context = SHACLValidationContext.get_instance(context)

        # get the shapes registry
        shapes_registry = shacl_context.shapes_registry

        # set up the input data for the validator
        ontology_graph = shacl_context.ontology_graph
        data_graph = shacl_context.data_graph
        shapes_graph = shacl_context.shapes_graph

        # uncomment to save the graphs to the logs folder (for debugging purposes)
        # data_graph.serialize("logs/data_graph.ttl", format="turtle")
        # shapes_graph.serialize("logs/shapes_graph.ttl", format="turtle")
        # if ontology_graph:
        #     ontology_graph.serialize("logs/ontology_graph.ttl", format="turtle")

        # if the SHACLvalidation has been done, skip the check
        result = getattr(context, "shacl_validation", None)
        if result is not None:
            return result

        # validate the data graph
        shacl_validator = SHACLValidator(shapes_graph=shapes_graph, ont_graph=ontology_graph)
        shacl_result = shacl_validator.validate(
            data_graph=data_graph, ontology_graph=ontology_graph, **shacl_context.settings)
        # parse the validation result
        logger.debug("Validation '%s' conforms: %s", self.name, shacl_result.conforms)
        # store the validation result in the context
        result = shacl_result.conforms
        setattr(context, "shacl_validation", result)
        # if the validation failed, add the issues to the context
        if not shacl_result.conforms:
            logger.debug("Validation failed")
            logger.debug("Parsing Validation result: %s", result)
            for violation in shacl_result.violations:
                shape = shapes_registry.get_shape(hash(violation.sourceShape))
                assert shape is not None, "Unable to map the violation to a shape"
                requirementCheck = SHACLCheck.get_instance(shape)
                assert requirementCheck is not None, "The requirement check cannot be None"
                c = shacl_context.result.add_check_issue(message=violation.get_result_message(shacl_context.rocrate_path),
                                                         check=requirementCheck,
                                                         severity=violation.get_result_severity())
                logger.debug("Added validation issue to the context: %s", c)
                if context.fail_fast:
                    break

        return result

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

    @classmethod
    def get_instance(cls, shape: Shape) -> Optional["SHACLCheck"]:
        return cls.__instances__.get(hash(shape), None)

    @classmethod
    def __add_instance__(cls, shape: Shape, check: "SHACLCheck") -> None:
        cls.__instances__[hash(shape)] = check

    @classmethod
    def clear_instances(cls) -> None:
        cls.__instances__.clear()


__all__ = ["SHACLCheck"]
