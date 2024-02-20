import logging
from typing import Optional, Union

from rdflib import Graph

import pyshacl
from pyshacl.pytypes import GraphLike

from .models import ROCRATE_METADATA_FILE, ValidationResult
from .shapes import get_shapes_paths, get_shapes_graph

# set up logging
logger = logging.getLogger(__name__)


class SHACLValidator:

    def __init__(
        self,
        shapes_graph: Optional[Union[GraphLike, str, bytes]],
        ont_graph: Optional[Union[GraphLike, str, bytes]] = None,
    ) -> None:
        self._shapes_graph = shapes_graph
        self._ont_graph = ont_graph

    @property
    def shapes_graph(self) -> Optional[Union[GraphLike, str, bytes]]:
        return self._shapes_graph

    @property
    def ont_graph(self) -> Optional[Union[GraphLike, str, bytes]]:
        return self._ont_graph

    def validate(
        self,
        data_graph: Union[GraphLike, str, bytes],
        advanced: Optional[bool] = False,
        inference: Optional[str] = None,
        inplace: Optional[bool] = False,
        abort_on_first: Optional[bool] = False,
        allow_infos: Optional[bool] = False,
        allow_warnings: Optional[bool] = False,
        serialisation_output_path: str = None,
        serialisation_output_format: str = "turtle",
        **kwargs,
    ) -> ValidationResult:

        # validate the data graph using pyshacl.validate
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            ont_graph=self.ont_graph,
            inference=inference,
            inplace=inplace,
            abort_on_first=abort_on_first,
            allow_infos=allow_infos,
            allow_warnings=allow_warnings,
            meta_shacl=False,
            advanced=advanced,
            js=False,
            debug=False,
            **kwargs,
        )
        # log the validation results
        logger.debug("Conforms: %r", conforms)
        logger.debug("Results Graph: %r", results_graph)
        logger.debug("Results Text: %r", results_text)

        # serialize the results graph
        if serialisation_output_path:
            assert serialisation_output_format in [
                "turtle",
                "n3",
                "nt",
                "xml",
                "rdf",
                "json-ld",
            ], "Invalid serialisation output format"
            results_graph.serialize(
                serialisation_output_path, format=serialisation_output_format
            )
        # return the validation result
        return ValidationResult(results_graph, conforms, results_text)


def validate(
    rocrate_path: Union[GraphLike, str, bytes],
    shapes_path: Union[GraphLike, str, bytes],
    advanced: Optional[bool] = False,
    inference: Optional[str] = None,
    inplace: Optional[bool] = False,
    abort_on_first: Optional[bool] = False,
    allow_infos: Optional[bool] = False,
    allow_warnings: Optional[bool] = False,
    serialisation_output_path: str = None,
    serialisation_output_format: str = "turtle",
    **kwargs,
) -> ValidationResult:
    """
    Validate a data graph using SHACL shapes as constraints
    """
    # TODO: handle multiple shapes files and allow user to select one
    shacl_graph = shapes_path
    logger.debug("shacl_graph: %s", shacl_graph)

    # load the data graph
    data_graph = Graph()
    data_graph.parse(f"{rocrate_path}/{ROCRATE_METADATA_FILE}",
                     format="json-ld", publicID=rocrate_path)

    # load the shapes graph
    shacl_graph = get_shapes_graph(shapes_path, publicID=rocrate_path)

    validator = SHACLValidator(shapes_graph=shacl_graph)
    result = validator.validate(
        data_graph=data_graph,
        advanced=advanced,
        inference=inference,
        inplace=inplace,
        abort_on_first=abort_on_first,
        allow_infos=allow_infos,
        allow_warnings=allow_warnings,
        serialisation_output_path=serialisation_output_path,
        serialisation_output_format=serialisation_output_format,
        publicID=rocrate_path,
        **kwargs,
    )
    logger.debug("Validation conforms: %s", result.conforms)
    return result
