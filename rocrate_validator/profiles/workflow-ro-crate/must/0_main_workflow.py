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


@requirement(name="Main Workflow file existence")
class MainWorkflowFileExistence(PyFunctionCheck):
    """Checks for main workflow file existence."""

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

    @check(name="Main Workflow file must exist")
    def check_workflow(self, validation_context: ValidationContext) -> bool:
        """Check if the crate contains the main workflow file."""
        json_dict = self.get_json_dict(validation_context)
        entity_dict = {_["@id"]: _ for _ in json_dict["@graph"]}
        main_workflow = find_main_workflow(entity_dict)
        if not main_workflow:
            validation_context.result.add_error(f"main workflow does not exist in metadata file", self)
            return False
        workflow_relpath = main_workflow["@id"]
        workflow_path = validation_context.rocrate_path / workflow_relpath
        if not workflow_path.is_file():
            validation_context.result.add_error(f"Main Workflow {workflow_path} not found in crate", self)
            return False
        return True
