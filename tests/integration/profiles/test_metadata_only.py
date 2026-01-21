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
import logging
from pathlib import Path
import shutil
import tempfile

from rocrate_validator import models
from tests.ro_crates import ValidROC
from tests.shared import do_entity_test
import pytest

# set up logging
logger = logging.getLogger(__name__)


def valid_roc_paths():
    """Fixture that returns a list of paths from ValidROC object."""
    valid_roc = ValidROC()
    return [
        value
        for attr in dir(valid_roc)
        if not attr.startswith('_')
        and not any(excluded in attr for excluded in ('bagit', 'multi_profile_crate', 'rocrate_with_relative_root'))
        and not str(value := getattr(valid_roc, attr)).endswith('.zip')
    ]


@pytest.mark.parametrize("valid_roc_path", valid_roc_paths())
def test_valid_ro_crates_from_folder(valid_roc_path):
    """Test all valid RO-Crates."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        temp_path = Path(tmpdirname) / valid_roc_path.name
        shutil.copytree(valid_roc_path, temp_path)
        valid_roc_path = temp_path
        do_entity_test(
            valid_roc_path,
            models.Severity.REQUIRED,
            True,
            [],
            [],
            metadata_only=True
        )


@pytest.mark.parametrize("valid_roc_path", valid_roc_paths())
def test_valid_ro_crates_from_metadata_dict(valid_roc_path):
    """Test all valid RO-Crates using metadata dict."""
    metadata_dict = None
    # Load the metadata dict from the RO-Crate
    if not isinstance(valid_roc_path, str):
        with open(valid_roc_path / "ro-crate-metadata.json", "r") as f:
            metadata_dict = json.load(f)
        assert metadata_dict is not None, "Failed to load metadata dict"
        assert isinstance(metadata_dict, dict), "Metadata dict is not a dictionary"
        do_entity_test(
            valid_roc_path,
            models.Severity.REQUIRED,
            True,
            [],
            [],
            metadata_dict=metadata_dict,
            metadata_only=True
        )
