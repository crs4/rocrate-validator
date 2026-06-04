# Copyright (c) 2024-2026 CRS4
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
from rocrate_validator.utils.uri import URI, validate_rocrate_uri
from tests.ro_crates import ValidROC


def test_valid_url():
    uri = URI("http://example.com")
    assert uri.is_remote_resource()
    assert uri.is_natively_checkable()
    assert uri.has_supported_rocrate_scheme()


def test_uri_with_unknown_scheme_is_accepted_but_not_supported_as_rocrate_root():
    # Schemes outside the natively-supported set are valid URIs (they may
    # appear as Data Entity identifiers, e.g. scp://, s3://) but they are
    # not accepted as RO-Crate root URIs.
    uri = URI("httpx:///example.com")
    assert uri.is_remote_resource()
    assert not uri.is_natively_checkable()
    assert not uri.has_supported_rocrate_scheme()


def test_invalid_url():
    # A bare token without any scheme/path separator is not a valid URI.
    with pytest.raises(ValueError):
        URI("")


def test_scp_uri_is_remote():
    uri = URI("scp://transfer.example.org//data/A.0.0")
    assert uri.is_remote_resource()
    assert uri.is_known_remote_scheme()
    assert not uri.is_natively_checkable()


def test_s3_uri_is_remote():
    uri = URI("s3://bucket/key/path")
    assert uri.is_remote_resource()
    assert uri.is_known_remote_scheme()
    assert not uri.is_natively_checkable()


@pytest.mark.parametrize("uri_str,expected_scheme", [
    # Scheme-only (no authority) absolute URIs are valid per RFC 3986 and
    # accepted by RO-Crate 1.1 § 4.2.2 as Data Entity `@id` values.
    ("urn:doi:10.5281/zenodo.1234", "urn"),
    ("doi:10.5281/zenodo.1234", "doi"),
    ("arcp://name,foo/bar", "arcp"),
])
def test_scheme_only_absolute_uri_is_remote(uri_str, expected_scheme):
    uri = URI(uri_str)
    assert uri.scheme == expected_scheme
    assert uri.is_remote_resource()
    assert not uri.is_natively_checkable()


def test_file_uri_with_remote_host_is_remote():
    # A `file://` URI carrying a (non-local) authority points to a file on
    # another host (RFC 8089) and must be treated as remote, not as a local
    # payload member (regression for issue #176 with `file://` schemes).
    uri = URI("file://gs02r3b58-ib0/scratch/tmp/5190874/tmp_rf_samples_slt86rc0")
    assert uri.scheme == "file"
    assert uri.is_remote_resource()
    assert not uri.is_local_resource()
    assert not uri.is_natively_checkable()


@pytest.mark.parametrize("uri_str", [
    "file:///absolute/path/file.txt",
    "file://localhost/absolute/path/file.txt",
])
def test_file_uri_to_local_host_is_local(uri_str):
    # An empty or `localhost` authority denotes the local machine.
    uri = URI(uri_str)
    assert uri.scheme == "file"
    assert uri.is_local_resource()
    assert not uri.is_remote_resource()


@pytest.mark.parametrize("path", ["README.md", "data/file.txt", "./", "/abs/dir"])
def test_local_path_never_gains_a_spurious_host(path):
    # Plain filesystem paths are normalized to authority-less `file:` URIs, so
    # the first path segment is never mistaken for a remote host.
    uri = URI(path)
    assert uri.is_local_resource()
    assert not uri.is_remote_resource()
    assert uri.get_netloc() == ""


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
    # An unknown scheme is a valid URI but cannot be used as an RO-Crate root.
    uri = URI("httpx:///example.com")
    assert not validate_rocrate_uri(uri, silent=True), \
        f"The URI {uri} should not be accepted as an RO-Crate root"
    with pytest.raises(ROCrateInvalidURIError):
        validate_rocrate_uri(uri, silent=False)

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
