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

