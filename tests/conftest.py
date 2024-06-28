# calculate the absolute path of the rocrate-validator package
# and add it to the system path
import os

from pytest import fixture

import rocrate_validator.log as logging

# set up logging
logging.basicConfig(
    level="warning",
    modules_config={
        # "rocrate_validator.models": {"level": logging.DEBUG}
    }
)

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

# test data paths
TEST_DATA_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "data"))

# profiles paths
PROFILES_PATH = os.path.abspath(f"{CURRENT_PATH}/../rocrate_validator/profiles")


@fixture
def random_path():
    return "/tmp/random_path"


@fixture
def ro_crates_path():
    return f"{TEST_DATA_PATH}/crates"


@fixture
def fake_profiles_path():
    return f"{TEST_DATA_PATH}/profiles/fake"


@fixture
def profiles_with_free_folder_structure_path():
    return f"{TEST_DATA_PATH}/profiles/free_folder_structure"


@fixture
def fake_versioned_profiles_path():
    return f"{TEST_DATA_PATH}/profiles/fake_versioned_profiles"


@fixture
def fake_conflicting_versioned_profiles_path():
    return f"{TEST_DATA_PATH}/profiles/conflicting_versions"


@fixture
def graphs_path():
    return f"{TEST_DATA_PATH}/graphs"


@fixture
def profiles_path():
    return PROFILES_PATH


@fixture
def graph_books_path():
    return f"{TEST_DATA_PATH}/graphs/books"


@fixture
def ro_crate_profile_path(profiles_path):
    return os.path.join(profiles_path, "ro-crate")


@fixture
def ro_crate_profile_must_path(ro_crate_profile_path):
    return os.path.join(ro_crate_profile_path, "must")


@fixture
def ro_crate_profile_should_path(ro_crate_profile_path):
    return os.path.join(ro_crate_profile_path, "should")


@fixture
def ro_crate_profile_may_path(ro_crate_profile_path):
    return os.path.join(ro_crate_profile_path, "may")
