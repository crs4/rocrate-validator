# Copyright (c) 2024 CRS4
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

import pytest

from rocrate_validator.models import Severity, ValidationSettings


def test_validation_settings_parse_dict():
    settings_dict = {
        "data_path": "/path/to/data",
        "profiles_path": "/path/to/profiles",
        "requirement_severity": "RECOMMENDED",
        "allow_infos": True,
        "inherit_profiles": False,
    }
    settings = ValidationSettings.parse(settings_dict)
    assert settings.data_path == "/path/to/data"
    assert settings.profiles_path == "/path/to/profiles"
    assert settings.requirement_severity == Severity.RECOMMENDED
    assert settings.allow_infos is True
    assert settings.inherit_profiles is False


def test_validation_settings_parse_object():
    existing_settings = ValidationSettings(
        data_path="/path/to/data",
        profiles_path="/path/to/profiles",
        requirement_severity=Severity.RECOMMENDED,
        allow_infos=True,
        inherit_profiles=False
    )
    settings = ValidationSettings.parse(existing_settings)
    assert settings.data_path == "/path/to/data"
    assert settings.profiles_path == "/path/to/profiles"
    assert settings.requirement_severity == Severity.RECOMMENDED
    assert settings.allow_infos is True
    assert settings.inherit_profiles is False


def test_validation_settings_parse_invalid_type():
    with pytest.raises(ValueError):
        ValidationSettings.parse("invalid_settings")


def test_validation_settings_to_dict():
    settings = ValidationSettings(
        data_path="/path/to/data",
        profiles_path="/path/to/profiles",
        requirement_severity=Severity.RECOMMENDED,
        allow_infos=True,
        inherit_profiles=False
    )
    settings_dict = settings.to_dict()
    assert settings_dict["data_path"] == "/path/to/data"
    assert settings_dict["profiles_path"] == "/path/to/profiles"
    assert settings_dict["requirement_severity"] == Severity.RECOMMENDED
    assert settings_dict["allow_infos"] is True
    assert settings_dict["inherit_profiles"] is False


def test_validation_settings_inherit_profiles():
    settings = ValidationSettings(inherit_profiles=True)
    assert settings.inherit_profiles is True

    settings = ValidationSettings(inherit_profiles=False)
    assert settings.inherit_profiles is False


def test_validation_settings_data_path():
    settings = ValidationSettings(data_path="/path/to/data")
    assert settings.data_path == "/path/to/data"


def test_validation_settings_profiles_path():
    settings = ValidationSettings(profiles_path="/path/to/profiles")
    assert settings.profiles_path == "/path/to/profiles"


def test_validation_settings_requirement_severity():
    settings = ValidationSettings(requirement_severity=Severity.RECOMMENDED)
    assert settings.requirement_severity == Severity.RECOMMENDED


def test_validation_settings_allow_infos():
    settings = ValidationSettings(allow_infos=True)
    assert settings.allow_infos is True


def test_validation_settings_abort_on_first():
    settings = ValidationSettings(abort_on_first=True)
    assert settings.abort_on_first is True
