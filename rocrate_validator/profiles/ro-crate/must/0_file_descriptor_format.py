import json
import logging
from typing import Optional

from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="File Descriptor existence")
class FileDescriptorExistence(PyFunctionCheck):
    """The file descriptor MUST be present in the RO-Crate and MUST not be empty."""

    @check(name="File Descriptor Existence")
    def test_existence(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is present in the RO-Crate
        """
        if not context.file_descriptor_path.exists():
            message = f'file descriptor "{context.rel_fd_path}" is not present'
            context.result.add_error(message, self)
            return False
        return True

    @check(name="File Descriptor size check")
    def test_size(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is not empty
        """
        if not context.file_descriptor_path.exists():
            message = f'file descriptor {context.rel_fd_path} is empty'
            context.result.add_error(message, self)
            return False
        if context.file_descriptor_path.stat().st_size == 0:
            context.result.add_error(f'RO-Crate "{context.rel_fd_path}" file descriptor is empty', self)
            return False
        return True


@requirement(name="File Descriptor JSON Format")
class FileDescriptorJsonFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON file
    """
    @check(name="File Descriptor JSON Format")
    def check(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor is in the correct format"""
        try:
            logger.debug("Checking validity of JSON file at %s", context.file_descriptor_path)
            with open(context.file_descriptor_path, "r") as file:
                json.load(file)
            return True
        except Exception as e:
            context.result.add_error(
                f'RO-Crate file descriptor "{context.rel_fd_path}" is not in the correct format', self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False


@requirement(name="File Descriptor JSON-LD Format")
class FileDescriptorJsonLdFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON-LD file
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

    @check(name="File Descriptor @context property validation")
    def check_context(self, validation_context: ValidationContext) -> bool:
        """ Check if the file descriptor contains the @context property """
        json_dict = self.get_json_dict(validation_context)
        if "@context" not in json_dict:
            validation_context.result.add_error(
                f'RO-Crate file descriptor "{validation_context.rel_fd_path}" '
                "does not contain a context", self)
            return False
        return True

    @check(name="Validation of the @id property of the file descriptor entities")
    def check_identifiers(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @id property """
        json_dict = self.get_json_dict(context)
        for entity in json_dict["@graph"]:
            if "@id" not in entity:
                context.result.add_error(
                    f"Entity \"{entity.get('name', None) or entity}\" "
                    f"of RO-Crate \"{context.rel_fd_path}\" "
                    "file descriptor does not contain the @id attribute", self)
                return False
        return True

    @check(name="Validation of the @type property of the file descriptor entities")
    def check_types(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @type property """
        json_dict = self.get_json_dict(context)
        for entity in json_dict["@graph"]:
            if "@type" not in entity:
                context.result.add_error(
                    f"Entity \"{entity.get('name', None) or entity}\" "
                    f"of RO-Crate \"{context.rel_fd_path}\" "
                    "file descriptor does not contain the @type attribute", self)
                return False
        return True
