import json
from typing import Optional

import rocrate_validator.log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


def find_metadata_file_descriptor(entity_dict: dict):
    for k, v in entity_dict.items():
        if k.endswith("ro-crate-metadata.json"):
            return v
    raise ValueError("no metadata file descriptor in crate")


def find_root_data_entity(entity_dict: dict):
    metadata_file_descriptor = find_metadata_file_descriptor(entity_dict)
    return entity_dict[metadata_file_descriptor["about"]["@id"]]


def find_main_workflow(entity_dict: dict):
    root_data_entity = find_root_data_entity(entity_dict)
    return entity_dict[root_data_entity["mainEntity"]["@id"]]


@requirement(name="Workflow-related files existence")
class WorkflowFilesExistence(PyFunctionCheck):
    """Checks for workflow-related crate files existence."""

    _json_dict_cache: Optional[dict] = None

    def get_json_dict(self, context: ValidationContext) -> dict:
        if self._json_dict_cache is None or \
                self._json_dict_cache['file_descriptor_path'] != context.file_descriptor_path:
            # invalid cache
            try:
                with open(context.file_descriptor_path, "r") as file:
                    self._json_dict_cache = dict(
                        json=json.load(file),
                        file_descriptor_path=context.file_descriptor_path)
            except Exception as e:
                context.result.add_error(
                    f'file descriptor "{context.rel_fd_path}" is not in the correct format', self)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                return {}
        return self._json_dict_cache['json']

    @check(name="Workflow diagram existence")
    def check_workflow_diagram(self, validation_context: ValidationContext) -> bool:
        """Check if the crate contains the workflow diagram."""
        json_dict = self.get_json_dict(validation_context)
        entity_dict = {_["@id"]: _ for _ in json_dict["@graph"]}
        main_workflow = find_main_workflow(entity_dict)
        image = main_workflow.get("image")
        diagram_relpath = image["@id"] if image else None
        if not diagram_relpath:
            validation_context.result.add_error(f"main workflow does not have an 'image' property", self)
            return False
        diagram_path = validation_context.rocrate_path / diagram_relpath
        if not diagram_path.is_file():
            validation_context.result.add_error(f"Workflow diagram {diagram_path} not found in crate", self)
            return False
        return True

    @check(name="Workflow description existence")
    def check_workflow_description(self, validation_context: ValidationContext) -> bool:
        """Check if the crate contains the workflow CWL description."""
        json_dict = self.get_json_dict(validation_context)
        entity_dict = {_["@id"]: _ for _ in json_dict["@graph"]}
        main_workflow = find_main_workflow(entity_dict)
        main_workflow = main_workflow.get("subjectOf")
        description_relpath = main_workflow["@id"] if main_workflow else None
        if not description_relpath:
            validation_context.result.add_error("main workflow does not have a 'subjectOf' property", self)
            return False
        description_path = validation_context.rocrate_path / description_relpath
        if not description_path.is_file():
            validation_context.result.add_error(f"Workflow CWL description {description_path} not found in crate", self)
            return False
        return True
