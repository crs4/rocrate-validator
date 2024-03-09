import logging
from typing import Literal, Optional, Union

from pyshacl.pytypes import GraphLike
from rdflib import Graph

from .errors import CheckValidationError, SHACLValidationError
from .models import ROCRATE_METADATA_FILE
from .utils import get_full_graph
from .validators.shacl import Validator

# set up logging
logger = logging.getLogger(__name__)


def validate(
    rocrate_path: Union[GraphLike, str, bytes],
    shapes_path: Union[GraphLike, str, bytes],
    ontologies_path: Union[GraphLike, str, bytes] = None,
    advanced: Optional[bool] = False,
    inference: Optional[Literal["owl", "rdfs"]] = False,
    inplace: Optional[bool] = False,
    abort_on_first: Optional[bool] = False,
    allow_infos: Optional[bool] = False,
    allow_warnings: Optional[bool] = False,
    serialization_output_path: str = None,
    serialization_output_format: str = "turtle",
    **kwargs,
) -> bool:
    """
    Validate a data graph using SHACL shapes as constraints

    :param rocrate_path: The path to the RO-Crate metadata file
    :param shapes_path: The path to the SHACL shapes file

    :return: True if the data graph conforms to the SHACL shapes
    :raises SHACLValidationError: If the data graph does not conform to the SHACL shapes
    :raises CheckValidationError: If a check fails
    """

    # set the RO-Crate metadata file
    rocrate_metadata_path = f"{rocrate_path}/{ROCRATE_METADATA_FILE}"
    logger.debug("rocrate_metadata_path: %s", rocrate_metadata_path)

    from .checks import get_checks

    # get the checks
    for check_instance in get_checks():
        logger.debug("Loaded check: %s", check_instance)
        result = check_instance.check(rocrate_path)
        if result[0] == 0:
            logger.debug("Check passed: %s", check_instance.name)
        else:
            logger.debug(
                f"Check {check_instance.name} failed: "
                f"{result[1]}", check_instance.name
            )
            raise CheckValidationError(
                check_instance, result[1], rocrate_path, result[0]
            )

    # load the data graph
    data_graph = Graph()
    data_graph.parse(rocrate_metadata_path,
                     format="json-ld", publicID=rocrate_path)

    # load the shapes graph
    shacl_graph = None
    if shapes_path:
        shacl_graph = get_full_graph(shapes_path, publicID=rocrate_path)

    # load the ontology graph
    ontology_graph = None
    if ontologies_path:
        ontology_graph = get_full_graph(ontologies_path)

    validator = Validator(
        shapes_graph=shacl_graph, ont_graph=ontology_graph)
    result = validator.validate(
        data_graph=data_graph,
        advanced=advanced,
        inference=inference,
        inplace=inplace,
        abort_on_first=abort_on_first,
        allow_infos=allow_infos,
        allow_warnings=allow_warnings,
        serialization_output_path=serialization_output_path,
        serialization_output_format=serialization_output_format,
        publicID=rocrate_path,
        **kwargs,
    )
    logger.debug("Validation conforms: %s", result.conforms)
    if not result.conforms:
        raise SHACLValidationError(result, rocrate_path)
    return True
