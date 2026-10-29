"""Regression coverage for issue #238: filesystem names and file URI inputs."""

import json
import shutil
import zipfile

import pytest
from click.testing import CliRunner
from rdflib import RDF, URIRef

from rocrate_validator import models, services
from rocrate_validator.cli.main import cli
from rocrate_validator.rocrate import ROCrate
from rocrate_validator.rocrate.package_type import PackageType
from tests.ro_crates import ValidROCrate12
from tests.ro_crates_v1_3 import ValidROCrate13


@pytest.fixture
def minimal_crate(tmp_path):
    crate = tmp_path / "my crate"
    crate.mkdir()
    metadata = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "Minimal crate",
                "description": "A minimal RO-Crate",
                "datePublished": "2026-10-23",
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
            },
        ],
    }
    (crate / "ro-crate-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return crate


@pytest.mark.parametrize("representation", ["path", "string", "uri", "relative"])
@pytest.mark.parametrize("download", [False, True])
def test_validate_crate_in_directory_with_spaces(minimal_crate, monkeypatch, representation, download):
    monkeypatch.chdir(minimal_crate.parent)
    inputs = {
        "path": minimal_crate,
        "string": str(minimal_crate),
        "uri": minimal_crate.as_uri(),
        "relative": minimal_crate.name,
    }
    result = services.validate(
        models.ValidationSettings(
            rocrate_uri=inputs[representation],
            profile_identifier="ro-crate-1.1",
            requirement_severity=models.Severity.REQUIRED,
            disable_remote_crate_download=not download,
        )
    )
    assert result.passed(), [issue.message for issue in result.get_issues()]
    assert result.context.publicID == minimal_crate.as_uri() + "/"
    graph = result.context.data_graph
    descriptor = URIRef(minimal_crate.as_uri() + "/ro-crate-metadata.json")
    root = URIRef(minimal_crate.as_uri() + "/")
    assert (descriptor, RDF.type, URIRef("http://schema.org/CreativeWork")) in graph
    assert (descriptor, URIRef("http://schema.org/about"), root) in graph


@pytest.mark.parametrize("as_uri", [False, True])
def test_cli_validates_crate_with_spaces(minimal_crate, as_uri):
    location = minimal_crate.as_uri() if as_uri else str(minimal_crate)
    result = CliRunner().invoke(
        cli,
        [
            "validate",
            "--profile-identifier",
            "ro-crate-1.1",
            "--requirement-severity",
            "REQUIRED",
            "--no-paging",
            location,
        ],
    )
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("kind", ["zip", "metadata", "bagit"])
def test_file_uri_loaders_preserve_packaging(minimal_crate, kind):
    metadata = (minimal_crate / "ro-crate-metadata.json").read_text()
    expected = PackageType.ATTACHED
    if kind == "zip":
        location = minimal_crate.parent / "my crate.zip"
        with zipfile.ZipFile(location, "w") as archive:
            archive.writestr("ro-crate-metadata.json", metadata)
    elif kind == "metadata":
        location = minimal_crate / "ro-crate-metadata.json"
        expected = PackageType.DETACHED
    else:
        location = minimal_crate
        (location / "bagit.txt").write_text("BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
        (location / "data").mkdir()
        (location / "data" / "ro-crate-metadata.json").write_text(metadata)
        (location / "ro-crate-metadata.json").unlink()
    crate = ROCrate.new_instance(location.as_uri())
    assert crate.package_type is expected
    assert crate.metadata.as_dict()["@graph"][1]["name"] == "Minimal crate"


@pytest.mark.parametrize("version,source", [("1.2", ValidROCrate12().attached), ("1.3", ValidROCrate13().attached)])
def test_warm_validation_preserves_encoded_crate_bases(tmp_path, version, source):
    first = tmp_path / "my crate"
    second = tmp_path / "my%20crate"
    shutil.copytree(source, first)
    shutil.copytree(source, second)
    validator = models.Validator(
        models.ValidationSettings(
            rocrate_uri=first,
            profile_identifier=f"ro-crate-{version}",
            requirement_severity=models.Severity.REQUIRED,
        )
    )
    initial = validator.validate()
    repeated = validator.validate(second.as_uri())
    assert initial.passed(), [issue.message for issue in initial.get_issues()]
    assert repeated.passed(), [issue.message for issue in repeated.get_issues()]
    assert initial.context.publicID == first.as_uri() + "/"
    assert repeated.context.publicID == second.as_uri() + "/"
    assert initial.context.prepared_validation_plan is repeated.context.prepared_validation_plan
