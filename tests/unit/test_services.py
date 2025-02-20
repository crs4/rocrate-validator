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

from pathlib import Path

import pytest

from rocrate_validator import log as logging
from rocrate_validator.errors import ROCrateInvalidURIError
from rocrate_validator.rocrate import (ROCrate, ROCrateEntity,
                                       ROCrateLocalFolder, ROCrateLocalZip,
                                       ROCrateMetadata, ROCrateRemoteZip)
from tests.ro_crates import InvalidDataEntity, ValidROC

from rocrate_validator.models import ValidationSettings
from rocrate_validator.services import detect_profiles

# set up logging
logger = logging.getLogger(__name__)


metadata_file_descriptor = Path(ROCrateMetadata.METADATA_FILE_DESCRIPTOR)


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
