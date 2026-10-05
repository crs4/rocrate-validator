"""Absolute file URIs identify resources independently of payload membership."""

import json
from pathlib import Path

import pytest

from rocrate_validator import models
from tests.shared import do_entity_test


@pytest.mark.parametrize("version", ["1.2", "1.3"])
@pytest.mark.parametrize("form", ["file://", "file:", "file://localhost", "FILE://LOCALHOST"])
@pytest.mark.parametrize("location", ["external-missing", "external-present", "payload"])
def test_file_uri_payload_membership(tmp_path, version, form, location):
    crate = tmp_path / "crate"
    crate.mkdir()
    # A sibling sharing the textual prefix must not count as payload.
    external = tmp_path / "crate-external"
    external.mkdir()
    target = (crate if location == "payload" else external) / "a file.txt"
    if location != "external-missing":
        target.write_text("data")
    entity_id = form + target.as_posix().replace(" ", "%20")
    _validate(crate, version, entity_id, location != "payload")


@pytest.mark.parametrize("version", ["1.2", "1.3"])
@pytest.mark.parametrize(
    "entity_id",
    [
        "file:///nonexistent/data.txt",
        "file:/nonexistent/data.txt",
        "file://localhost/nonexistent/data.txt",
        "file://example.org/data.txt",
    ],
)
def test_detached_file_uri(tmp_path, version, entity_id):
    _validate(tmp_path, version, entity_id, True, detached=True)


@pytest.mark.parametrize("version", ["1.2", "1.3"])
@pytest.mark.parametrize("entity_id", ["missing.txt", "/missing.txt", "file:///a file.txt"])
def test_invalid_data_entity_references(tmp_path, version, entity_id):
    _validate(tmp_path, version, entity_id, False)


@pytest.mark.parametrize("version", ["1.2", "1.3"])
@pytest.mark.parametrize(
    "entity_id, issue",
    [
        ("file:relative.txt", "file URI path MUST be absolute"),
        ("file://localhost", "file URI path MUST be absolute"),
        ("file://example.org", "file URI path MUST be absolute"),
        ("C:/data/x", "Windows drive path"),
        ("//example.org/data.txt", "network-path reference"),
    ],
)
@pytest.mark.parametrize("detached", [False, True])
def test_identifier_path_syntax(tmp_path, version, entity_id, issue, detached):
    _validate(tmp_path, version, entity_id, False, detached=detached, expected_issue=issue)


def _validate(crate, version, entity_id, valid, detached=False, expected_issue=None):
    source = Path(
        f"tests/data/crates/rocrate-{version}/8_metadata_dataEntities/local_entity_reference/valid/ro-crate-metadata.json"
    )
    metadata = json.loads(source.read_text())
    graph = metadata["@graph"]
    root = next(e for e in graph if e["@id"] == "./")
    files = [e for e in graph if e.get("@type") == "File"]
    graph[:] = [e for e in graph if e not in files]
    root["hasPart"] = [{"@id": entity_id}]
    graph.append({"@id": entity_id, "@type": "File", "name": "Test file"})
    if detached:
        root["@id"] = "https://example.org/crate/"
        graph[0]["about"] = {"@id": root["@id"]}
    descriptor = crate / "ro-crate-metadata.json"
    descriptor.write_text(json.dumps(metadata))
    do_entity_test(
        descriptor if detached else crate,
        models.Severity.REQUIRED,
        valid,
        expected_triggered_issues=(
            [expected_issue]
            if expected_issue
            else []
            if valid
            else [
                "does not include the Data Entity"
                if entity_id == "missing.txt"
                else "invalid @id"
                if " " in entity_id
                else "MUST use a relative @id within the RO-Crate root"
            ]
        ),
        profile_identifier=f"ro-crate-{version}",
        skip_availability_check=True,
    )
