# calculate the absolute path of the rocrate-validator package
# and add it to the system path
import os

from pytest import fixture
from rocrate_validator.config import configure_logging

import logging

# set up logging
configure_logging(level=logging.DEBUG)

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_DATA_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "data"))


@fixture
def random_path():
    return "/tmp/random_path"


@fixture
def ro_crates_path():
    return f"{TEST_DATA_PATH}/crates"


@fixture
def graphs_path():
    return f"{TEST_DATA_PATH}/graphs"


@fixture
def graph_books_path():
    return f"{TEST_DATA_PATH}/graphs/books"
