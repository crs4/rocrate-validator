from pathlib import Path
from tempfile import TemporaryDirectory

from pytest import fixture

CURRENT_PATH = Path(__file__).resolve().parent
TEST_DATA_PATH = (CURRENT_PATH / "data").absolute()
CRATES_DATA_PATH = TEST_DATA_PATH / "crates"
VALID_CRATES_DATA_PATH = CRATES_DATA_PATH / "valid"
INVALID_CRATES_DATA_PATH = CRATES_DATA_PATH / "invalid"


@fixture
def ro_crates_path() -> Path:
    return CRATES_DATA_PATH


class ValidROC:
    @property
    def wrroc_paper(self) -> Path:
        return VALID_CRATES_DATA_PATH / "wrroc-paper"

    @property
    def wrroc_paper_long_date(self) -> Path:
        return VALID_CRATES_DATA_PATH / "wrroc-paper-long-date"

    @property
    def workflow_roc(self) -> Path:
        return VALID_CRATES_DATA_PATH / "workflow-roc"


class InvalidFileDescriptor:

    base_path = INVALID_CRATES_DATA_PATH / "0_file_descriptor_format"

    @property
    def missing_file_descriptor(self) -> Path:
        return TemporaryDirectory()

    @property
    def invalid_json_format(self) -> Path:
        return self.base_path / "invalid_json_format"

    @property
    def invalid_jsonld_format(self) -> Path:
        return self.base_path / "invalid_jsonld_format"


class InvalidRootDataEntity:

    base_path = INVALID_CRATES_DATA_PATH / "2_root_data_entity_metadata"

    @property
    def missing_root(self) -> Path:
        return self.base_path / "missing_root_entity"

    @property
    def invalid_root_type(self) -> Path:
        return self.base_path / "invalid_root_type"

    @property
    def invalid_root_value(self) -> Path:
        return self.base_path / "invalid_root_value"

    @property
    def recommended_root_value(self) -> Path:
        return self.base_path / "recommended_root_value"

    @property
    def invalid_root_date(self) -> Path:
        return self.base_path / "invalid_root_date"

    @property
    def missing_root_name(self) -> Path:
        return self.base_path / "missing_root_name"

    @property
    def missing_root_description(self) -> Path:
        return self.base_path / "missing_root_description"

    @property
    def missing_root_license(self) -> Path:
        return self.base_path / "missing_root_license"

    @property
    def missing_root_license_name(self) -> Path:
        return self.base_path / "missing_root_license_name"

    @property
    def missing_root_license_description(self) -> Path:
        return self.base_path / "missing_root_license_description"

    @property
    def valid_referenced_generic_data_entities(self) -> Path:
        return self.base_path / "valid_referenced_generic_data_entities"


class InvalidFileDescriptorEntity:

    base_path = INVALID_CRATES_DATA_PATH / "1_file_descriptor_metadata"

    @property
    def missing_entity(self) -> Path:
        return self.base_path / "missing_entity"

    @property
    def invalid_entity_type(self) -> Path:
        return self.base_path / "invalid_entity_type"

    @property
    def missing_entity_about(self) -> Path:
        return self.base_path / "missing_entity_about"

    @property
    def invalid_entity_about(self) -> Path:
        return self.base_path / "invalid_entity_about"

    @property
    def invalid_entity_about_type(self) -> Path:
        return self.base_path / "invalid_entity_about_type"

    @property
    def missing_conforms_to(self) -> Path:
        return self.base_path / "missing_conforms_to"

    @property
    def invalid_conforms_to(self) -> Path:
        return self.base_path / "invalid_conforms_to"


class InvalidDataEntity:

    base_path = INVALID_CRATES_DATA_PATH / "4_data_entity_metadata"

    @property
    def missing_hasPart_data_entity_reference(self) -> Path:
        return self.base_path / "invalid_missing_hasPart_reference"

    @property
    def direct_hasPart_data_entity_reference(self) -> Path:
        return self.base_path / "valid_direct_hasPart_reference"

    @property
    def indirect_hasPart_data_entity_reference(self) -> Path:
        return self.base_path / "valid_indirect_hasPart_reference"

    @property
    def directory_data_entity_wo_trailing_slash(self) -> Path:
        return self.base_path / "directory_data_entity_wo_trailing_slash"

    @property
    def missing_data_entity_encoding_format(self) -> Path:
        return self.base_path / "missing_encoding_format"

    @property
    def invalid_data_entity_encoding_format_pronom(self) -> Path:
        return self.base_path / "invalid_encoding_format_pronom"

    @property
    def invalid_encoding_format_ctx_entity_missing_ws_type(self) -> Path:
        return self.base_path / "invalid_encoding_format_ctx_entity_missing_ws_type"

    @property
    def invalid_encoding_format_ctx_entity_missing_ws_name(self) -> Path:
        return self.base_path / "invalid_encoding_format_ctx_entity_missing_ws_name"

    @property
    def valid_encoding_format_ctx_entity(self) -> Path:
        return self.base_path / "valid_encoding_format_ctx_entity"

    @property
    def valid_encoding_format_pronom(self) -> Path:
        return self.base_path / "valid_encoding_format_pronom"


class InvalidMainWorkflow:

    base_path = INVALID_CRATES_DATA_PATH / "0_main_workflow"

    @property
    def main_workflow_bad_type(self) -> Path:
        return self.base_path / "main_workflow_bad_type"

    @property
    def main_workflow_no_lang(self) -> Path:
        return self.base_path / "main_workflow_no_lang"

    @property
    def main_workflow_no_image(self) -> Path:
        return self.base_path / "main_workflow_no_image"
