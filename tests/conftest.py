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
def check_overriding_profiles_path():
    return f"{TEST_DATA_PATH}/profiles/check_overriding"


@fixture
def profiles_requirement_loading():
    return f"{TEST_DATA_PATH}/profiles/requirement_loading"


@fixture
def profiles_loading_hidden_requirements():
    return f"{TEST_DATA_PATH}/profiles/hidden_requirements"


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


@fixture(params=[
    "2024 01 01",
    "2024 Jan 01",
    "2021-13-01",
    "2021-00-10",
    "2021-01-32",
    "2021-01-01T25:00",
    "2021-01-01T23:60",
    "2021-01-01T23:59:60",
    "T23:59:59",
])
def invalid_datetime(request):
    return request.param


@fixture(params=[
    "2024",
    "2024-01",
    "202401",
    "2024-01-01",
    "20240101",
    "2024-001",
    "2024-W01",
    "2024-W01-1",
    "2024-01-01T00:00",
    "2024-01-01T00:00:00",
    "2024-01-01T00:00:00Z",
    "2024-01-01T00:00:00+00:00",
    "2024-01-01T00:00:00.000",
    "2024-01-01T00:00:00.000Z",
    "2024-01-01T00:00:00.000+00:00",
])
def valid_datetime(request):
    return request.param
