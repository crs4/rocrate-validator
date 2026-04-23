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

"""Integration tests for offline mode, auto warm-up and the cache CLI."""

from __future__ import annotations

import io

import pytest
import urllib3
from click.testing import CliRunner

from rocrate_validator.cli.main import cli
from rocrate_validator.models import ValidationSettings
from rocrate_validator.utils.http import (OFFLINE_CACHE_MISS_STATUS,
                                          HttpRequester)
from tests.conftest import SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER
from tests.ro_crates import ValidROC


def _urllib3_response(payload: bytes = b'{"@context": {}}',
                      status: int = 200,
                      content_type: str = "application/ld+json") -> urllib3.HTTPResponse:
    return urllib3.HTTPResponse(
        body=io.BytesIO(payload),
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(payload)),
        },
        status=status,
        preload_content=False,
        decode_content=False,
    )


@pytest.fixture
def network_interceptor(monkeypatch):
    """
    Intercept every outbound HTTP call and record the requested URLs so tests
    can assert whether the cache was actually consulted.
    """
    from requests.adapters import HTTPAdapter

    recorder = {"calls": []}

    def fake_send(self, request, **kwargs):
        recorder["calls"].append(request.url)
        return self.build_response(request, _urllib3_response())

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)
    return recorder


@pytest.fixture(autouse=True)
def _clean_singleton(monkeypatch):
    monkeypatch.setenv("ROCRATE_VALIDATOR_AUTO_WARM", "0")
    HttpRequester.reset()
    yield
    HttpRequester.reset()


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_offline_flag_configures_cache(tmp_path):
    settings = ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
        cache_path=tmp_path / "cache",
    )
    info = HttpRequester().cache_info()
    assert info["offline"] is True
    assert info["permanent"] is True
    assert settings.offline is True


def test_offline_default_path_is_persistent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
        cache_path=None,
    )
    info = HttpRequester().cache_info()
    assert info["offline"] is True
    assert info["permanent"] is True
    assert str(tmp_path / "xdg") in str(info["path"])


def test_offline_cache_miss_yields_504_response(tmp_path):
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
        cache_path=tmp_path / "cache",
    )
    response = HttpRequester().get("https://example.org/never")
    assert response.status_code == OFFLINE_CACHE_MISS_STATUS


def test_online_then_offline_share_default_cache(tmp_path, network_interceptor, monkeypatch):
    """Reproduce the common user workflow: validate online without passing a
    cache path, then validate offline without passing a cache path. Both runs
    must share the same persistent XDG cache so the offline run finds every
    resource fetched online.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    url = "https://example.org/ctx"

    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=False,
        cache_max_age=60,
    )
    online_info = HttpRequester().cache_info()
    assert online_info["permanent"] is True
    assert str(tmp_path / "xdg") in str(online_info["path"])
    HttpRequester().get(url)
    assert HttpRequester().has_cached(url) is True

    HttpRequester.reset()

    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
    )
    offline_info = HttpRequester().cache_info()
    assert offline_info["path"] == online_info["path"]
    assert HttpRequester().has_cached(url) is True
    response = HttpRequester().get(url)
    assert response.status_code == 200


def test_offline_reuses_cached_response(tmp_path, network_interceptor):
    cache_path = tmp_path / "cache"
    # First: online run populates the cache.
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=False,
        cache_path=cache_path,
        cache_max_age=60,
    )
    url = "https://example.org/context"
    response = HttpRequester().get(url)
    assert response.status_code == 200
    assert HttpRequester().has_cached(url) is True
    pre_calls = len(network_interceptor["calls"])

    # Second: offline run must not hit the network but still get the cached doc.
    HttpRequester.reset()
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
        cache_path=cache_path,
    )
    response = HttpRequester().get(url)
    assert response.status_code == 200
    assert response.content == b'{"@context": {}}'
    # No new network traffic in offline mode.
    assert len(network_interceptor["calls"]) == pre_calls


def test_no_cache_disables_cache_backend(tmp_path, network_interceptor):
    """no_cache=True must skip the cache and hit the network every call."""
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=False,
        no_cache=True,
    )
    requester = HttpRequester()
    info = requester.cache_info()
    assert info["backend"] is None
    assert requester.has_cached("https://example.org/any") is False
    # Two identical requests must both hit the network.
    requester.get("https://example.org/any")
    requester.get("https://example.org/any")
    assert network_interceptor["calls"].count("https://example.org/any") == 2


def test_negative_cache_max_age_means_never_expire(tmp_path, network_interceptor):
    """cache_max_age<0 must enable the cache with no expiration."""
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=False,
        cache_max_age=-1,
        cache_path=tmp_path / "cache",
    )
    requester = HttpRequester()
    info = requester.cache_info()
    assert info["backend"] is not None
    url = "https://example.org/any"
    requester.get(url)
    # Second call must be served from the cache.
    requester.get(url)
    assert network_interceptor["calls"].count(url) == 1


def test_offline_with_disabled_cache_raises():
    with pytest.raises(ValueError, match="Offline mode requires the HTTP cache"):
        ValidationSettings(
            rocrate_uri=str(ValidROC().wrroc_paper_long_date),
            offline=True,
            no_cache=True,
        )


def test_cli_no_cache_and_offline_rejected(cli_runner):
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--no-paging",
            "--no-cache",
            "--offline",
        ],
    )
    assert result.exit_code != 0, result.output
    assert "mutually exclusive" in result.output.lower()


def test_cli_no_cache_disables_cache_backend(cli_runner, tmp_path, network_interceptor):
    """The --no-cache flag must skip the cache and hit the network on every call."""
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--no-paging",
            "--no-cache",
            "--skip-checks", SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )
    # The validation itself may pass or fail depending on upstream checks; we
    # only require that no cache file was written (ephemeral session).
    assert "Traceback" not in result.output, result.output
    info = HttpRequester().cache_info()
    assert info["backend"] is None


def test_cli_cache_info(cli_runner, tmp_path):
    result = cli_runner.invoke(
        cli,
        ["cache", "info", "--cache-path", str(tmp_path / "cache")],
    )
    assert result.exit_code == 0, result.output
    assert "HTTP Cache" in result.output or "Entries" in result.output


def test_cli_cache_reset_noninteractive_requires_yes(cli_runner, tmp_path, network_interceptor):
    cache_path = tmp_path / "cache"
    # Populate the cache so the reset has something to do.
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=60)
    HttpRequester().get("https://example.org/ctx")
    assert HttpRequester().cache_info()["entries"] >= 1
    HttpRequester.reset()

    # Without --yes in non-interactive mode, reset must abort.
    result = cli_runner.invoke(
        cli,
        ["-y", "cache", "reset", "--cache-path", str(cache_path)],
    )
    assert result.exit_code == 1, result.output
    # Cache should still contain the entry.
    HttpRequester.reset()
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=3600)
    assert HttpRequester().cache_info()["entries"] >= 1


def test_cli_cache_reset_yes_clears_entries(cli_runner, tmp_path, network_interceptor):
    cache_path = tmp_path / "cache"
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=60)
    HttpRequester().get("https://example.org/ctx")
    HttpRequester().get("https://example.org/other")
    assert HttpRequester().cache_info()["entries"] >= 2
    HttpRequester.reset()

    result = cli_runner.invoke(
        cli,
        ["-y", "cache", "reset", "--cache-path", str(cache_path), "--yes"],
    )
    assert result.exit_code == 0, result.output

    HttpRequester.reset()
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=-1)
    assert HttpRequester().cache_info()["entries"] == 0


def test_cli_cache_warm_populates_profile_urls(cli_runner, tmp_path, network_interceptor):
    cache_path = tmp_path / "cache"
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "cache", "warm",
            "--cache-path", str(cache_path),
            "--profile-identifier", "ro-crate-1.1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert any("w3id.org" in c for c in network_interceptor["calls"]), \
        f"No expected URL fetched. Calls: {network_interceptor['calls']}"
    # The URL must now be cached for offline use.
    HttpRequester.reset()
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=3600, offline=True)
    assert HttpRequester().has_cached("https://w3id.org/ro/crate/1.1/context") is True


def test_cli_cache_warm_crate_caches_remote_archive(cli_runner, tmp_path, network_interceptor):
    cache_path = tmp_path / "cache"
    crate_url = "https://example.org/my-crate.zip"
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "cache", "warm",
            "--cache-path", str(cache_path),
            "--crate", crate_url,
        ],
    )
    assert result.exit_code == 0, result.output
    HttpRequester.reset()
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=3600, offline=True)
    assert HttpRequester().has_cached(crate_url) is True


def test_cli_validate_offline_warns_when_remote(cli_runner, tmp_path, network_interceptor):
    """In offline mode with a remote URI the validator must emit a warning."""
    # Pre-populate the cache so the remote crate resolves in offline mode.
    cache_path = tmp_path / "cache"
    HttpRequester.initialize_cache(cache_path=str(cache_path), cache_max_age=60)
    HttpRequester().get("https://example.org/fake-crate.zip")
    HttpRequester.reset()

    # We intentionally do not actually run the full validation here; the CLI
    # will fail because the cached body is not a valid ZIP, but the warning is
    # emitted before that point.
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "validate",
            "https://example.org/fake-crate.zip",
            "--no-paging",
            "--offline",
            "--cache-path", str(cache_path),
        ],
    )
    assert "offline mode is enabled" in result.output.lower() \
        or "cached version" in result.output.lower(), result.output


def test_cli_validate_offline_on_local_crate_succeeds(cli_runner, tmp_path):
    """Validating a local crate in offline mode must work without network access."""
    cache_path = tmp_path / "cache"
    result = cli_runner.invoke(
        cli,
        [
            "-y",
            "validate",
            str(ValidROC().wrroc_paper_long_date),
            "--no-paging",
            "--offline",
            "--cache-path", str(cache_path),
            "--skip-checks", SKIP_LOCAL_DATA_ENTITY_EXISTENCE_CHECK_IDENTIFIER,
        ],
    )
    # The validation may report issues for locally missing contexts; what we
    # require is that no uncaught network-related exception aborts the run.
    assert result.exit_code in (0, 1), result.output
    assert "Traceback" not in result.output


def test_auto_warm_up_skipped_when_offline(tmp_path, network_interceptor, monkeypatch):
    """Auto warm-up must not run when offline mode is active."""
    monkeypatch.setenv("ROCRATE_VALIDATOR_AUTO_WARM", "1")
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=True,
        cache_path=tmp_path / "cache",
    )
    assert network_interceptor["calls"] == []


def test_auto_warm_up_disabled_via_env(tmp_path, network_interceptor, monkeypatch):
    monkeypatch.setenv("ROCRATE_VALIDATOR_AUTO_WARM", "0")
    ValidationSettings(
        rocrate_uri=str(ValidROC().wrroc_paper_long_date),
        offline=False,
        cache_path=tmp_path / "cache",
    )
    assert network_interceptor["calls"] == []
