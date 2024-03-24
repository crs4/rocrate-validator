import json
import logging
from typing import Optional, Tuple

from rocrate_validator.models import RequirementCheck, check

# set up logging
logger = logging.getLogger(__name__)


class FileDescriptorExistence(RequirementCheck):
    """The file descriptor MUST be present in the RO-Crate and MUST not be empty."""
    @check(name="File Description Existence")
    def test_existence(self) -> bool:
        """
        Check if the file descriptor is present in the RO-Crate
        """
        if not self.file_descriptor_path.exists():
            self.result.add_error(f'RO-Crate "{self.file_descriptor_path}" file descriptor is not present', self)
            return False
        return True

    @check(name="File size check")
    def test_size(self) -> bool:
        """
        Check if the file descriptor is not empty
        """
        if not self.file_descriptor_path.exists():
            self.result.add_error(
                f'RO-Crate "{self.file_descriptor_path}" is empty: file descriptor is not present', self)
            return False
        if self.file_descriptor_path.stat().st_size == 0:
            self.result.add_error(f'RO-Crate "{self.file_descriptor_path}" file descriptor is empty', self)
            return False
        return True


class FileDescriptorJsonFormat(RequirementCheck):
    """
    The file descriptor MUST be a valid JSON file
    """
    @check(name="Check JSON Format of the file descriptor")
    def check(self) -> Tuple[int, Optional[str]]:
        # check if the file descriptor is in the correct format
        try:
            with open(self.file_descriptor_path, "r") as file:
                json.load(file)
            return True
        except Exception as e:
            self.result.add_error(
                f'RO-Crate "{self.file_descriptor_path}" "\
                    "file descriptor is not in the correct format', self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return False


class FileDescriptorJsonLdFormat(RequirementCheck):
    """
    The file descriptor MUST be a valid JSON-LD file
    """

    _json_dict: Optional[dict] = None

    @property
    def json_dict(self):
        if self._json_dict is None:
            self._json_dict = self.get_json_dict()
        return self._json_dict

    def get_json_dict(self):
        try:
            with open(self.file_descriptor_path, "r") as file:
                return json.load(file)
        except Exception as e:
            self.result.add_error(
                f"RO-Crate \"{self.file_descriptor_path}\" "
                "file descriptor is not in the correct format", self)
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return {}

    @check(name="Check if the @context property is present in the file descriptor")
    def check_context(self) -> Tuple[int, Optional[str]]:
        json_dict = self.json_dict
        if "@context" not in json_dict:
            self.result.add_error(
                f"RO-Crate \"{self.file_descriptor_path}\" "
                "file descriptor does not contain a context", self)
            return False
        return True

    @check(name="Check if descriptor entities have the @id property")
    def check_identifiers(self) -> Tuple[int, Optional[str]]:
        json_dict = self.json_dict
        for entity in json_dict["@graph"]:
            if "@id" not in entity:
                self.result.add_error(
                    f"Entity \"{entity.get('name', None) or entity}\" "
                    f"of RO-Crate \"{self.file_descriptor_path}\" "
                    "file descriptor does not contain the @id attribute", self)
                return False

    @check(name="Check if descriptor entities have the @type property")
    def check_types(self) -> Tuple[int, Optional[str]]:
        json_dict = self.json_dict
        for entity in json_dict["@graph"]:
            if "@type" not in entity:
                self.result.add_error(
                    f"Entity \"{entity.get('name', None) or entity}\" "
                    f"of RO-Crate \"{self.file_descriptor_path}\" "
                    "file descriptor does not contain the @type attribute", self)
                return False
