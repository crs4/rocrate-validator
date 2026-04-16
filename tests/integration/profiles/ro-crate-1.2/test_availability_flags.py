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

import logging

from rocrate_validator import models, services
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.uri import URI
from tests.ro_crates import ValidROCrate12

logger = logging.getLogger(__name__)


valid = ValidROCrate12()

# Minimal set of JSON-LD context keys needed to pass `check_compaction`
# for the test crates used in this module.
_FAKE_CONTEXT_KEYS = {
    "about", "affiliation", "author", "cite-as", "conformsTo", "funder",
    "contentLocation", "contentSize", "contentUrl", "dateCreated",
    "dateModified", "datePublished", "description", "encodingFormat",
    "hasPart", "license", "name", "publisher", "sdDatePublished", "url",
}


class _FakeContextResponse:
    """Minimal HTTP response that satisfies `FileDescriptorJsonLdFormat` checks."""
    status_code = 200
    headers = {"Content-Type": "application/ld+json"}

    def json(self):
        return {"@context": {k: f"http://schema.org/{k}" for k in _FAKE_CONTEXT_KEYS}}


def _fake_context_get(url, *args, **kwargs):
    """Return a fake JSON-LD context for w3id.org; reject anything else."""
    if "w3id.org" in url:
        return _FakeContextResponse()
    raise RuntimeError(f"Unexpected GET request in test: {url}")


def _validate_with_settings(**kwargs):
    return services.validate(
        models.ValidationSettings(
            rocrate_uri=URI(valid.attached_absolute_root),
            profile_identifier="ro-crate-1.2",
            requirement_severity=models.Severity.RECOMMENDED,
            **kwargs,
        )
    )


def _availability_messages(result):
    return [
        issue.message
        for issue in result.get_issues(models.Severity.RECOMMENDED)
        if "Web-based Data Entity" in issue.message
    ]


def _patch_unavailable(monkeypatch):
    """Make every HEAD request fail (simulates unreachable web entities)
    and return a fake JSON-LD context for GET requests to avoid proxy errors."""
    def fake_head(url, *args, **kwargs):
        raise RuntimeError("Not downloadable")

    monkeypatch.setattr(HttpRequester(), "head", fake_head)
    monkeypatch.setattr(HttpRequester(), "get", _fake_context_get)


def test_default_availability_warns(monkeypatch):
    _patch_unavailable(monkeypatch)
    result = _validate_with_settings()
    # REQUIRED checks must pass; the unavailable entity only raises a RECOMMENDED warning
    assert result.passed(models.Severity.REQUIRED)
    messages = _availability_messages(result)
    assert messages, "Expected availability warnings for web-based data entities"


def test_creation_time_enforces_availability(monkeypatch):
    _patch_unavailable(monkeypatch)
    result = _validate_with_settings(creation_time=True)
    assert not result.passed()
    messages = _availability_messages(result)
    assert messages, "Expected availability violations at creation time"


def test_enforce_availability_flag(monkeypatch):
    _patch_unavailable(monkeypatch)
    result = _validate_with_settings(enforce_availability=True)
    assert not result.passed()
    messages = _availability_messages(result)
    assert messages, "Expected availability violations when enforced"


def test_skip_availability_check(monkeypatch):
    monkeypatch.setattr(HttpRequester(), "get", _fake_context_get)
    result = _validate_with_settings(skip_availability_check=True)
    assert result.passed()
    messages = _availability_messages(result)
    assert not messages, "Availability warnings should be skipped"


def test_content_size_warning(monkeypatch):
    class FakeResponse:
        def __init__(self, status_code=200, content_length="10"):
            self.status_code = status_code
            self.headers = {"Content-Length": content_length}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("HTTP error")

    def fake_head(url, *args, **kwargs):
        if url.endswith("/file.txt"):
            return FakeResponse(content_length="10")
        if url.endswith("/content.txt"):
            raise RuntimeError("Not downloadable")
        return FakeResponse(content_length="10")

    monkeypatch.setattr(HttpRequester(), "head", fake_head)
    monkeypatch.setattr(HttpRequester(), "get", _fake_context_get)

    metadata_dict = {
        "@context": "https://w3id.org/ro/crate/1.2/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
                "about": {"@id": "./"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "Availability test",
                "description": "Content size and contentUrl warnings.",
                "license": {"@id": "http://spdx.org/licenses/CC0-1.0"},
                "datePublished": "2024-01-01",
                "hasPart": [{"@id": "https://example.org/file.txt"}],
            },
            {
                "@id": "https://example.org/file.txt",
                "@type": "File",
                "name": "file.txt",
                "description": "Remote file.",
                "encodingFormat": "text/plain",
                "contentSize": "5",
                "contentUrl": "https://example.org/content.txt",
            },
        ],
    }

    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=URI("."),
            metadata_dict=metadata_dict,
            metadata_only=True,
            profile_identifier="ro-crate-1.2",
            requirement_severity=models.Severity.RECOMMENDED,
        )
    )

    messages = [issue.message for issue in result.get_issues(models.Severity.RECOMMENDED) if issue.message]
    assert any("contentSize" in message for message in messages)
    assert any("contentUrl" in message for message in messages)
