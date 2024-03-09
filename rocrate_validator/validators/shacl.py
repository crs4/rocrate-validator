import logging
from typing import Literal, Optional, Union

import pyshacl
from pyshacl.pytypes import GraphLike
from rdflib import Graph

from ..constants import RDF_SERIALIZATION_FORMATS, RDF_SERIALIZATION_FORMATS_TYPES, VALID_INFERENCE_OPTIONS, VALID_INFERENCE_OPTIONS_TYPES
from ..models import ValidationResult

# set up logging
logger = logging.getLogger(__name__)


class Validator:

    def __init__(
        self,
        shapes_graph: Optional[Union[GraphLike, str, bytes]],
        ont_graph: Optional[Union[GraphLike, str, bytes]] = None,
    ) -> None:
        """
        Create a new SHACLValidator instance.

        :param shacl_graph: rdflib.Graph or file path or web url
                of the SHACL Shapes graph to use to
        validate the data graph
        :type shacl_graph: rdflib.Graph | str | bytes
        :param ont_graph: rdflib.Graph or file path or web url
                of an extra ontology document to mix into the data graph
        :type ont_graph: rdflib.Graph | str | bytes
        """
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
        inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None,
        inplace: Optional[bool] = False,
        abort_on_first: Optional[bool] = False,
        allow_infos: Optional[bool] = False,
        allow_warnings: Optional[bool] = False,
        serialization_output_path: Optional[str] = None,
        serialization_output_format:
            Optional[RDF_SERIALIZATION_FORMATS_TYPES] = "turtle",
        **kwargs,
    ) -> ValidationResult:
        f"""
        Validate a data graph using SHACL shapes as constraints

        :param data_graph: rdflib.Graph or file path or web url
                of the data to validate
        :type data_graph: rdflib.Graph | str | bytes
        :param advanced: Enable advanced SHACL features, default=False
        :type advanced: bool | None
        :param inference: One of {VALID_INFERENCE_OPTIONS}
        :type inference: str | None
        :param inplace: If this is enabled, do not clone the datagraph,
                manipulate it inplace
        :type inplace: bool
        :param abort_on_first: Stop evaluating constraints after first
                violation is found
        :type abort_on_first: bool | None
        :param allow_infos: Shapes marked with severity of sh:Info
                will not cause result to be invalid.
        :type allow_infos: bool | None
        :param allow_warnings: Shapes marked with severity of sh:Warning
                or sh:Info will not cause result to be invalid.
        :type allow_warnings: bool | None
        :param serialization_output_format: Literal[
            {RDF_SERIALIZATION_FORMATS}
        ]
        :param kwargs: Additional keyword arguments to pass to pyshacl.validate
        """

        # Validate data_graph
        if not isinstance(data_graph, (Graph, str, bytes)):
            raise ValueError(
                "data_graph must be an instance of Graph, str, or bytes")

        # Validate inference
        if inference and inference not in VALID_INFERENCE_OPTIONS:
            raise ValueError(
                f"inference must be one of {VALID_INFERENCE_OPTIONS}")

        # Validate serialization_output_format
        if serialization_output_format and \
                serialization_output_format not in RDF_SERIALIZATION_FORMATS:
            raise ValueError(
                "serialization_output_format must be one of "
                f"{RDF_SERIALIZATION_FORMATS}")

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
        if serialization_output_path:
            assert serialization_output_format in [
                "turtle",
                "n3",
                "nt",
                "xml",
                "rdf",
                "json-ld",
            ], "Invalid serialization output format"
            results_graph.serialize(
                serialization_output_path, format=serialization_output_format
            )
        # return the validation result
        return ValidationResult(results_graph, conforms, results_text)
