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

import json
import shutil
import tempfile
from pathlib import Path

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationSettings
from rocrate_validator.rocrate import ROCrateMetadata
from rocrate_validator.services import detect_profiles, get_profiles, validate
from tests.ro_crates import InvalidMultiProfileROC, ValidROC, InvalidFileDescriptorEntity

# set up logging
logger = logging.getLogger(__name__)


metadata_file_descriptor = Path(ROCrateMetadata.METADATA_FILE_DESCRIPTOR)


def test_default_profiles_list():
    """
    Test the list of profiles.
    """
    logger.debug("Testing the list of profiles")
    profiles = get_profiles()
    logger.debug("Profiles: %s", profiles)
    # Check the number of profiles
    assert len(profiles) > 0, "Expected at least one profile"


def test_extra_profiles_list(fake_profiles_path: Path):
    logger.error("Testing the list of extra profiles")
    default_profiles = get_profiles()
    assert len(default_profiles) > 0, "Expected at least one default profile"
    extra_profiles = get_profiles(profiles_path=fake_profiles_path)
    logger.error("Extra profiles: %s", extra_profiles)
    # Check the number of extra profiles
    assert len(extra_profiles) > 0, "Expected at least one extra profile"

    all_profiles = get_profiles(extra_profiles_path=fake_profiles_path)
    logger.error("All profiles: %s", all_profiles)
    # Check the number of all profiles
    assert len(all_profiles) > len(default_profiles), \
        "Expected more profiles with extra profiles added than the default ones"
    assert len(all_profiles) == len(extra_profiles) + len(default_profiles), \
        "Expected the number of all profiles to be the sum of default and extra profiles"


def test_valid_local_rocrate():
    logger.debug("Validating a local RO-Crate: %s", ValidROC().wrroc_paper)
    profiles = detect_profiles(ValidationSettings(
        rocrate_uri=ValidROC().wrroc_paper
    ))

    logger.debug("Candidate profiles: %s", profiles)
    # Check the number of detected profiles
    assert len(profiles) == 1, "Expected a single profile"
    # Check the detected profile
    assert profiles[0].identifier == "ro-crate-1.1", "Expected the 'ro-crate' profile"


def test_valid_local_workflow_rocrate():
    # Set the rocrate_uri to the workflow RO-Crate
    crate_path = ValidROC().workflow_roc
    logger.debug("Validating a local RO-Crate: %s", crate_path)
    profiles = detect_profiles(ValidationSettings(
        rocrate_uri=crate_path
    ))
    assert len(profiles) == 1, "Expected a single profile"
    assert profiles[0].identifier == "workflow-ro-crate-1.0", "Expected the 'workflow-ro-crate-1.0' profile"


def test_valid_local_process_run_crate():
    # Set the rocrate_uri to the process run RO-Crate
    crate_path = ValidROC().process_run_crate
    logger.debug("Validating a local RO-Crate: %s", crate_path)
    profiles = detect_profiles(ValidationSettings(
        rocrate_uri=crate_path
    ))
    assert len(profiles) == 1, "Expected a single profile"
    assert profiles[0].identifier == "process-run-crate-0.5", "Expected the 'process-run-crate-0.5' profile"


def test_valid_local_workflow_testing_ro_crate():
    # Set the rocrate_uri to the workflow testing RO-Crate
    crate_path = ValidROC().workflow_testing_ro_crate
    logger.debug("Validating a local RO-Crate: %s", crate_path)
    profiles = detect_profiles(ValidationSettings(
        rocrate_uri=crate_path
    ))
    assert len(profiles) == 1, "Expected a single profile"
    assert profiles[0].identifier == "workflow-testing-ro-crate-0.1", \
        "Expected the 'workflow-testing-ro-crate-0.1' profile"


def test_disable_inherited_profiles_issue_reporting():
    # Set the rocrate_uri to the workflow testing RO-Crate
    crate_path = ValidROC().workflow_testing_ro_crate
    logger.debug("Validating a local RO-Crate: %s", crate_path)

    # First, validate with inherited profiles issue reporting enabled
    settings = ValidationSettings(
        rocrate_uri=crate_path,
        disable_inherited_profiles_issue_reporting=False
    )
    result = validate(settings)
    total_issues_with_inheritance = len(result.get_issues())
    logger.debug("Total issues with inherited profiles issue reporting enabled: %d", total_issues_with_inheritance)

    # Now, validate with inherited profiles issue reporting disabled
    settings.disable_inherited_profiles_issue_reporting = True
    result = validate(settings)
    total_issues_without_inheritance = len(result.get_issues())
    logger.debug("Total issues with inherited profiles issue reporting disabled: %d", total_issues_without_inheritance)

    # Check that disabling inherited profiles issue reporting reduces the number of reported issues
    assert total_issues_without_inheritance <= total_issues_with_inheritance, \
        "Disabling inherited profiles issue reporting should not increase the number of reported issues"

    # Check that all reported issues are from the main profile
    main_profile_identifier = "workflow-testing-ro-crate-0.1"
    for issue in result.get_issues():
        assert issue.check.profile.identifier == main_profile_identifier, \
            "All reported issues should belong to the main profile when inherited profiles issue reporting is disabled"


def test_skip_pycheck_on_workflow_ro_crate():
    # Set the rocrate_uri to the workflow testing RO-Crate
    crate_path = InvalidFileDescriptorEntity().invalid_conforms_to
    logger.debug("Validating a local RO-Crate: %s", crate_path)
    settings = ValidationSettings(rocrate_uri=crate_path)
    result = validate(settings)
    assert not result.passed(), \
        "The RO-Crate is expected to be invalid because of an incorrect conformsTo field and missing resources"
    assert len(result.failed_checks) == 2, "No failed checks expected when skipping the problematic check"
    assert any(check.identifier == "ro-crate-1.1_5.3" for check in result.failed_checks), \
        "Expected the check 'ro-crate-1.1_5.3' to fail"
    assert any(check.identifier == "ro-crate-1.1_12.1" for check in result.failed_checks), \
        "Expected the check 'ro-crate-1.1_12.1' to fail"

    # Perform a new validation skipping specific checks
    settings.skip_checks = ["ro-crate-1.1_5.3", "ro-crate-1.1_12.1"]
    result = validate(settings)
    assert result.passed(), \
        "The RO-Crate should be valid when skipping the checks related to the invalid file descriptor entity"

    # Ensure that the skipped checks are indeed skipped
    skipped_check_ids = {check.identifier for check in result.skipped_checks}
    # logger.error("Skipped checks: %s", result.skipped_checks)
    assert "ro-crate-1.1_5.3" in skipped_check_ids, "Expected check 'ro-crate-1.1_5.3' to be skipped"
    assert "ro-crate-1.1_12.1" in skipped_check_ids, "Expected check 'ro-crate-1.1_12.1' to be skipped"


def test_valid_local_multi_profile_crate():
    # Set the rocrate_uri to the multi-profile RO-Crate
    crate_path = InvalidMultiProfileROC().invalid_multi_profile_crate
    logger.debug("Validating a local RO-Crate: %s", crate_path)
    profiles = detect_profiles(ValidationSettings(
        rocrate_uri=crate_path
    ))
    assert len(profiles) == 2, "Expected two profiles"

    # Extract profiles identifiers
    profiles_ids = [profile.identifier for profile in profiles]
    assert "provenance-run-crate-0.5" in profiles_ids, "Expected the 'provenance-run-crate' profile"
    assert "workflow-testing-ro-crate-0.1" in profiles_ids, \
        "Expected the 'workflow-testing-ro-crate-0.1' profile"


def test_valid_crate_folder_with_metadata_only():
    # Set the rocrate_uri to the WRROC paper RO-Crate
    crate_path = ValidROC().wrroc_paper
    logger.debug("Validating a local RO-Crate in metadata-only mode: %s", crate_path)

    # Copy the ro-crate-metadata.json content only to a temporary folder
    with tempfile.TemporaryDirectory() as tmpdirname:
        metadata_src = crate_path / "ro-crate-metadata.json"
        metadata_dst = Path(tmpdirname) / "ro-crate-metadata.json"
        shutil.copy(metadata_src, metadata_dst)

        # Define shared settings object
        settings = ValidationSettings(
            rocrate_uri=Path(tmpdirname),
            metadata_only=True
        )

        profiles = detect_profiles(settings)

        logger.debug("Candidate profiles: %s", profiles)
        # Check the number of detected profiles
        assert len(profiles) == 1, "Expected a single profile"
        # Check the detected profile
        assert profiles[0].identifier == "ro-crate-1.1", "Expected the 'ro-crate' profile"

        result = validate(settings)
        assert result.passed(), "RO-Crate should be valid in metadata-only mode"


def test_valid_crate_metadata_dict_with_metadata_only():
    # Set the rocrate_uri to the WRROC paper RO-Crate
    crate_path = ValidROC().wrroc_paper
    logger.debug("Validating a local RO-Crate in metadata-only mode: %s", crate_path)

    # Load the metadata dict from the RO-Crate
    with open(crate_path / "ro-crate-metadata.json", "r") as f:
        metadata_dict = json.loads(f.read())

    # Define shared settings object
    settings = ValidationSettings(
        metadata_dict=metadata_dict
    )

    profiles = detect_profiles(settings)

    logger.debug("Candidate profiles: %s", profiles)
    # Check the number of detected profiles
    assert len(profiles) == 1, "Expected a single profile"
    # Check the detected profile
    assert profiles[0].identifier == "ro-crate-1.1", "Expected the 'ro-crate' profile"

    from rocrate_validator.services import validate_metadata_as_dict
    result = validate_metadata_as_dict(metadata_dict, settings)
    assert result.passed(), "RO-Crate should be valid in metadata-only mode"
