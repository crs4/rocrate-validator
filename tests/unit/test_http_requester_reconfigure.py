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

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rocrate_validator.utils.http import HttpRequester


@pytest.fixture(autouse=True)
def _reset_singleton():
    HttpRequester.reset()
    yield
    HttpRequester.reset()


def _initialize(cache_path, offline=False, cache_max_age=-1):
    return HttpRequester.initialize_cache(
        cache_path=str(cache_path),
        cache_max_age=cache_max_age,
        offline=offline,
    )


def _fake_session(status_code=200):
    """A session-like mock whose ``get`` returns a sentinel response."""
    session = MagicMock()
    response = MagicMock(status_code=status_code, from_cache=False)
    session.get.return_value = response
    return session, response


def test_initialize_cache_creates_instance_when_absent(tmp_path):
    assert HttpRequester._instance is None
    requester = _initialize(tmp_path / "cache")
    assert isinstance(requester, HttpRequester)
    assert HttpRequester._instance is requester


def test_initialize_cache_reuses_existing_instance(tmp_path):
    first = _initialize(tmp_path / "cache-1")
    second = _initialize(tmp_path / "cache-2")
    # The singleton is reconfigured in place rather than recreated.
    assert second is first


def test_reconfigure_applies_new_settings(tmp_path):
    requester = _initialize(tmp_path / "cache", offline=False, cache_max_age=60)
    assert requester.offline is False

    same = _initialize(tmp_path / "cache", offline=True, cache_max_age=-1)
    assert same is requester
    assert same.offline is True
    # Offline mode is enforced on the freshly rebuilt session.
    assert getattr(same.session.settings, "only_if_cached", False) is True


def test_reconfigure_rebuilds_underlying_session(tmp_path):
    requester = _initialize(tmp_path / "cache-1", cache_max_age=60)
    old_session = requester.session
    _initialize(tmp_path / "cache-2", cache_max_age=60)
    assert requester.session is not old_session


def test_reconfigure_preserves_instance_attributes(tmp_path):
    """Regression: reconfiguring the cache must not discard state set on the
    singleton (e.g. methods patched by tests)."""
    requester = _initialize(tmp_path / "cache-1", cache_max_age=60)
    sentinel = object()
    requester.custom_marker = sentinel  # pyright: ignore[reportAttributeAccessIssue]

    _initialize(tmp_path / "cache-2", cache_max_age=60)

    assert requester.custom_marker is sentinel


def test_method_wrapper_targets_current_session(tmp_path):
    """The ``__getattr__`` HTTP wrappers resolve the session at call time, so a
    wrapper obtained before a session swap still hits the live session."""
    requester = _initialize(tmp_path / "cache", cache_max_age=60)

    first_session, _ = _fake_session()
    requester.session = first_session
    wrapper = requester.get  # captured before swapping the session

    second_session, expected = _fake_session(status_code=201)
    requester.session = second_session

    result = wrapper("https://example.org/x")

    assert result is expected
    second_session.get.assert_called_once()
    first_session.get.assert_not_called()


def test_pinned_wrapper_survives_reconfigure(tmp_path):
    """Mimics how ``pytest.monkeypatch`` teardown leaves a method wrapper pinned
    as an instance attribute: after a reconfigure rebuilds the session, that
    wrapper must still target the live session, not a closed one."""
    requester = _initialize(tmp_path / "cache-1", cache_max_age=60)
    # pin the wrapper as an instance attribute
    requester.get = requester.get  # pyright: ignore[reportAttributeAccessIssue]  # pylint: disable=no-member

    _initialize(tmp_path / "cache-2", cache_max_age=60)  # rebuilds the session

    mock_session, expected = _fake_session()
    requester.session = mock_session

    result = requester.get("https://example.org/x")

    assert result is expected
    mock_session.get.assert_called_once()


def test_reset_drops_instance(tmp_path):
    requester = _initialize(tmp_path / "cache", cache_max_age=60)
    HttpRequester.reset()
    assert HttpRequester._instance is None
    # A subsequent initialization yields a brand-new instance.
    assert _initialize(tmp_path / "cache", cache_max_age=60) is not requester


def test_validation_settings_preserves_singleton(tmp_path):
    """Constructing ``ValidationSettings`` reconfigures the cache in place and
    must not drop the existing requester (nor any state held on it)."""
    from rocrate_validator.models import ValidationSettings
    from rocrate_validator.utils.uri import URI

    requester = _initialize(tmp_path / "cache", cache_max_age=60)
    marker = object()
    requester.custom_marker = marker  # pyright: ignore[reportAttributeAccessIssue]

    # ``offline=True`` keeps the construction self-contained (no warm-up/network).
    ValidationSettings(
        rocrate_uri=URI("."),
        offline=True,
        cache_path=tmp_path / "cache",
    )

    assert HttpRequester._instance is requester
    assert requester.custom_marker is marker
