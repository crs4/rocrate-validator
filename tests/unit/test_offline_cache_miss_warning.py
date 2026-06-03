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

from rocrate_validator import models as models_module
from rocrate_validator.models import ValidationContext
from rocrate_validator.utils.http import OfflineCacheMissError, find_offline_cache_miss


# ---------- find_offline_cache_miss ----------
def test_find_offline_cache_miss_direct():
    exc = OfflineCacheMissError("https://example.org/x")
    assert find_offline_cache_miss(exc) is exc


def test_find_offline_cache_miss_walks_cause_chain():
    inner = OfflineCacheMissError("https://example.org/x")
    try:
        try:
            raise inner
        except OfflineCacheMissError as e:
            raise RuntimeError("wrapped") from e
    except Exception as outer:
        found = find_offline_cache_miss(outer)
    assert found is inner


def test_find_offline_cache_miss_walks_context_chain():
    # `raise` inside `except` without `from` populates __context__.
    try:
        try:
            raise OfflineCacheMissError("https://example.org/y")
        except OfflineCacheMissError:
            raise RuntimeError("wrapped via context")  # noqa: B904
    except Exception as outer:
        found = find_offline_cache_miss(outer)
    assert isinstance(found, OfflineCacheMissError)
    assert found.url == "https://example.org/y"


def test_find_offline_cache_miss_returns_none_for_unrelated():
    assert find_offline_cache_miss(ValueError("nope")) is None


def test_find_offline_cache_miss_handles_cyclic_chain():
    # Two exceptions referencing each other must not loop forever.
    a = RuntimeError("a")
    b = RuntimeError("b")
    a.__context__ = b
    b.__context__ = a
    assert find_offline_cache_miss(a) is None


# ---------- ValidationContext.maybe_warn_offline_cache_miss ----------
@pytest.fixture
def bare_context():
    """A ValidationContext with only the state needed by the dedup helper."""
    ctx = ValidationContext.__new__(ValidationContext)
    ctx._offline_cache_misses_warned = set()
    return ctx


@pytest.fixture
def mock_logger(monkeypatch):
    """
    Replace the module-level logger in ``rocrate_validator.models`` with a
    MagicMock. The project's custom logger sets ``propagate=False``, so
    pytest's ``caplog`` does not see its records — observing the mock is
    both simpler and more precise.
    """
    fake = MagicMock()
    monkeypatch.setattr(models_module, "logger", fake)
    return fake


def test_maybe_warn_returns_false_for_unrelated_exception(bare_context, mock_logger):
    assert bare_context.maybe_warn_offline_cache_miss(ValueError("nope")) is False
    mock_logger.warning.assert_not_called()


def test_maybe_warn_emits_once_per_url(bare_context, mock_logger):
    url = "https://example.org/ctx"
    for _ in range(3):
        assert bare_context.maybe_warn_offline_cache_miss(OfflineCacheMissError(url)) is True
    assert mock_logger.warning.call_count == 1
    # The bare miss exception is logged via "%s" so it stringifies and the
    # URL appears verbatim in the formatted message.
    args, _ = mock_logger.warning.call_args
    assert url in str(args[1])


def test_maybe_warn_emits_once_per_distinct_url(bare_context, mock_logger):
    url_a = "https://example.org/a"
    url_b = "https://example.org/b"
    bare_context.maybe_warn_offline_cache_miss(OfflineCacheMissError(url_a))
    bare_context.maybe_warn_offline_cache_miss(OfflineCacheMissError(url_b))
    bare_context.maybe_warn_offline_cache_miss(OfflineCacheMissError(url_a))
    assert mock_logger.warning.call_count == 2
    logged = " ".join(str(call.args[1]) for call in mock_logger.warning.call_args_list)
    assert url_a in logged
    assert url_b in logged


def test_maybe_warn_dedups_when_miss_is_wrapped(bare_context, mock_logger):
    url = "https://example.org/ctx"
    try:
        raise RuntimeError("wrapped") from OfflineCacheMissError(url)
    except RuntimeError as wrapped_exc:
        wrapped = wrapped_exc
    # First call: direct miss; warning emitted.
    assert bare_context.maybe_warn_offline_cache_miss(OfflineCacheMissError(url)) is True
    # Second call: same URL but reached via a wrapper exception. Must still
    # be recognized through the __cause__ chain and dedup'd against the first.
    assert bare_context.maybe_warn_offline_cache_miss(wrapped) is True
    assert mock_logger.warning.call_count == 1
