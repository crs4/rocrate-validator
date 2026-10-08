"""Packaging mode is selected from the source, independently of graph contents."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from rocrate_validator.events import Event, EventType
from rocrate_validator.models import ValidationSettings
from rocrate_validator.rocrate import ROCrate
from rocrate_validator.rocrate.package_type import PackageType
from rocrate_validator.services import __initialise_validator__, validate
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.io_helpers.output.console import Console
from rocrate_validator.utils.io_helpers.output.json.formatters import format_validation_results
from rocrate_validator.utils.io_helpers.output.text.formatters import ValidationResultTextOutputFormatter
from rocrate_validator.utils.io_helpers.output.text.layout.report import ValidationReportLayout
from rocrate_validator.utils.uri import URI


@pytest.mark.parametrize("root_id", ["./", "https://example.org/crate", "urn:example:crate"])
def test_directory_mode_does_not_depend_on_root_id_or_payload(tmp_path: Path, root_id: str):
    descriptor = tmp_path / "ro-crate-metadata.json"
    descriptor.write_text(json.dumps({"@graph": [{"@id": root_id, "@type": "Dataset"}]}))
    crate = ROCrate.new_instance(tmp_path)
    assert crate.package_type is PackageType.ATTACHED
    assert crate.is_attached() and not crate.is_detached()
    descriptor.write_text("not JSON")
    assert ROCrate.new_instance(tmp_path).package_type is PackageType.ATTACHED


def test_missing_payload_does_not_change_attached_mode(tmp_path: Path):
    (tmp_path / "ro-crate-metadata.json").write_text("{}")
    crate = ROCrate.new_instance(tmp_path)
    assert crate.package_type is PackageType.ATTACHED
    (tmp_path / "payload.txt").write_text("data")
    assert ROCrate.new_instance(tmp_path).package_type is PackageType.ATTACHED


@pytest.mark.parametrize("root_id", ["./", "https://example.org/crate"])
def test_standalone_document_is_detached_even_with_dot_root(tmp_path: Path, root_id: str):
    descriptor = tmp_path / "crate-ro-crate-metadata.json"
    descriptor.write_text(json.dumps({"@graph": [{"@id": root_id, "@type": "Dataset"}]}))
    crate = ROCrate.new_instance(descriptor)
    assert crate.package_type is PackageType.DETACHED
    assert crate.is_detached() and not crate.is_attached()


def test_zip_and_explicit_mode_constraints(tmp_path: Path):
    archive = tmp_path / "crate.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("ro-crate-metadata.json", "{}")
    assert ROCrate.new_instance(archive).package_type is PackageType.ATTACHED
    with pytest.raises(ValueError, match="standalone metadata document"):
        ROCrate.new_instance(archive, packaging_mode="detached")
    with pytest.raises(ValueError, match="standalone metadata document"):
        ROCrate.new_instance(tmp_path, packaging_mode="detached")
    assert ROCrate.new_instance(archive, relative_root_path=Path("nested")).attached_descriptor_id == (
        "nested/ro-crate-metadata.json"
    )


def test_bagit_package_type_and_effective_descriptor(tmp_path: Path):
    (tmp_path / "bagit.txt").write_text("BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "ro-crate-metadata.json").write_text("{}")
    crate = ROCrate.new_instance(tmp_path)
    assert crate.package_type is PackageType.ATTACHED
    assert crate.attached_descriptor_id == "data/ro-crate-metadata.json"


def test_extracted_zip_keeps_attached_mode_and_source_alive(tmp_path: Path):
    archive = tmp_path / "crate.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("ro-crate-metadata.json", json.dumps(_minimal_metadata()))
    settings = ValidationSettings(
        rocrate_uri=archive,
        profile_identifier="ro-crate-1.2",
        requirement_severity="REQUIRED",
        offline=True,
        disable_remote_crate_download=False,
    )
    validator = __initialise_validator__(settings)
    result = validator.validate()
    assert result.context.ro_crate.package_type is PackageType.ATTACHED
    assert result.context.ro_crate.has_descriptor()
    assert result.context.ro_crate.metadata.as_dict() == _minimal_metadata()
    assert result.validation_settings.to_dict()["rocrate_uri"] == str(archive)
    assert settings.rocrate_uri.as_path() == archive


def test_downloaded_zip_preserves_attached_mode_and_remote_source(monkeypatch, tmp_path: Path):
    archive = tmp_path / "crate.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("ro-crate-metadata.json", json.dumps(_minimal_metadata()))

    class Response:
        status_code = 200

        def __init__(self):
            self.raw = io.BytesIO(archive.read_bytes())

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.raw.close()

    remote_uri = "https://example.org/crate.zip"
    settings = ValidationSettings(
        rocrate_uri=remote_uri,
        profile_identifier="ro-crate-1.2",
        requirement_severity="REQUIRED",
        packaging_mode="attached",
        disable_remote_crate_download=False,
        offline=True,
    )
    monkeypatch.setattr(URI, "is_available", lambda self: True)
    monkeypatch.setattr(HttpRequester().session, "get", lambda *_args, **_kwargs: Response())
    result = __initialise_validator__(settings).validate()
    assert result.context.ro_crate.package_type is PackageType.ATTACHED
    assert result.context.ro_crate.packaging_mode_explicit
    assert result.validation_settings.to_dict()["rocrate_uri"] == remote_uri
    assert result.context.ro_crate.has_descriptor()


def test_explicit_attached_canonical_document_uses_parent(tmp_path: Path):
    descriptor = tmp_path / "ro-crate-metadata.json"
    descriptor.write_text("{}")
    crate = ROCrate.new_instance(descriptor, packaging_mode="attached")
    assert crate.package_type is PackageType.ATTACHED
    assert crate.packaging_mode_explicit
    assert crate.uri.as_path() == tmp_path


def test_in_memory_source_has_no_implicit_directory(monkeypatch, tmp_path: Path):
    metadata = {"@graph": [{"@id": "./", "@type": "Dataset"}]}
    first = ROCrate.from_metadata_dict(metadata)
    monkeypatch.chdir(tmp_path)
    second = ROCrate.from_metadata_dict(metadata)
    assert first.package_type is second.package_type is PackageType.UNSPECIFIED
    assert not first.is_attached() and not first.is_detached()
    assert str(first.uri) == str(second.uri)
    assert not first.has_file(Path("payload.txt"))
    assert ROCrate.from_metadata_dict(metadata, "detached").is_detached()
    assert ROCrate.from_metadata_dict(metadata, "attached").is_attached()
    assert ROCrate.from_metadata_dict({}).metadata.as_json() == "{}"


def test_settings_and_service_reject_invalid_context(tmp_path: Path):
    with pytest.raises(ValueError, match="packaging_mode"):
        ValidationSettings(rocrate_uri=tmp_path, packaging_mode="unknown", offline=True)
    settings = ValidationSettings(
        rocrate_uri=tmp_path, metadata_dict={"@graph": []}, packaging_mode="attached", offline=True
    )
    with pytest.raises(ValueError, match="metadata_only"):
        __initialise_validator__(settings)
    with pytest.raises(ValueError, match="remote standalone"):
        ROCrate.new_instance("https://example.org/ro-crate-metadata.json", packaging_mode="attached")
    in_memory = __initialise_validator__({"metadata_dict": {}, "offline": True})
    assert in_memory.validation_settings.metadata_only is True


def _minimal_metadata(*, root_id: str = "./", file_id: str | None = None) -> dict:
    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": root_id},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
        },
        {
            "@id": root_id,
            "@type": "Dataset",
            "name": "Test crate",
            "description": "A minimal test crate",
            "datePublished": "2026-01-01",
            "license": {"@id": "https://spdx.org/licenses/CC0-1.0"},
        },
    ]
    if file_id is not None:
        graph.append({"@id": file_id, "@type": "File", "name": "Test file"})
    return {"@context": {"@vocab": "http://schema.org/"}, "@graph": graph}


def _validate_metadata(metadata: dict, mode: str):
    return validate(
        {
            "metadata_dict": metadata,
            "metadata_only": True,
            "packaging_mode": mode,
            "offline": True,
            "requirement_severity": "REQUIRED",
            "profile_identifier": "ro-crate-1.2",
        }
    )


def test_metadata_mode_controls_detached_rule_and_reports_scope(monkeypatch, tmp_path: Path):
    metadata = _minimal_metadata(file_id="missing.txt")
    first = _validate_metadata(metadata, "auto")
    (tmp_path / "missing.txt").write_text("irrelevant")
    monkeypatch.chdir(tmp_path)
    second = _validate_metadata(metadata, "auto")
    assert first.passed() and second.passed()
    assert first.skipped_checks_count == second.skipped_checks_count
    assert any("package context is unavailable" in detail.message for detail in first.skipped_check_details)
    assert first.context.publicID == second.context.publicID
    assert first.to_dict()["validation_settings"]["package_type"] == "unspecified"
    assert first.to_dict()["validation_settings"]["packaging_mode"] == "auto"
    assert first.to_dict()["validation_settings"]["metadata_only"] is True

    attached = _validate_metadata(metadata, "attached")
    detached = _validate_metadata(metadata, "detached")
    assert attached.passed()
    assert not detached.passed()
    assert any("not web-based" in issue.message for issue in detached.issues)
    assert detached.to_dict()["validation_settings"]["packaging_mode_explicit"] is True


def test_detached_contextual_file_is_not_treated_as_payload():
    metadata = _minimal_metadata(file_id="#contextual-file")
    result = _validate_metadata(metadata, "detached")
    assert not any("not web-based" in issue.message for issue in result.issues)


@pytest.mark.parametrize("mode,expected", [("auto", "Unspecified"), ("attached", "Attached"), ("detached", "Detached")])
def test_reports_show_package_type_after_target_profile(mode: str, expected: str):
    result = _validate_metadata(_minimal_metadata(), mode)
    console = Console(record=True, width=120)
    layout = ValidationReportLayout(console, result.validation_settings)
    _ = layout.layout
    assert layout.base_info_layout is not None

    layout.subscribers[0].update(Event(EventType.VALIDATION_START), result.context)
    assert f"[bold yellow]{expected}[/bold yellow]" in layout.base_info_layout.renderable.renderable
    assert "[bold orange1]Metadata Only[/bold orange1]" in layout.base_info_layout.renderable.renderable
    console.print(layout.base_info_layout.renderable)
    interactive_text = console.export_text()
    assert "Validation Severity:" in interactive_text
    assert f"RO-Crate Package Type: {expected}" in interactive_text
    assert interactive_text.index("RO-Crate:") < interactive_text.index("RO-Crate Package Type:")
    assert interactive_text.index("RO-Crate Package Type:") < interactive_text.index("Target Profile:")
    assert "Validation Scope: Metadata Only" in interactive_text

    report = json.loads(format_validation_results({"ro-crate-1.2": result}))
    assert report["validation_settings"]["package_type"] == expected.lower()
    assert report["validation_settings"]["packaging_mode"] == mode
    assert report["validation_settings"]["metadata_only"] is True
    assert result.to_dict()["validation_settings"]["package_type"] == expected.lower()
    assert result.to_dict()["validation_settings"]["packaging_mode"] == mode
    assert result.to_dict()["validation_settings"]["metadata_only"] is True

    text_console = Console(record=True, width=120)
    text_console.print(ValidationResultTextOutputFormatter(result))
    text_report = text_console.export_text()
    assert "Packaging mode:" not in text_report
    assert "validation scope:" not in text_report


def test_interactive_report_shows_full_package_scope(tmp_path: Path):
    settings = ValidationSettings(rocrate_uri=tmp_path, metadata_only=False, offline=True)
    console = Console(record=True, width=120)
    layout = ValidationReportLayout(console, settings)
    _ = layout.layout
    assert layout.base_info_layout is not None
    console.print(layout.base_info_layout.renderable)
    assert "Validation Scope: Full Package" in console.export_text()


def test_attached_directory_missing_payload_stays_attached(tmp_path: Path):
    (tmp_path / "ro-crate-metadata.json").write_text(json.dumps(_minimal_metadata(file_id="missing.txt")))
    settings = ValidationSettings(
        rocrate_uri=tmp_path,
        profile_identifier="ro-crate-1.2",
        requirement_severity="REQUIRED",
        offline=True,
    )
    result = validate(settings)
    assert result.context.ro_crate.package_type is PackageType.ATTACHED
    assert any("missing.txt" in issue.message for issue in result.issues)
    (tmp_path / "missing.txt").write_text("now available")
    available_result = validate(settings)
    assert available_result.context.ro_crate.package_type is PackageType.ATTACHED
    assert not any("missing.txt" in issue.message for issue in available_result.issues)


def test_prefixed_descriptor_in_directory_does_not_become_detached(tmp_path: Path):
    (tmp_path / "prefix-ro-crate-metadata.json").write_text(json.dumps(_minimal_metadata()))
    settings = ValidationSettings(
        rocrate_uri=tmp_path,
        profile_identifier="ro-crate-1.2",
        requirement_severity="REQUIRED",
        offline=True,
    )
    result = validate(settings)
    assert result.context.ro_crate.package_type is PackageType.ATTACHED
    assert any('file descriptor "ro-crate-metadata.json" is not present' in issue.message for issue in result.issues)


def test_ambiguous_attached_descriptors_are_not_selected_arbitrarily(tmp_path: Path):
    (tmp_path / "first-ro-crate-metadata.json").write_text("{}")
    (tmp_path / "second-ro-crate-metadata.json").write_text("{}")
    crate = ROCrate.new_instance(tmp_path)
    assert crate.package_type is PackageType.ATTACHED
    assert crate.metadata_descriptor_id == "ro-crate-metadata.json"
    assert not crate.has_descriptor()

    (tmp_path / "ro-crate-metadata.json").write_text("{}")
    crate = ROCrate.new_instance(tmp_path)
    assert crate.metadata_descriptor_id == "ro-crate-metadata.json"
    assert crate.has_descriptor()
