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
Tests for the default validation profile and for the resolution of bare
profile tokens (e.g. `ro-crate`) to a concrete profile version.
"""

import logging

from rocrate_validator.constants import DEFAULT_PROFILE_IDENTIFIER
from rocrate_validator.models import URI, Profile, Severity, ValidationSettings
from rocrate_validator.services import get_profile, get_profiles, validate
from tests.ro_crates import ValidROC
from tests.ro_crates_v1_2 import ValidROCrate12
from tests.shared import RO_CRATE_1_1_PROFILE_IDENTIFIER

logger = logging.getLogger(__name__)

EXPECTED_DEFAULT_PROFILE_IDENTIFIER = "ro-crate-1.2"


def test_default_profile_identifier_is_ro_crate_1_2():
    """The base RO-Crate profile used by default is 1.2."""
    assert DEFAULT_PROFILE_IDENTIFIER == EXPECTED_DEFAULT_PROFILE_IDENTIFIER


def test_validation_settings_default_profile():
    """`ValidationSettings` picks up the default profile when none is given."""
    settings = ValidationSettings(rocrate_uri=URI(str(ValidROC().wrroc_paper)))
    assert settings.profile_identifier == EXPECTED_DEFAULT_PROFILE_IDENTIFIER


def test_bare_token_resolves_to_highest_version_via_services():
    """`get_profile` resolves a bare token to the highest available version."""
    assert get_profile("ro-crate").identifier == EXPECTED_DEFAULT_PROFILE_IDENTIFIER


def test_explicit_identifier_wins_over_token_resolution():
    """An exact identifier is never overridden by the highest-version rule."""
    assert get_profile(RO_CRATE_1_1_PROFILE_IDENTIFIER).identifier == RO_CRATE_1_1_PROFILE_IDENTIFIER
    assert get_profile("ro-crate-1.2").identifier == "ro-crate-1.2"


def test_bare_token_resolves_to_highest_version_in_validation_context():
    """
    The validation context resolves a bare token the same way `get_profile` does.

    These two used to disagree: the context picked the highest version while
    `Profile.find_in_list` returned the first match in load order.
    """
    settings = ValidationSettings(
        rocrate_uri=URI(str(ValidROC().wrroc_paper)),
        profile_identifier="ro-crate",
        requirement_severity=Severity.REQUIRED,
    )
    validate(settings)
    # The resolved identifier is written back to the settings
    assert settings.profile_identifier == EXPECTED_DEFAULT_PROFILE_IDENTIFIER


def test_version_sort_key_orders_versions_numerically():
    """Versions are compared component-wise, so 1.10 sorts after 1.9."""
    profiles = get_profiles()
    ro_crate_profiles = [p for p in profiles if p.token == "ro-crate"]
    assert len(ro_crate_profiles) >= 2, "Expected at least two versions of the RO-Crate profile"
    highest = max(ro_crate_profiles, key=lambda p: Profile.version_sort_key(p.version))
    assert highest.identifier == EXPECTED_DEFAULT_PROFILE_IDENTIFIER
    # A plain string comparison would rank "1.9" above "1.10"
    assert Profile.version_sort_key("1.10") > Profile.version_sort_key("1.9")
    assert Profile.version_sort_key(None) < Profile.version_sort_key("0.1")


def test_default_profile_validates_a_1_2_crate():
    """A 1.2 crate validates against the default profile without pinning it."""
    settings = ValidationSettings(
        rocrate_uri=URI(str(ValidROCrate12().attached)),
        requirement_severity=Severity.REQUIRED,
    )
    result = validate(settings)
    assert result.passed(), "A valid RO-Crate 1.2 should pass under the default profile"


def test_default_profile_rejects_a_1_1_context():
    """
    A 1.1-era crate no longer passes under the default profile.

    This documents the breaking part of the default switch: the crate declares the
    1.1 JSON-LD context, which 1.2 requires to be the 1.2 one.
    """
    settings = ValidationSettings(
        rocrate_uri=URI(str(ValidROC().wrroc_paper)),
        requirement_severity=Severity.REQUIRED,
    )
    result = validate(settings)
    assert not result.passed()
    failed_check_ids = {issue.check.identifier for issue in result.get_issues()}
    assert "ro-crate-1.2_2.2" in failed_check_ids, (
        f"Expected the 1.2 context check to fail, got: {sorted(failed_check_ids)}"
    )

    # ...and it still passes when explicitly pinned to 1.1
    settings.profile_identifier = RO_CRATE_1_1_PROFILE_IDENTIFIER
    assert validate(settings).passed(), "Pinning `ro-crate-1.1` should restore the previous behaviour"
