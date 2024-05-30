import json
import logging
from typing import Optional

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="RO-Crate Root Data Entity RECOMMENDED value")
class RootDataEntityRelativeURI(PyFunctionCheck):
    """
    The Root Data Entity SHOULD be denoted by the string /
    """

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

    def find_entity(self, context: ValidationContext, entity_id: str) -> dict:
        json_dict = self.get_json_dict(context)
        for entity in json_dict["@graph"]:
            if entity["@id"] == entity_id:
                return entity
        return {}

    def find_property(self, context: ValidationContext, entity_id: str, property_name: str) -> dict:
        entity = self.find_entity(context, entity_id)
        if entity:
            return entity.get(property_name, {})
        return {}

    @check(name="Root Data Entity: RECOMMENDED value")
    def check_relative_uris(self, context: ValidationContext) -> bool:
        """Check if the Root Data Entity is denoted by the string `./` in the file descriptor JSON-LD"""
        about_property = self.find_property(context, "ro-crate-metadata.json", "about")
        if not about_property:
            context.result.add_error(
                'Unable to find the about property on `ro-crate-metadata.json`', self)
            return False
        root_entity_id = about_property.get("@id", None)
        if not root_entity_id:
            context.result.add_error(
                'Unable to identity the Root Data Entity from the `about` property of the `ro-crate-metadata.json`', self)
            return False
        # check relative URIs
        if not root_entity_id == './':
            context.result.add_error(
                'Root Data Entity URI is not denoted by the string `./`', self)
            return False

        return False
