# Copyright (c) 2024 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rocrate_validator.log as logging
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
        if not context.ro_crate.has_descriptor():
            message = f'file descriptor "{context.rel_fd_path}" is not present'
            context.result.add_error(message, self)
            return False
        return True

    @check(name="File Descriptor size check")
    def test_size(self, context: ValidationContext) -> bool:
        """
        Check if the file descriptor is not empty
        """
        if not context.ro_crate.has_descriptor():
            message = f'file descriptor {context.rel_fd_path} is empty'
            context.result.add_error(message, self)
            return False
        if context.ro_crate.metadata.size == 0:
            context.result.add_error(f'RO-Crate "{context.rel_fd_path}" file descriptor is empty', self)
            return False
        return True


@requirement(name="File Descriptor JSON format")
class FileDescriptorJsonFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON file
    """
    @check(name="File Descriptor JSON format")
    def check(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor is in the correct format"""
        try:
            logger.debug("Checking validity of JSON file at %s", context.ro_crate.metadata)
            context.ro_crate.metadata.as_dict()
            return True
        except Exception as e:
            context.result.add_error(
                f'RO-Crate file descriptor "{context.rel_fd_path}" is not in the correct format', self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False


@requirement(name="File Descriptor JSON-LD format")
class FileDescriptorJsonLdFormat(PyFunctionCheck):
    """
    The file descriptor MUST be a valid JSON-LD file
    """

    @check(name="File Descriptor @context property validation")
    def check_context(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor contains the @context property """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            if "@context" not in json_dict:
                context.result.add_error(
                    f'RO-Crate file descriptor "{context.rel_fd_path}" '
                    "does not contain a context", self)
                return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    @check(name="Validation of the @id property of the file descriptor entities")
    def check_identifiers(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @id property """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@id" not in entity:
                    context.result.add_error(
                        f"Entity \"{entity.get('name', None) or entity}\" "
                        f"of RO-Crate \"{context.rel_fd_path}\" "
                        "file descriptor does not contain the @id attribute", self)
                    return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False

    @check(name="Validation of the @type property of the file descriptor entities")
    def check_types(self, context: ValidationContext) -> bool:
        """ Check if the file descriptor entities have the @type property """
        try:
            json_dict = context.ro_crate.metadata.as_dict()
            for entity in json_dict["@graph"]:
                if "@type" not in entity:
                    context.result.add_error(
                        f"Entity \"{entity.get('name', None) or entity}\" "
                        f"of RO-Crate \"{context.rel_fd_path}\" "
                        "file descriptor does not contain the @type attribute", self)
                    return False
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
        return False
