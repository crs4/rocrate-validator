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

import importlib.util
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def fd_format():
    """Load the module with numeric prefix."""
    spec = importlib.util.spec_from_file_location(
        "fd_format",
        "rocrate_validator/profiles/ro-crate/1.2/must/0_file_descriptor_format.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["fd_format"] = module
    spec.loader.exec_module(module)
    return module


class TestGetRemoteContextLogic:
    """Test the logic of __get_remote_context__ method without needing to instantiate the class."""

    def test_success_with_correct_content_type(self, fd_format):
        """Test successful context retrieval with correct Content-Type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/ld+json"}
        mock_response.json.return_value = {"@context": {"name": "https://schema.org/name"}}

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__check_remote_context__("https://example.com/context.json")
            assert result is True
        finally:
            fd_format.HttpRequester = original_requester

    def test_fallback_to_alternate_link(self, fd_format):
        """Test fallback to alternate Link header when Content-Type is not application/ld+json."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/html",
            "Link": '<https://example.com/alternate-context.json>; rel="alternate"; type="application/ld+json"'
        }

        mock_alternate_response = MagicMock()
        mock_alternate_response.status_code = 200
        mock_alternate_response.headers = {"Content-Type": "application/ld+json"}
        mock_alternate_response.json.return_value = {"@context": {"alternate": "value"}}

        original_requester = fd_format.HttpRequester
        call_count = [0]

        def mock_requester():
            class MockHttpRequester:
                def get(self, url, headers=None):
                    call_count[0] += 1
                    # Return the initial response on the first call,
                    # and the alternate response on the second call
                    if call_count[0] == 1:
                        return mock_response
                    # Return the alternate response for the second call
                    return mock_alternate_response
            return MockHttpRequester()

        fd_format.HttpRequester = mock_requester

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__get_remote_context__("https://example.com/context.json")
            assert result == {"alternate": "value"}
        finally:
            fd_format.HttpRequester = original_requester

    def test_relative_alternate_url_resolution(self, fd_format):
        """Test relative URL resolution for alternate links."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/html",
            "Link": '<./alternate-context.json>; rel="alternate"; type="application/ld+json"'
        }

        mock_alternate_response = MagicMock()
        mock_alternate_response.status_code = 200
        mock_alternate_response.headers = {"Content-Type": "application/ld+json"}
        mock_alternate_response.json.return_value = {"@context": {"relative": "resolved"}}

        original_requester = fd_format.HttpRequester
        call_count = [0]
        call_args_list = []

        def mock_requester():
            class MockHttpRequester:
                def get(self, url, headers=None):
                    call_count[0] += 1
                    call_args_list.append((url, headers))
                    if call_count[0] == 1:
                        return mock_response
                    return mock_alternate_response
            return MockHttpRequester()

        fd_format.HttpRequester = mock_requester

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__get_remote_context__("https://example.com/base/context.json")
            assert result == {"relative": "resolved"}
            assert call_count[0] == 2  # Ensure both requests were made
            # Check that the first request was made to the original context URI
            assert call_args_list[0][0] == "https://example.com/base/context.json", \
                f"The first request should be made to the original context URI " \
                f"{'https://example.com/base/context.json'}, " \
                f"but got {call_args_list[0][0]}"
            # Check that the second request was made to the resolved alternate URL
            assert call_args_list[1][0] == "https://example.com/base/alternate-context.json", \
                f"The second request should be made to the resolved alternate URL " \
                f"{'https://example.com/base/alternate-context.json'}, " \
                f"but got {call_args_list[1][0]}"
        finally:
            fd_format.HttpRequester = original_requester

    def test_no_content_type_no_alternate_raises_error(self, fd_format):
        """Test error when no Content-Type and no alternate Link header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            with pytest.raises(RuntimeError) as exc_info:
                checker.__get_remote_context__("https://example.com/context.json")
            assert "no alternate link found in Link header" in str(exc_info.value)
        finally:
            fd_format.HttpRequester = original_requester

    def test_invalid_alternate_link_format_raises_error(self, fd_format):
        """Test error when alternate Link header format is invalid."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/html",
            "Link": "invalid-link-format"
        }

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            with pytest.raises(RuntimeError) as exc_info:
                checker.__get_remote_context__("https://example.com/context.json")
            assert "no alternate link found" in str(exc_info.value)
        finally:
            fd_format.HttpRequester = original_requester

    def test_failed_request_raises_error(self, fd_format):
        """Test error when HTTP request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            with pytest.raises(RuntimeError) as exc_info:
                checker.__get_remote_context__("https://example.com/context.json")
            assert "Unable to retrieve" in str(exc_info.value)
        finally:
            fd_format.HttpRequester = original_requester

    def test_alternate_request_failed_raises_error(self, fd_format):
        """Test error when alternate URL request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/html",
            "Link": '<https://example.com/alternate-context.json>; rel="alternate"; type="application/ld+json"'
        }

        mock_alternate_response = MagicMock()
        mock_alternate_response.status_code = 500

        original_requester = fd_format.HttpRequester
        call_count = [0]

        def mock_requester():
            class MockHttpRequester:
                def get(self, url, headers=None):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return mock_response
                    return mock_alternate_response
            return MockHttpRequester()

        fd_format.HttpRequester = mock_requester

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            with pytest.raises(RuntimeError) as exc_info:
                checker.__get_remote_context__("https://example.com/context.json")
            assert "Unable to retrieve the JSON-LD context from alternate URL" in str(exc_info.value)
        finally:
            fd_format.HttpRequester = original_requester

    def test_alternate_wrong_content_type_raises_error(self, fd_format):
        """Test error when alternate URL returns wrong Content-Type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/html",
            "Link": '<https://example.com/alternate-context.json>; rel="alternate"; type="application/ld+json"'
        }

        mock_alternate_response = MagicMock()
        mock_alternate_response.status_code = 200
        mock_alternate_response.headers = {"Content-Type": "text/plain"}

        original_requester = fd_format.HttpRequester
        call_count = [0]

        def mock_requester():
            class MockHttpRequester:
                def get(self, url, headers=None):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return mock_response
                    return mock_alternate_response
            return MockHttpRequester()

        fd_format.HttpRequester = mock_requester

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            with pytest.raises(RuntimeError) as exc_info:
                checker.__get_remote_context__("https://example.com/context.json")
            assert "does not have a Content-Type of application/ld+json" in str(exc_info.value)
        finally:
            fd_format.HttpRequester = original_requester


class TestCheckRemoteContext:

    def test_check_remote_context_valid(self, fd_format):
        """Test successful remote context validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/ld+json"}
        mock_response.json.return_value = {"@context": {"name": "https://schema.org/name"}}

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__check_remote_context__("https://example.com/context.json")
            assert result is True
        finally:
            fd_format.HttpRequester = original_requester

    def test_check_remote_context_invalid(self, fd_format):
        """Test failed remote context validation."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__check_remote_context__("https://example.com/context.json")
            assert result is False
        finally:
            fd_format.HttpRequester = original_requester


class TestGetContextKeys:

    def test_get_context_keys_from_string(self, fd_format):
        """Test getting context keys from a remote URI string."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/ld+json"}
        mock_response.json.return_value = {"@context": {"key1": "value1", "key2": "value2"}}

        original_requester = fd_format.HttpRequester
        fd_format.HttpRequester = lambda: MagicMock(get=lambda url, headers=None: mock_response)

        try:
            checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)
            result = checker.__get_context_keys__("https://example.com/context.json")
            assert result == {"key1", "key2"}
        finally:
            fd_format.HttpRequester = original_requester

    def test_get_context_keys_from_dict(self, fd_format):
        """Test getting context keys from a dictionary."""
        checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)

        ctx = {"key1": "value1", "key2": "value2"}
        result = checker.__get_context_keys__(ctx)
        assert result == {"key1", "key2"}

    def test_get_context_keys_from_list(self, fd_format):
        """Test getting context keys from a list of contexts."""
        checker = object.__new__(fd_format.FileDescriptorJsonLdFormat)

        ctx1 = {"key1": "value1"}
        ctx2 = {"key2": "value2"}
        result = checker.__get_context_keys__([ctx1, ctx2])
        assert result == {"key1", "key2"}
