import os

from pytest import fixture

import logging

logging.basicConfig(level=logging.DEBUG)

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_DATA_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "data"))
CRATES_DATA_PATH = f"{TEST_DATA_PATH}/crates"
VALID_CRATES_DATA_PATH = f"{CRATES_DATA_PATH}/valid"
INVALID_CRATES_DATA_PATH = f"{CRATES_DATA_PATH}/invalid"


@fixture
def ro_crates_path():
    return CRATES_DATA_PATH


class InvalidFileDescriptor:

    base_path = f"{INVALID_CRATES_DATA_PATH}/0_file_descriptor"

    @property
    def missing_file_descriptor(self):
        return f"{self.base_path}/missing_file_descriptor"
