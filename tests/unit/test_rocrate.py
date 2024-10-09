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
from rocrate_validator.rocrate import (
    ROCrate,
    ROCrateEntity,
    ROCrateLocalFolder,
    ROCrateLocalZip,
    ROCrateMetadata,
    ROCrateRemoteZip,
)
from tests.ro_crates import ValidROC

# set up logging
logger = logging.getLogger(__name__)


metadata_file_descriptor = Path(ROCrateMetadata.METADATA_FILE_DESCRIPTOR)


################################
#     ROCrateLocalFolder
################################


def test_invalid_local_ro_crate():
    with pytest.raises(ROCrateInvalidURIError):
        ROCrateLocalFolder("/tmp/does_not_exist")


def test_valid_local_rocrate():
    roc = ROCrateLocalFolder(ValidROC().wrroc_paper)
    assert isinstance(roc, ROCrateLocalFolder)

    # raise Exception("Test not implemented: %s", str(roc.uri))

    # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    assert len(files) == 14, "Should have 14 files"

    # test is_file
    assert roc.has_file(metadata_file_descriptor), "Should be a file"

    # test file size
    size = roc.get_file_size(metadata_file_descriptor)
    assert size == 26788, "Size should be 26788"

    # test crate size
    assert roc.size == 309521, "Size should be 309521"

    # test get_file_content binary mode
    content = roc.get_file_content(metadata_file_descriptor)
    assert isinstance(content, bytes), "Content should be bytes"

    # test get_file_content text mode
    content = roc.get_file_content(metadata_file_descriptor, binary_mode=False)
    assert isinstance(content, str), "Content should be str"

    # test metadata
    metadata = roc.metadata
    assert isinstance(metadata, ROCrateMetadata), "Metadata should be ROCrateMetadata"

    # test metadata id
    file_descriptor_entity = metadata.get_entity("ro-crate-metadata.json")
    logger.debug(f"File descriptor entity: {file_descriptor_entity}")
    assert isinstance(file_descriptor_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert file_descriptor_entity.id == "ro-crate-metadata.json", "Id should be ro-crate-metadata.json"
    assert file_descriptor_entity.type == "CreativeWork", "Type should be File"

    # test root data entity
    root_data_entity = metadata.get_entity("./")
    logger.debug(f"Root data entity: {root_data_entity}")
    assert isinstance(root_data_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert root_data_entity.id == "./", "Id should be ./"
    assert root_data_entity.type == "Dataset", "Type should be Dataset"
    assert root_data_entity.name == "Recording provenance of workflow runs with RO-Crate (RO-Crate and mapping)", \
        "Name should be wrroc-paper"

    # check metadata consistency
    assert root_data_entity.metadata == metadata, "Metadata should be the same"
    assert root_data_entity.metadata == roc.metadata, "Metadata should be the same"

    # check availability
    assert root_data_entity.is_available(), "Main entity should be available"


################################
#      ROCrateLocalZip
################################
def test_valid_zip_rocrate():
    roc = ROCrateLocalZip(ValidROC().sort_and_change_archive)
    assert isinstance(roc, ROCrateLocalZip)

    # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    assert len(files) == 11, "Should have 11 files"

    # test is_file
    assert roc.has_file(metadata_file_descriptor), "Should be a file"

    # test file size
    size = roc.get_file_size(metadata_file_descriptor)
    assert size == 3935, "Size should be 3935"

    # test crate size
    assert roc.size == 137039, "Size should be 136267"

    # test get_file_content binary mode
    content = roc.get_file_content(metadata_file_descriptor)
    assert isinstance(content, bytes), "Content should be bytes"

    # test get_file_content text mode
    content = roc.get_file_content(metadata_file_descriptor, binary_mode=False)
    assert isinstance(content, str), "Content should be str"

    # test metadata
    metadata = roc.metadata
    assert isinstance(metadata, ROCrateMetadata), "Metadata should be ROCrateMetadata"

    # test metadata id
    file_descriptor_entity = metadata.get_entity("ro-crate-metadata.json")
    logger.debug(f"File descriptor entity: {file_descriptor_entity}")
    assert isinstance(file_descriptor_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert file_descriptor_entity.id == "ro-crate-metadata.json", "Id should be ro-crate-metadata.json"
    assert file_descriptor_entity.type == "CreativeWork", "Type should be File"

    # test root data entity
    root_data_entity = metadata.get_entity("./")
    logger.debug(f"Root data entity: {root_data_entity}")
    assert isinstance(root_data_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert root_data_entity.id == "./", "Id should be ./"
    assert root_data_entity.type == "Dataset", "Type should be Dataset"
    assert root_data_entity.name == "sort-and-change-case", "Name should be sort_and_change"

    # test subEntity mainEntity
    main_entity = root_data_entity.get_property("mainEntity")
    logger.debug(f"Main entity: {main_entity}")
    assert isinstance(main_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert main_entity.id == "sort-and-change-case.ga", "Id should be main-entity"
    assert "ComputationalWorkflow" in main_entity.type, "Type should be ComputationalWorkflow"

    # check metadata consistency
    assert main_entity.metadata == metadata, "Metadata should be the same"
    assert main_entity.metadata == roc.metadata, "Metadata should be the same"

    # check availability
    assert main_entity.is_available(), "Main entity should be available"


################################
#      ROCrateRemoteZip
################################


def test_valid_remote_zip_rocrate():
    roc = ROCrateRemoteZip(ValidROC().sort_and_change_remote)
    # assert isinstance(roc,  ROCrateRemoteZip)
    # return
    # # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    assert len(files) == 11, "Should have 11 files"

    # test crate size
    assert roc.size == 137039, "Size should be 136267"

    # test is_file
    assert roc.has_file(metadata_file_descriptor), "Should be a file"

    # test file size
    size = roc.get_file_size(metadata_file_descriptor)
    assert size == 3935, "Size should be 3935"

    # test get_file_content binary mode
    content = roc.get_file_content(metadata_file_descriptor)
    assert isinstance(content, bytes), "Content should be bytes"

    # test get_file_content text mode
    content = roc.get_file_content(metadata_file_descriptor, binary_mode=False)
    assert isinstance(content, str), "Content should be str"

    # test metadata
    metadata = roc.metadata
    assert isinstance(metadata, ROCrateMetadata), "Metadata should be ROCrateMetadata"

    # test metadata id
    file_descriptor_entity = metadata.get_entity("ro-crate-metadata.json")
    logger.debug(f"File descriptor entity: {file_descriptor_entity}")
    assert isinstance(file_descriptor_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert file_descriptor_entity.id == "ro-crate-metadata.json", "Id should be ro-crate-metadata.json"
    assert file_descriptor_entity.type == "CreativeWork", "Type should be File"

    # test root data entity
    root_data_entity = metadata.get_entity("./")
    logger.debug(f"Root data entity: {root_data_entity}")
    assert isinstance(root_data_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert root_data_entity.id == "./", "Id should be ./"
    assert root_data_entity.type == "Dataset", "Type should be Dataset"
    assert root_data_entity.name == "sort-and-change-case", "Name should be sort_and_change"

    # test subEntity mainEntity
    main_entity = root_data_entity.get_property("mainEntity")
    logger.debug(f"Main entity: {main_entity}")
    assert isinstance(main_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    assert main_entity.id == "sort-and-change-case.ga", "Id should be main-entity"
    assert "ComputationalWorkflow" in main_entity.type, "Type should be ComputationalWorkflow"

    # check metadata consistency
    assert main_entity.metadata == metadata, "Metadata should be the same"
    assert main_entity.metadata == roc.metadata, "Metadata should be the same"

    # check availability
    assert main_entity.is_available(), "Main entity should be available"


def test_external_file():
    content = ROCrate.get_external_file_content(ValidROC().sort_and_change_remote)
    assert isinstance(content, bytes), "Content should be bytes"

    size = ROCrate.get_external_file_size(ValidROC().sort_and_change_remote)
    assert size == 137039, "Size should be 137039"
