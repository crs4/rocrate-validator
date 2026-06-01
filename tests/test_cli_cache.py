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

"""
CLI tests for the ``rocrate-validator cache`` subcommands:

* ``cache warm`` profile-token fallback (mirrors ``validate``).
* ``cache warm -u/--url`` arbitrary URL warming.
* ``cache list`` / ``cache ls`` entry listing with filter/sort/--json.
"""

from __future__ import annotations

import io
import json

import pytest
import urllib3
from click.testing import CliRunner

from rocrate_validator.cli.main import cli
from rocrate_validator.models import Profile
from rocrate_validator.utils.http import HttpRequester


# ---------- shared fixtures ----------
@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _reset_requester():
    HttpRequester.reset()
    yield
    HttpRequester.reset()


@pytest.fixture
def mock_network(monkeypatch):
    """Route every outbound HTTP call to a fake successful response."""
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


@pytest.fixture
def tmp_cache(tmp_path):
    """Path passed via ``--cache-path`` to keep tests off the user cache."""
    return tmp_path / "cache"


def _make_profile_stub(identifier: str, version: str, token: str):
    """Lightweight stand-in for a Profile used only by token fallback tests."""

    class _Stub:
        pass

    stub = _Stub()
    stub.identifier = identifier
    stub.version = version
    stub.token = token
    return stub


# ====================================================================
# cache warm: profile-token fallback
# ====================================================================
def test_warm_token_resolves_to_single_versioned_profile(
    cli_runner,
    mock_network,
    tmp_cache,
    monkeypatch,
):
    """`-p process-run-crate` should resolve to the only versioned variant."""
    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "-p", "process-run-crate"],
    )
    assert result.exit_code == 0, result.output
    assert "process-run-crate-0.5" in result.output
    # Single-version token must resolve silently — no "Note:" line.
    assert "Note:" not in result.output
    assert "not found and skipped" not in result.output


def test_warm_token_with_multiple_versions_emits_note(
    cli_runner,
    mock_network,
    tmp_cache,
    monkeypatch,
):
    """When a token matches more than one version, the picked identifier and
    the alternatives must appear in a one-line Note."""
    candidates = [
        _make_profile_stub("fakeprof-0.1", "0.1", "fakeprof"),
        _make_profile_stub("fakeprof-0.2", "0.2", "fakeprof"),
    ]

    real_by_id = Profile.get_by_identifier
    real_by_token = Profile.get_by_token

    def fake_by_id(ident):
        if ident == "fakeprof":
            return None
        return real_by_id(ident)

    def fake_by_token(tok):
        if tok == "fakeprof":
            return candidates
        return real_by_token(tok)

    monkeypatch.setattr(Profile, "get_by_identifier", staticmethod(fake_by_id))
    monkeypatch.setattr(Profile, "get_by_token", staticmethod(fake_by_token))
    # Skip URL discovery entirely — the test cares about the resolver, not
    # what's warmed.
    monkeypatch.setattr(
        "rocrate_validator.cli.commands.cache.discover_cacheable_urls_from_profiles",
        lambda profiles: [],
    )

    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "-p", "fakeprof"],
    )
    assert result.exit_code == 0, result.output
    assert "Note:" in result.output
    assert "fakeprof-0.2" in result.output  # picked (highest version)
    assert "fakeprof-0.1" in result.output  # listed as alternative


def test_warm_unknown_profile_still_reported_as_missing(
    cli_runner,
    mock_network,
    tmp_cache,
):
    """A profile id that matches neither identifier nor token must end up
    in the existing 'Profile(s) not found and skipped' message."""
    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "-p", "definitely-not-a-profile"],
    )
    assert result.exit_code == 0, result.output
    assert "not found and skipped" in result.output
    assert "definitely-not-a-profile" in result.output


# ====================================================================
# cache warm: -u / --url
# ====================================================================
def test_warm_url_alone_does_not_fall_back_to_all_profiles(
    cli_runner,
    mock_network,
    tmp_cache,
    monkeypatch,
):
    """``cache warm -u <url>`` with no -p must warm only the URL — not every
    installed profile (which is the default when no explicit source is
    given)."""
    seen = {"profile_calls": 0}

    def fake_discover(profiles):
        seen["profile_calls"] += 1
        return []

    monkeypatch.setattr(
        "rocrate_validator.cli.commands.cache.discover_cacheable_urls_from_profiles",
        fake_discover,
    )
    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "-u", "https://example.org/a"],
    )
    assert result.exit_code == 0, result.output
    assert seen["profile_calls"] == 0
    assert "Fetching explicit URLs" in result.output
    assert "https://example.org/a" in result.output


def test_warm_url_invalid_value_is_rejected(cli_runner, tmp_cache):
    """Non-http(s) values must trip Click's parameter validation and exit 2."""
    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "-u", "notaurl"],
    )
    assert result.exit_code == 2
    assert "http(s)" in result.output
    assert "notaurl" in result.output


def test_warm_url_combined_with_profile_warms_both(
    cli_runner,
    mock_network,
    tmp_cache,
    monkeypatch,
):
    """``-p <profile> -u <url>`` must warm the profile URLs *and* the extra
    URL in the same invocation."""
    # Make the profile contribute a single deterministic URL.
    monkeypatch.setattr(
        "rocrate_validator.cli.commands.cache.discover_cacheable_urls_from_profiles",
        lambda profiles: ["https://example.org/from-profile"],
    )
    result = cli_runner.invoke(
        cli,
        [
            "cache",
            "warm",
            "--cache-path",
            str(tmp_cache),
            "-p",
            "ro-crate-1.1",
            "-u",
            "https://example.org/explicit",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Warming cache for profiles" in result.output
    assert "Fetching explicit URLs" in result.output
    assert "https://example.org/from-profile" in result.output
    assert "https://example.org/explicit" in result.output


# ====================================================================
# cache warm: --crate (remote RO-Crate)
# ====================================================================
@pytest.fixture
def mock_network_gzip(monkeypatch):
    """
    Same as ``mock_network``, but returns a ``Content-Encoding: gzip`` body.
    This encoded response is required to reproduce the warm-crate bug.
    """
    import gzip

    from requests.adapters import HTTPAdapter

    body = gzip.compress(b'{"@context": "https://w3id.org/ro/crate/1.2/context"}')

    def fake_send(self, request, **kwargs):
        raw = urllib3.HTTPResponse(
            body=io.BytesIO(body),
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(body)),
            },
            status=200,
            preload_content=False,
            decode_content=False,
        )
        return self.build_response(request, raw)

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)


def test_warm_crate_caches_remote_metadata(cli_runner, mock_network_gzip, tmp_cache):
    """
    Regression: ``cache warm --crate <url>`` must consume the body via
    ``response.content`` rather than streaming ``response.raw``.

    With ``stream=True`` + ``shutil.copyfileobj(response.raw, ...)`` the warm-up
    crashed with urllib3's "Calling read(decode_content=False) is not supported
    after read(decode_content=True) was called": requests_cache buffers the
    streamed body (decode_content=True) to store it, after which a raw read
    (decode_content=False) is rejected. The body must therefore be touched in a
    way that goes through the already-decoded content.
    """
    url = "https://example.org/ro-crate/ro-crate-metadata.json"
    result = cli_runner.invoke(
        cli,
        ["cache", "warm", "--cache-path", str(tmp_cache), "--crate", url],
    )
    assert result.exit_code == 0, result.output
    assert "Fetching remote RO-Crates" in result.output
    assert "Summary: 1 cached, 0 failed, 0 skipped" in result.output

    # The fetched crate must actually be retrievable from the cache afterwards.
    listed = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache)],
    )
    assert listed.exit_code == 0, listed.output
    assert "ro-crate-metadata.json" in listed.output


# ====================================================================
# cache list / ls
# ====================================================================
def _warm_some(cli_runner, tmp_cache, urls):
    args = ["cache", "warm", "--cache-path", str(tmp_cache)]
    for u in urls:
        args += ["-u", u]
    return cli_runner.invoke(cli, args)


def test_list_reports_empty_cache(cli_runner, tmp_cache):
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache)],
    )
    assert result.exit_code == 0, result.output
    assert "Cache is empty" in result.output


def test_list_shows_warmed_entries(cli_runner, mock_network, tmp_cache):
    urls = [
        "https://example.org/alpha",
        "https://example.org/beta",
        "https://example.org/gamma",
    ]
    warm = _warm_some(cli_runner, tmp_cache, urls)
    assert warm.exit_code == 0, warm.output

    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache)],
    )
    assert result.exit_code == 0, result.output
    for u in urls:
        # URLs are wrapped/folded in the Rich table, so check a stable token.
        assert u.rsplit("/", 1)[1] in result.output
    assert "Total:" in result.output


def test_list_url_filter_narrows_results(cli_runner, mock_network, tmp_cache):
    urls = [
        "https://example.org/keep-me",
        "https://example.org/other",
    ]
    _warm_some(cli_runner, tmp_cache, urls)
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--url", "keep-me"],
    )
    assert result.exit_code == 0, result.output
    assert "keep-me" in result.output
    # The filter is case-insensitive substring on URL; "other" must be absent.
    assert "/other" not in result.output


def test_list_filter_with_no_match_message(cli_runner, mock_network, tmp_cache):
    _warm_some(cli_runner, tmp_cache, ["https://example.org/only"])
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--url", "no-such-fragment"],
    )
    assert result.exit_code == 0, result.output
    assert "No entries match" in result.output


def test_list_json_output_is_well_formed(cli_runner, mock_network, tmp_cache):
    urls = [
        "https://example.org/a",
        "https://example.org/b",
    ]
    _warm_some(cli_runner, tmp_cache, urls)
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert {e["url"] for e in payload} == set(urls)
    sample = payload[0]
    # Every entry must carry the documented fields.
    assert {"url", "status", "size_bytes", "content_type", "created_at", "expires", "is_expired"} <= set(sample)
    assert isinstance(sample["size_bytes"], int)


def test_list_sort_by_url_asc_then_desc(cli_runner, mock_network, tmp_cache):
    """`--sort url` defaults to asc; `--order desc` must reverse it."""
    _warm_some(
        cli_runner,
        tmp_cache,
        [
            "https://example.org/c",
            "https://example.org/a",
            "https://example.org/b",
        ],
    )

    asc = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--sort", "url", "--json"],
    )
    assert asc.exit_code == 0, asc.output
    asc_urls = [e["url"] for e in json.loads(asc.output)]
    assert asc_urls == sorted(asc_urls)

    desc = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--sort", "url", "--order", "desc", "--json"],
    )
    assert desc.exit_code == 0, desc.output
    desc_urls = [e["url"] for e in json.loads(desc.output)]
    assert desc_urls == sorted(desc_urls, reverse=True)


def test_list_default_sort_is_created_desc(cli_runner, mock_network, tmp_cache):
    """No --sort flag: entries come back ordered by created_at, most recent
    first (the documented default)."""
    _warm_some(
        cli_runner,
        tmp_cache,
        [
            "https://example.org/first",
            "https://example.org/second",
            "https://example.org/third",
        ],
    )
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--json"],
    )
    assert result.exit_code == 0, result.output
    created = [e["created_at"] for e in json.loads(result.output)]
    # Each entry has a timestamp (mocked response goes through requests_cache);
    # the sequence must be monotonically non-increasing.
    assert all(a >= b for a, b in zip(created, created[1:]))


def test_list_invalid_order_is_rejected(cli_runner, tmp_cache):
    result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--order", "sideways"],
    )
    assert result.exit_code == 2
    assert "'sideways'" in result.output


def test_ls_alias_runs_the_same_command(cli_runner, mock_network, tmp_cache):
    _warm_some(cli_runner, tmp_cache, ["https://example.org/x"])
    list_result = cli_runner.invoke(
        cli,
        ["cache", "list", "--cache-path", str(tmp_cache), "--json"],
    )
    ls_result = cli_runner.invoke(
        cli,
        ["cache", "ls", "--cache-path", str(tmp_cache), "--json"],
    )
    assert list_result.exit_code == ls_result.exit_code == 0
    assert json.loads(list_result.output) == json.loads(ls_result.output)
