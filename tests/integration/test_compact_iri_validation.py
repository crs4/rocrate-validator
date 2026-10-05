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

"""Exercise compact IRIs through the public validator and profile overlays."""

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

from rocrate_validator import models, services
from rocrate_validator.utils.http import HttpRequester

COMPACTION_CHECK = "Validation of the compaction format of the file descriptor"


@pytest.mark.parametrize("version", ["1.1", "1.2", "1.3"])
@pytest.mark.parametrize("property_name", ["ex:property", "property", "unknown"])
def test_compact_property_validation(version, property_name, tmp_path, monkeypatch):
    context = {
        "Dataset": "http://schema.org/Dataset",
        "CreativeWork": "http://schema.org/CreativeWork",
        "name": "http://schema.org/name",
        "description": "http://schema.org/description",
        "datePublished": "http://schema.org/datePublished",
        "license": "http://schema.org/license",
        "about": "http://schema.org/about",
        "conformsTo": "http://purl.org/dc/terms/conformsTo",
    }
    response = Mock(status_code=200, headers={"Content-Type": "application/ld+json"})
    response.json.side_effect = lambda: {"@context": deepcopy(context)}
    monkeypatch.setattr(HttpRequester(), "get", Mock(return_value=response))
    metadata = {
        "@context": [
            f"https://w3id.org/ro/crate/{version}/context",
            {
                "ex": "https://example.org/",
                "property": "https://example.org/property",
            },
        ],
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": f"https://w3id.org/ro/crate/{version}"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "Prefix regression",
                "description": "Test crate",
                "datePublished": "2026-10-01",
                "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                property_name: "value",
            },
        ],
    }
    (tmp_path / "ro-crate-metadata.json").write_text(json.dumps(metadata))
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=str(tmp_path),
            profile_identifier=f"ro-crate-{version}",
            requirement_severity=models.Severity.REQUIRED,
        )
    )
    checks = [check for check in result.executed_checks if check.name == COMPACTION_CHECK]
    assert len(checks) == 1
    source_version = "1.2" if version == "1.3" else version
    assert checks[0].requirement.profile.identifier == f"ro-crate-{source_version}"
    accepted = property_name != "unknown"
    assert result.get_executed_check_result(checks[0]) is accepted
    issues = [issue for issue in result.get_issues() if issue.check.name == COMPACTION_CHECK]
    assert len(issues) == (0 if accepted else 1)
    if issues:
        assert issues[0].profile_identifier == f"ro-crate-{version}"
        assert issues[0].source_profile_identifier == f"ro-crate-{source_version}"
    assert result.passed() is accepted, [issue.message for issue in result.get_issues()]
