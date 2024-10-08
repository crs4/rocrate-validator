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

from rocrate_validator.utils import URI


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


if __name__ == '__main__':
    unittest.main()
