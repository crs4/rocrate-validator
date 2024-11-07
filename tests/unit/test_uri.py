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

import unittest

import pytest

from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.utils import URI, validate_rocrate_uri
from tests.ro_crates import ValidROC


def test_valid_url():
    uri = URI("http://example.com")
    assert uri.is_remote_resource()


def test_invalid_url():
    with pytest.raises(ValueError):
        URI("httpx:///example.com")


def test_url_with_query_params():
    uri = URI("http://example.com?param1=value1&param2=value2")
    assert uri.get_query_param("param1") == "value1"
    assert uri.get_query_param("param2") == "value2"


def test_url_without_query_params():
    uri = URI("http://example.com")
    assert uri.get_query_param("param1") is None


def test_url_with_fragment():
    uri = URI("http://example.com#fragment")
    assert uri.fragment == "fragment"


def test_url_without_fragment():
    uri = URI("http://example.com")
    assert uri.fragment is None


def test_valid_path():
    uri = URI("README.md")
    assert uri.is_local_resource()
    assert uri.is_available()


def test_invalid_path():
    uri = URI("path/to/file.txt")
    assert not uri.is_available()


def test_path_with_query_params():
    uri = URI("/path/to/file.txt?param1=value1&param2=value2")
    assert uri.get_query_param("param1") == "value1"
    assert uri.get_query_param("param2") == "value2"


def test_path_without_query_params():
    uri = URI("/path/to/file.txt")
    assert uri.get_query_param("param1") is None


def test_path_with_fragment():
    uri = URI("/path/to/file.txt#fragment")
    assert uri.fragment == "fragment"


def test_path_without_fragment():
    uri = URI("/path/to/file.txt")
    assert uri.fragment is None


def test_rocrate_uri_local_folder_valid():
    uri = URI(ValidROC().workflow_roc)
    assert validate_rocrate_uri(uri), f"The URI {uri} should be valid"


def test_rocrate_uri_local_folder_invalid():
    # Test with a non-existent folder
    uri = URI("path/to/folder")
    # Use silent mode to avoid printing the error message
    assert not validate_rocrate_uri(uri, silent=True), f"The URI {uri} should be invalid"

    # Use verbose mode to print the error message
    with pytest.raises(ROCrateInvalidURIError) as excinfo:
        validate_rocrate_uri(uri, silent=False)
    assert str(
        excinfo.value) == f"\"{uri}\" is not a valid RO-Crate URI. "\
        "It MUST be either a local path to the RO-Crate root directory "\
        "or a local/remote RO-Crate ZIP file."


def test_rocrate_uri_local_zip_valid():
    uri = URI(ValidROC().sort_and_change_archive)
    assert validate_rocrate_uri(uri), f"The URI {uri} should be valid"


def test_rocrate_uri_local_zip_invalid():
    # Test with a non-existent zip file
    uri = URI("path/to/zipfile.zip")
    # Use silent mode to avoid printing the error message
    assert not validate_rocrate_uri(uri, silent=True), f"The URI {uri} should be invalid"

    # Use verbose mode to print the error message
    with pytest.raises(ROCrateInvalidURIError) as excinfo:
        validate_rocrate_uri(uri, silent=False)
    assert str(
        excinfo.value) == f"\"{uri}\" is not a valid RO-Crate URI. "\
        "It MUST be either a local path to the RO-Crate root directory "\
        "or a local/remote RO-Crate ZIP file."


def test_rocrate_uri_remote_valid():
    uri = URI(ValidROC().sort_and_change_remote)
    assert validate_rocrate_uri(uri), f"The URI {uri} should be valid"


def test_rocrate_uri_remote_invalid():

    with pytest.raises(ValueError) as excinfo:
        URI("httpx:///example.com")
    assert str(excinfo.value) == "Invalid URI: httpx:///example.com"

    # Test with an invalid remote URL
    uri = URI("https:///example.com")
    # Use silent mode to avoid printing the error message
    assert not validate_rocrate_uri(uri, silent=True), f"The URI {uri} should be invalid"

    # Use verbose mode to print the error message
    with pytest.raises(ROCrateInvalidURIError) as excinfo:
        validate_rocrate_uri(uri, silent=False)
    assert str(
        excinfo.value) == f"The RO-crate at the URI \"{uri}\" is not available"


if __name__ == '__main__':
    unittest.main()
