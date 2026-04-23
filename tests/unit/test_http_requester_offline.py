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

"""Unit tests for the HttpRequester offline-mode extensions."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
import urllib3

from rocrate_validator.utils import http as http_module
from rocrate_validator.utils.http import (OFFLINE_CACHE_MISS_STATUS,
                                          HttpRequester)


def _build_urllib3_response(body: bytes = b'{"ok": true}',
                            status: int = 200,
                            content_type: str = "application/json") -> urllib3.HTTPResponse:
    return urllib3.HTTPResponse(
        body=io.BytesIO(body),
        headers={"Content-Type": content_type, "Content-Length": str(len(body))},
        status=status,
        preload_content=False,
        decode_content=False,
    )


@pytest.fixture
def mock_network(monkeypatch):
    """Route every outbound HTTP call to a fake urllib3 response."""
    from requests.adapters import HTTPAdapter

    def fake_send(self, request, **kwargs):
        raw = _build_urllib3_response()
        response = self.build_response(request, raw)
        return response

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)


@pytest.fixture(autouse=True)
def _reset_singleton():
    HttpRequester.reset()
    yield
    HttpRequester.reset()


def _initialize(cache_path, offline=False, cache_max_age=-1):
    HttpRequester.reset()
    return HttpRequester.initialize_cache(
        cache_path=str(cache_path),
        cache_max_age=cache_max_age,
        offline=offline,
    )


def test_initialize_offline_sets_only_if_cached(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=True)
    assert requester.offline is True
    assert getattr(requester.session.settings, "only_if_cached", False) is True


def test_offline_cache_miss_returns_504(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=True)
    response = requester.get("https://example.org/missing")
    assert response.status_code == OFFLINE_CACHE_MISS_STATUS


def test_online_unknown_url_is_not_cached(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    assert requester.has_cached("https://example.org/anything") is False


def test_has_cached_returns_true_after_successful_fetch(tmp_path, mock_network):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    url = "https://example.org/ctx"
    assert requester.has_cached(url) is False
    response = requester.get(url)
    assert response.status_code == 200
    assert requester.has_cached(url) is True


def test_offline_serves_cached_response_populated_online(tmp_path, mock_network):
    cache_path = tmp_path / "cache"
    requester = _initialize(cache_path, offline=False, cache_max_age=60)
    url = "https://example.org/ctx"
    requester.get(url)
    HttpRequester.reset()
    # Re-open the cache in offline mode and confirm the hit.
    requester = _initialize(cache_path, offline=True)
    response = requester.get(url)
    assert response.status_code == 200
    assert response.content == b'{"ok": true}'


def test_fetch_fresh_bypasses_cache_when_online(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    session_mock = MagicMock()
    fresh_response = MagicMock()
    fresh_response.status_code = 200
    fresh_response.from_cache = False
    session_mock.get.return_value = fresh_response
    requester.session = session_mock
    result = requester.fetch_fresh("https://example.org/fresh", allow_redirects=True)
    assert result is fresh_response
    session_mock.get.assert_called_once()
    kwargs = session_mock.get.call_args.kwargs
    assert kwargs.get("force_refresh") is True
    assert kwargs.get("allow_redirects") is True


def test_fetch_fresh_falls_back_when_force_refresh_unsupported(tmp_path):
    """Older requests_cache versions lack force_refresh; fall back to refresh."""
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)

    class _LegacySession:
        def __init__(self):
            self.calls: list[dict] = []

        def get(self, url, **kwargs):
            self.calls.append(kwargs)
            if "force_refresh" in kwargs:
                raise TypeError("unexpected keyword argument 'force_refresh'")
            fake = MagicMock()
            fake.status_code = 200
            fake.from_cache = False
            return fake

    legacy = _LegacySession()
    requester.session = legacy
    response = requester.fetch_fresh("https://example.org/fresh")
    assert response.status_code == 200
    assert len(legacy.calls) == 2
    assert "refresh" in legacy.calls[1]


def test_fetch_fresh_in_offline_does_not_refresh(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=True)
    session_mock = MagicMock()
    cached_response = MagicMock()
    cached_response.status_code = 200
    cached_response.from_cache = True
    session_mock.get.return_value = cached_response
    requester.session = session_mock
    result = requester.fetch_fresh("https://example.org/x")
    assert result is cached_response
    assert "force_refresh" not in session_mock.get.call_args.kwargs
    assert "refresh" not in session_mock.get.call_args.kwargs


def test_clear_cache_empties_backend(tmp_path, mock_network):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    requester.get("https://example.org/a")
    requester.get("https://example.org/b")
    assert requester.cache_info()["entries"] >= 2
    requester.clear_cache()
    assert requester.cache_info()["entries"] == 0


def test_cache_info_reports_metadata(tmp_path):
    cache_path = tmp_path / "cache"
    requester = _initialize(cache_path, offline=False, cache_max_age=60)
    info = requester.cache_info()
    assert info["backend"] == "SQLiteCache"
    assert info["path"].endswith(".sqlite")
    assert info["permanent"] is True
    assert info["offline"] is False
    assert info["entries"] == 0


class _RecordCollector:
    """Context manager that attaches a capturing handler to the http logger."""

    def __init__(self):
        self.records: list = []

    def __enter__(self):
        import logging as _logging

        from rocrate_validator.utils import http as http_module
        self.records.clear()
        self.handler = _logging.Handler()
        self.handler.setLevel(_logging.DEBUG)
        self.handler.emit = lambda record: self.records.append(record)  # type: ignore[assignment]
        # Force initialization of the underlying logger via the proxy.
        http_module.logger.warning  # noqa: B018
        self._target = http_module.logger._instance
        self._target.addHandler(self.handler)
        self._previous_level = self._target.level
        self._target.setLevel(_logging.DEBUG)
        return self

    def __exit__(self, exc_type, exc, tb):
        self._target.removeHandler(self.handler)
        self._target.setLevel(self._previous_level)
        return False

    def messages(self) -> list[str]:
        return [r.getMessage() for r in self.records]


def test_offline_prefix_logs_remote_then_cache(tmp_path, mock_network):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    with _RecordCollector() as collector:
        requester.get("https://example.org/ctx")
        requester.get("https://example.org/ctx")
    messages = [m for m in collector.messages() if "CachedHttpRequester:" in m]
    assert any("fetched from remote" in m for m in messages)
    assert any("served from HTTP cache" in m for m in messages)


def test_offline_prefix_logs_cache_miss_in_offline_mode(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=True)
    with _RecordCollector() as collector:
        requester.get("https://example.org/unknown")
    messages = [m for m in collector.messages() if "CachedHttpRequester:" in m]
    assert any("not available in HTTP cache" in m for m in messages)


def test_offline_prefix_logs_fetch_fresh_as_refresh(tmp_path, mock_network):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    # Populate the cache first.
    requester.get("https://example.org/x")
    with _RecordCollector() as collector:
        requester.fetch_fresh("https://example.org/x")
    messages = [m for m in collector.messages() if "CachedHttpRequester:" in m]
    assert any("cache refresh" in m for m in messages)


def test_offline_without_requests_cache_uses_fallback_session(tmp_path, monkeypatch):
    """When requests_cache is unavailable, offline mode falls back to a 504 stub."""
    original_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "requests_cache" or (fromlist and "CachedSession" in fromlist and name.endswith("requests_cache")):
            raise ImportError("simulated missing dependency")
        return original_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        requester = _initialize(tmp_path / "cache", offline=True)
    assert isinstance(requester.session, http_module._OfflineFallbackSession)
    response = requester.get("https://example.org/whatever")
    assert response.status_code == OFFLINE_CACHE_MISS_STATUS
