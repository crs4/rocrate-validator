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

"""Unit tests for the JSON-LD document loader."""

from __future__ import annotations

import io

import pytest
import urllib3

from rocrate_validator.utils import document_loader
from rocrate_validator.utils.document_loader import (install_document_loader,
                                                     resolve_remote_document,
                                                     uninstall_document_loader)
from rocrate_validator.utils.http import HttpRequester, OfflineCacheMissError


def _urllib3_response(payload: bytes = b'{"@context": {"name": "https://schema.org/name"}}',
                      status: int = 200) -> urllib3.HTTPResponse:
    return urllib3.HTTPResponse(
        body=io.BytesIO(payload),
        headers={
            "Content-Type": "application/ld+json",
            "Content-Length": str(len(payload)),
        },
        status=status,
        preload_content=False,
        decode_content=False,
    )


@pytest.fixture
def mock_network(monkeypatch):
    from requests.adapters import HTTPAdapter

    def fake_send(self, request, **kwargs):
        raw = _urllib3_response()
        return self.build_response(request, raw)

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)


@pytest.fixture(autouse=True)
def _cleanup():
    uninstall_document_loader()
    HttpRequester.reset()
    yield
    uninstall_document_loader()
    HttpRequester.reset()


def test_install_is_idempotent(tmp_path):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=-1)
    assert install_document_loader() is True
    assert install_document_loader() is True
    assert document_loader._installed is True


def test_install_returns_false_on_error(tmp_path, monkeypatch):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=-1)
    from rdflib.plugins.shared.jsonld import util as jsonld_util

    class _FrozenModule:
        def __setattr__(self, _name, _value):
            raise RuntimeError("boom")

    monkeypatch.setattr(document_loader, "jsonld_util", _FrozenModule())
    assert install_document_loader() is False
    assert document_loader._installed is False
    # Original module must remain untouched on failure.
    assert jsonld_util.source_to_json is document_loader._original_source_to_json


def test_uninstall_returns_true_when_not_installed():
    assert uninstall_document_loader() is True


def test_uninstall_returns_false_on_error(tmp_path, monkeypatch):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=-1)
    assert install_document_loader() is True

    class _FrozenModule:
        def __setattr__(self, _name, _value):
            raise RuntimeError("boom")

    monkeypatch.setattr(document_loader, "jsonld_util", _FrozenModule())
    assert uninstall_document_loader() is False
    assert document_loader._installed is True


def test_resolve_remote_document_uses_http_requester(tmp_path, mock_network):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=60)
    payload, content_type = resolve_remote_document("https://example.org/context")
    assert payload == {"@context": {"name": "https://schema.org/name"}}
    assert content_type == "application/ld+json"
    assert HttpRequester().has_cached("https://example.org/context") is True


def test_resolve_raises_offline_cache_miss(tmp_path):
    HttpRequester.initialize_cache(
        cache_path=str(tmp_path / "cache"),
        cache_max_age=-1,
        offline=True,
    )
    with pytest.raises(OfflineCacheMissError):
        resolve_remote_document("https://example.org/never-cached")


def test_patched_source_to_json_routes_http_urls(tmp_path, mock_network):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=60)
    install_document_loader()
    from rdflib.plugins.shared.jsonld import util as jsonld_util
    doc, _ = jsonld_util.source_to_json("https://example.org/context")
    assert doc == {"@context": {"name": "https://schema.org/name"}}


def test_patched_source_to_json_ignores_non_http(tmp_path):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=60)
    install_document_loader()
    from rdflib.plugins.shared.jsonld import util as jsonld_util
    file_path = tmp_path / "context.jsonld"
    file_path.write_text('{"@context": {"foo": "https://example.org/foo"}}')
    doc, _ = jsonld_util.source_to_json(str(file_path))
    assert doc == {"@context": {"foo": "https://example.org/foo"}}


def test_resolve_maps_http_error_to_runtime(tmp_path, monkeypatch):
    HttpRequester.initialize_cache(cache_path=str(tmp_path / "cache"), cache_max_age=60)

    class _StubResponse:
        status_code = 500
        text = ""

        def json(self):
            raise ValueError

    monkeypatch.setattr(
        HttpRequester(),
        "get",
        lambda *_, **__: _StubResponse(),
    )
    with pytest.raises(RuntimeError):
        resolve_remote_document("https://example.org/broken")
