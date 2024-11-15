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

from rocrate_validator import models, services
from rocrate_validator.models import (LevelCollection, RequirementLevel,
                                      Severity, ValidationSettings)
from tests.ro_crates import InvalidRootDataEntity, WROCInvalidReadme


def test_severity_ordering():
    assert hash(Severity.OPTIONAL) != 0  # should be ok as long it hash runs
    assert Severity.OPTIONAL < Severity.RECOMMENDED
    assert Severity.RECOMMENDED > Severity.OPTIONAL
    assert Severity.RECOMMENDED < Severity.REQUIRED
    assert Severity.OPTIONAL < Severity.REQUIRED
    assert Severity.OPTIONAL == Severity.OPTIONAL
    assert Severity.RECOMMENDED <= Severity.REQUIRED
    assert Severity.RECOMMENDED >= Severity.OPTIONAL


def test_level_ordering():
    may = RequirementLevel('MAY', Severity.OPTIONAL)
    should = RequirementLevel('SHOULD', Severity.RECOMMENDED)
    assert may < should
    assert should > may
    assert should != may
    assert may == may
    assert may != 1
    assert may != RequirementLevel('OPTIONAL', Severity.OPTIONAL)
    with pytest.raises(TypeError):
        _ = may > 1


def test_level_basics():
    may = RequirementLevel('MAY', Severity.OPTIONAL)
    assert str(may) == "MAY"
    assert int(may) == Severity.OPTIONAL.value
    assert hash(may) != 0  # should be find as long as it runs


def test_level_collection():
    assert LevelCollection.get('may') == LevelCollection.MAY

    # Test ordering
    assert LevelCollection.MAY < LevelCollection.SHOULD
    assert LevelCollection.SHOULD > LevelCollection.MAY
    assert LevelCollection.SHOULD != LevelCollection.MAY
    assert LevelCollection.MAY == LevelCollection.MAY

    all_levels = LevelCollection.all()
    assert 10 == len(all_levels)
    level_names = [level.name for level in all_levels]
    # Test a few of the keys
    assert 'MAY' in level_names
    assert 'SHOULD_NOT' in level_names
    assert 'RECOMMENDED' in level_names
    assert 'REQUIRED' in level_names


@pytest.fixture
def validation_settings():
    return ValidationSettings(
        requirement_severity=Severity.OPTIONAL,
        abort_on_first=False
    )


# @pytest.mark.skip(reason="Temporarily disabled: we need an RO-Crate with multiple failed requirements to test this.")
def test_sortability_requirements(validation_settings: ValidationSettings):
    validation_settings.rocrate_uri = InvalidRootDataEntity().invalid_root_type
    result: models.ValidationResult = services.validate(validation_settings)
    failed_requirements = sorted(result.failed_requirements, reverse=True)
    assert len(failed_requirements) > 1
    assert failed_requirements[0] >= failed_requirements[1]
    assert failed_requirements[0].order_number >= failed_requirements[1].order_number


def test_sortability_checks(validation_settings: ValidationSettings):
    validation_settings.rocrate_uri = WROCInvalidReadme().wroc_readme_wrong_encoding_format
    result: models.ValidationResult = services.validate(validation_settings)
    failed_checks = sorted(result.failed_checks, reverse=True)
    assert len(failed_checks) > 1
    i_checks = iter(failed_checks)
    one, two = next(i_checks), next(i_checks)
    assert one >= two
    assert one.requirement >= two.requirement


def test_sortability_issues(validation_settings: ValidationSettings):
    validation_settings.rocrate_uri = WROCInvalidReadme().wroc_readme_wrong_encoding_format
    result: models.ValidationResult = services.validate(validation_settings)
    issues = sorted(result.get_issues(min_severity=Severity.OPTIONAL), reverse=True)
    assert len(issues) > 1
    i_issues = iter(issues)
    one, two = next(i_issues), next(i_issues)
    assert one >= two
    assert one.check >= two.check


def test_hidden_shape():
    rocrate_profile = services.get_profile("ro-crate-1.1")
    assert rocrate_profile is not None, "Profile should not be None"
    # get the hidden requirement
    hidden_requirement = rocrate_profile.get_requirement("Identify the Root Data Entity of the RO-Crate")
    assert hidden_requirement is not None, "Requirement should not be None"
    # check if the requirement is hidden
    assert hidden_requirement.hidden is True, "Hidden should be True"
