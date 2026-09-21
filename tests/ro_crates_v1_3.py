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

from pathlib import Path

from pytest import fixture

CURRENT_PATH = Path(__file__).resolve().parent
TEST_DATA_PATH = (CURRENT_PATH / "data").absolute()
CRATES_DATA_PATH = TEST_DATA_PATH / "crates"
VALID_CRATES_DATA_PATH = CRATES_DATA_PATH / "valid"
INVALID_CRATES_DATA_PATH = CRATES_DATA_PATH / "invalid"


@fixture
def ro_crates_path() -> Path:
    return CRATES_DATA_PATH


BASE_PATH = CRATES_DATA_PATH / "rocrate-1.3"


class WorkflowsScripts:
    WORKFLOWS_SCRIPTS_CRATES_PATH = BASE_PATH / "11_workflows_scripts"

    # --- Script type ---
    @property
    def valid_script_type(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "script_type" / "valid"

    @property
    def invalid_script_type(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "script_type" / "invalid"

    # --- Script name ---
    @property
    def valid_script_name(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "script_name" / "valid"

    @property
    def invalid_script_name(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "script_name" / "invalid"

    # --- Workflow type ---
    @property
    def valid_workflow_type(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_type" / "valid"

    @property
    def invalid_workflow_type_missing_file(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_type" / "invalid_missing_file"

    @property
    def invalid_workflow_type_missing_ssc(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_type" / "invalid_missing_ssc"

    # --- Workflow name ---
    @property
    def valid_workflow_name(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_name" / "valid"

    @property
    def invalid_workflow_name(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_name" / "invalid"

    # --- programmingLanguage ---
    @property
    def valid_programming_language(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "programming_language" / "valid"

    @property
    def invalid_programming_language(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "programming_language" / "invalid"

    # --- Workflow conformsTo ---
    @property
    def valid_workflow_conformsTo(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_conformsTo" / "valid"

    @property
    def invalid_workflow_conformsTo(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "workflow_conformsTo" / "invalid"

    # --- ImageObject encodingFormat ---
    @property
    def valid_image_encoding_format(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "image_encoding_format" / "valid"

    @property
    def invalid_image_encoding_format(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "image_encoding_format" / "invalid"

    # --- ImageObject about ---
    @property
    def valid_image_about(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "image_about" / "valid"

    @property
    def invalid_image_about(self) -> Path:
        return self.WORKFLOWS_SCRIPTS_CRATES_PATH / "image_about" / "invalid"


class ValidROCrate13:
    base_path = VALID_CRATES_DATA_PATH

    @property
    def attached(self) -> Path:
        return self.base_path / "ro-crate-1.3-attached"

    @property
    def attached_absolute_root(self) -> Path:
        return self.base_path / "ro-crate-1.3-absolute-root"

    @property
    def detached(self) -> Path:
        return self.base_path / "detached-1.3" / "dataset-ro-crate-metadata.json"

    @property
    def detached_prefixed(self) -> Path:
        return self.base_path / "detached-1.3" / "test-ro-crate-metadata.json"
