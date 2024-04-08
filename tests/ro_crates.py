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
    def invalid_entity_about_type(self) -> Path:
        return self.base_path / "invalid_entity_about_type"

    @property
    def missing_conforms_to(self) -> Path:
        return self.base_path / "missing_conforms_to"

    @property
    def invalid_conforms_to(self) -> Path:
        return self.base_path / "invalid_conforms_to"
