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

"""Unit tests for profile URL discovery and cache warm-up."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import urllib3

from rocrate_validator.models import Profile
from rocrate_validator.utils.cache_warmup import (
    auto_warm_up_for_settings, discover_cacheable_urls_from_profiles,
    discover_profile_cacheable_urls, warm_up_urls)
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import get_profiles_path


PROFILE_TTL_TEMPLATE = """
@prefix dct: <http://purl.org/dc/terms/> .
@prefix prof: <http://www.w3.org/ns/dx/prof/> .
@prefix role: <http://www.w3.org/ns/dx/prof/role/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<https://example.org/profiles/sample>
    a prof:Profile ;
    rdfs:label "Sample profile" ;
    prof:hasResource [
        a prof:ResourceDescriptor ;
        prof:hasRole role:Vocabulary ;
        prof:hasArtifact <https://example.org/ctx/v1> ;
    ] ;
    prof:hasResource [
        a prof:ResourceDescriptor ;
        prof:hasRole role:Specification ;
        prof:hasArtifact <https://example.org/spec/v1/index.html> ;
    ] ;
    prof:hasResource [
        a prof:ResourceDescriptor ;
        prof:hasArtifact "not-a-url" ;
    ] ;
    prof:hasToken "sample" ;
.
"""


@pytest.fixture(autouse=True)
def _reset_requester():
    HttpRequester.reset()
    yield
    HttpRequester.reset()


@pytest.fixture
def sample_profile(tmp_path):
    profile_dir = tmp_path / "sample"
    profile_dir.mkdir()
    (profile_dir / "profile.ttl").write_text(PROFILE_TTL_TEMPLATE)
    return Profile(
        profiles_base_path=tmp_path,
        profile_path=profile_dir,
    )


@pytest.fixture
def mock_network(monkeypatch):
    from requests.adapters import HTTPAdapter

    def fake_send(self, request, **kwargs):
        raw = urllib3.HTTPResponse(
            body=io.BytesIO(b'{"ok": true}'),
            headers={"Content-Type": "application/json", "Content-Length": "12"},
            status=200,
            preload_content=False,
            decode_content=False,
        )
        return self.build_response(request, raw)

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)


def test_discover_urls_returns_all_declared_artifacts(sample_profile):
    urls = discover_profile_cacheable_urls(sample_profile)
    # Both declared roles are included; the non-URL artifact is dropped.
    assert "https://example.org/ctx/v1" in urls
    assert "https://example.org/spec/v1/index.html" in urls
    assert all(u.lower().startswith("http") for u in urls)
    assert len(urls) == 2


def test_discover_urls_on_multiple_profiles_deduplicates(sample_profile, tmp_path):
    other_dir = tmp_path / "sample_other"
    other_dir.mkdir()
    (other_dir / "profile.ttl").write_text(
        PROFILE_TTL_TEMPLATE
        .replace("<https://example.org/profiles/sample>",
                 "<https://example.org/profiles/other>")
        .replace('prof:hasToken "sample"', 'prof:hasToken "other"')
    )
    other_profile = Profile(profiles_base_path=tmp_path, profile_path=other_dir)
    aggregated = discover_cacheable_urls_from_profiles([sample_profile, other_profile])
    # Both profiles share the same two artifacts; the result should be deduped.
    assert len(aggregated) == 2


def test_warm_up_urls_skips_already_cached(tmp_path, mock_network):
    HttpRequester.initialize_cache(
        cache_path=str(tmp_path / "cache"),
        cache_max_age=60,
    )
    urls = ["https://example.org/a", "https://example.org/b"]
    first = warm_up_urls(urls)
    assert [r.status for r in first] == ["ok", "ok"]
    second = warm_up_urls(urls)
    assert [r.status for r in second] == ["skipped", "skipped"]


def test_warm_up_reports_offline_cache_miss(tmp_path):
    HttpRequester.initialize_cache(
        cache_path=str(tmp_path / "cache"),
        cache_max_age=-1,
        offline=True,
    )
    results = warm_up_urls(["https://example.org/missing"])
    assert results[0].status == "failed"
    assert "offline" in (results[0].detail or "").lower()


def test_auto_warm_up_noop_when_offline(tmp_path):
    class _Settings:
        offline = True
        cache_path = tmp_path / "cache"
        profile_identifier = "ro-crate-1.1"
        profiles_path = get_profiles_path()
        extra_profiles_path = None

    assert auto_warm_up_for_settings(_Settings()) is None


def test_auto_warm_up_disabled_via_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ROCRATE_VALIDATOR_AUTO_WARM", "0")

    class _Settings:
        offline = False
        cache_path = tmp_path / "cache"
        profile_identifier = "ro-crate-1.1"
        profiles_path = get_profiles_path()
        extra_profiles_path = None

    assert auto_warm_up_for_settings(_Settings()) is None


def test_auto_warm_up_noop_when_no_cache_path():
    class _Settings:
        offline = False
        cache_path = None
        profile_identifier = "ro-crate-1.1"
        profiles_path = get_profiles_path()
        extra_profiles_path = None

    assert auto_warm_up_for_settings(_Settings()) is None
