# Copyright (c) 2024-2025 CRS4
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
from rocrate_validator.rocrate import (BagitROCrate, ROCrate,
                                       ROCrateBagitLocalFolder,
                                       ROCrateBagitLocalZip,
                                       ROCrateBagitRemoteZip, ROCrateEntity,
                                       ROCrateLocalFolder, ROCrateLocalZip,
                                       ROCrateMetadata, ROCrateRemoteZip)
from tests.ro_crates import InvalidDataEntity, ValidROC

# set up logging
logger = logging.getLogger(__name__)


metadata_file_descriptor = Path(ROCrateMetadata.METADATA_FILE_DESCRIPTOR)


################################
#     ROCrateLocalFolder
################################


def test_invalid_local_ro_crate():
    with pytest.raises(ROCrateInvalidURIError):
        ROCrateLocalFolder("/tmp/does_not_exist")


def test_is_bagit_rocrate():
    assert BagitROCrate.is_bagit_wrapping_crate(ValidROC().bagit), \
        "Should be a BagIt RO-Crate"

    assert BagitROCrate.is_bagit_wrapping_crate(ValidROC().bagit_zip), \
        "Should be a BagIt Zip RO-Crate"

    assert BagitROCrate.is_bagit_wrapping_crate(ValidROC().bagit_remote_zip), \
        "Should be a BagIt Remote Zip RO-Crate"

    assert not BagitROCrate.is_bagit_wrapping_crate(ValidROC().wrroc_paper), \
        "Should not be a BagIt RO-Crate"

    assert not BagitROCrate.is_bagit_wrapping_crate(ValidROC().sort_and_change_archive), \
        "Should not be a BagIt RO-Crate"

    assert not BagitROCrate.is_bagit_wrapping_crate(ValidROC().sort_and_change_remote), \
        "Should not be a BagIt RO-Crate"


def test_abstract_bagit_rocrate_instantiation():
    # Check that the base class BagItROCrate cannot be instantiated directly
    with pytest.raises(TypeError, match="Can't instantiate"):
        BagitROCrate(ValidROC().bagit)


def test_rocrate_factory():

    logger.debug("Testing wrroc_paper: %s", ValidROC().wrroc_paper)
    roc = ROCrate.new_instance(ValidROC().wrroc_paper)
    assert isinstance(roc, ROCrateLocalFolder), "Should be a ROCrateLocalFolder"

    roc = ROCrate.new_instance(ValidROC().sort_and_change_archive)
    assert isinstance(roc, ROCrateLocalZip), "Should be a ROCrateLocalZip"

    roc = ROCrate.new_instance(ValidROC().sort_and_change_remote)
    assert isinstance(roc, ROCrateRemoteZip), "Should be a ROCrateRemoteZip"

    roc = ROCrate.new_instance(ValidROC().bagit)
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateLocalFolder), "Should be a ROCrateLocalFolder"
    assert isinstance(roc, ROCrateBagitLocalFolder), "Should be a ROCrateBagitLocalFolder"

    roc = ROCrate.new_instance(ValidROC().bagit_zip)
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateLocalZip), "Should be a ROCrateLocalZip"
    assert isinstance(roc, ROCrateBagitLocalZip), "Should be a ROCrateBagitLocalZip"

    roc = ROCrate.new_instance(ValidROC().bagit_remote_zip)
    assert isinstance(roc, ROCrateRemoteZip), "Should be a ROCrateRemoteZip"
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateBagitRemoteZip), "Should be a ROCrateBagitRemoteZip"


def test_rocrate_constructor():
    roc = ROCrate(ValidROC().wrroc_paper)
    assert isinstance(roc, ROCrateLocalFolder), "Should be a ROCrateLocalFolder"

    roc = ROCrate(ValidROC().sort_and_change_archive)
    assert isinstance(roc, ROCrateLocalZip), "Should be a ROCrateLocalZip"

    roc = ROCrate(ValidROC().sort_and_change_remote)
    assert isinstance(roc, ROCrateRemoteZip), "Should be a ROCrateRemoteZip"

    roc = ROCrate(ValidROC().bagit)
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateLocalFolder), "Should be a ROCrateLocalFolder"
    assert isinstance(roc, ROCrateBagitLocalFolder), "Should be a ROCrateBagitLocalFolder"

    roc = ROCrate(ValidROC().bagit_zip)
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateLocalZip), "Should be a ROCrateLocalZip"
    assert isinstance(roc, ROCrateBagitLocalZip), "Should be a ROCrateBagitLocalZip"


def test_parse_path():
    roc = ROCrate.new_instance(ValidROC().bagit_zip)
    assert isinstance(roc, ROCrateBagitLocalZip)

    logger.debug("Testing bagit_zip: %s", ValidROC().bagit_zip)

    # test parse_path for normal file
    path = Path("file.txt")
    parsed_path = roc.__parse_path__(path)
    logger.debug(f"Parsed path: {parsed_path}")
    assert parsed_path == Path("data/file.txt"), "Parsed path should be data/file.txt"

    # test parse_path for bagit wrapped file
    path = Path("ro-crate-metadata.json")
    parsed_path = roc.__parse_path__(path)
    logger.debug(f"Parsed path: {parsed_path}")
    assert parsed_path == Path("data/ro-crate-metadata.json"), "Parsed path should be data/ro-crate-metadata.json"

    # test parse_path for an explicit data/ path
    path = Path("data/file.txt")
    parsed_path = roc.__parse_path__(path)
    logger.debug(f"Parsed path: {parsed_path}")
    assert parsed_path == Path("data/file.txt"), "Parsed path should be data/file.txt"


def test_local_folder_with_relative_root():
    # set relative root path
    relative_root_path = "data"
    # create ROCrateBagitLocalFolder with relative root path
    roc = ROCrateLocalFolder(ValidROC().bagit, relative_root_path=relative_root_path)
    assert isinstance(roc, ROCrateLocalFolder)
    logger.debug("Testing bagit with relative root path: %s", relative_root_path)

    # test parse_path for normal file
    path = Path("file.txt")

    search_path, root_path = roc.__get_search_path__(path)
    logger.debug(f"Search path: {search_path}")
    logger.debug(f"Root path: {root_path}")
    assert root_path == roc.uri.as_path(), "Root path should be the ro-crate path"
    assert search_path == path, "Search path should be file.txt"

    parsed_path = roc.__parse_path__(path)
    logger.debug(f"Parsed path: {parsed_path}")
    assert parsed_path == ValidROC().bagit / relative_root_path / path, "Parsed path should be data/file.txt"

    # test has_file
    assert roc.has_file("data/ro-crate-metadata.json"), "Should have ro-crate-metadata.json file"

    # test get_file_content
    content = roc.get_file_content("data/ro-crate-metadata.json")
    assert isinstance(content, bytes), "Content should be bytes"


def test_remote_bagit_rocrate():

    bagit_crate = ValidROC().bagit_remote_zip
    roc = ROCrate.new_instance(bagit_crate)
    assert isinstance(roc, BagitROCrate), "Should be a BagItROCrate"
    assert isinstance(roc, ROCrateRemoteZip), "Should be a ROCrateRemoteZip"
    assert isinstance(roc, ROCrateBagitRemoteZip), "Should be a ROCrateBagitRemoteZip"

    # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    assert len(files) == 16, "Should have 16 files"

    # test is_file
    assert roc.has_file(metadata_file_descriptor), "Should be a file"
    # test file size
    size = roc.get_file_size(metadata_file_descriptor)
    assert size == 7321, "Size should be 7321"

    # test has directory
    assert roc.has_directory(Path("data")), "Should have data/ directory"
    assert roc.has_directory(Path("data/pics/")), "Should have data/pics/ directory"
    assert roc.has_directory(Path("data%20set/")), "Should have data%20set/ directory"
    assert roc.has_directory(Path("data set3/")), "Should have data set3/ directory"
    # test has file
    assert roc.has_file("pics/2018-06-11 12.56.14.jpg"), "Should have pics/2018-06-11%2012.56.14.jpg file"

    # test file availability
    img_2018 = roc.metadata.get_entity("pics/2018-06-11%2012.56.14.jpg")
    assert img_2018 is not None, "Should have pics/2018-06-11%2012.56.14.jpg entity"
    logger.debug(f"Image 2018 entity: {img_2018}")
    assert img_2018.is_available(), "pics/2018-06-11%2012.56.14.jpg entity should be available"


def test_valid_local_rocrate():
    roc = ROCrateLocalFolder(ValidROC().wrroc_paper)
    assert isinstance(roc, ROCrateLocalFolder)

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
    assert roc.size == 311817, "Size should be 311817"

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
#      ROCrateLocalFolder
def test_valid_local_folder_rocrate_with_relative_root():
    # set relative root path
    relative_root_path = "custom-relative-root"
    # create ROCrateLocalFolder with relative root path
    roc = ROCrateLocalFolder(ValidROC().rocrate_with_relative_root,
                             relative_root_path=relative_root_path)
    assert isinstance(roc, ROCrateLocalFolder)
    logger.debug("Testing bagit with relative root path: %s", relative_root_path)

    # inspect ro-crate-metadata.json to confirm correct relative root path
    assert roc.has_file("ro-crate-metadata.json"), "Should have ro-crate-metadata.json file"

    metadata_path = roc.get_file_content("ro-crate-metadata.json", binary_mode=False)
    logger.debug(f"ro-crate-metadata.json content: {metadata_path}")

    # test has_file
    assert roc.has_file("ro-crate-metadata.json"), "Should have ro-crate-metadata.json file"
    assert roc.has_file("pics/2017-06-11%252012.56.14.jpg"), \
        "Should have pics/2017-06-11%252012.56.14.jpg file"

    # test get_file_content
    content = roc.get_file_content("ro-crate-metadata.json")
    assert isinstance(content, bytes), "Content should be bytes"

    # check availability
    metadata = roc.metadata
    assert isinstance(metadata, ROCrateMetadata), "Metadata should be ROCrateMetadata"

    # check availability
    entity = metadata.get_entity("pics/2017-06-11%252012.56.14.jpg")
    assert entity is not None, "Entity should be available"
    logger.debug(f"Entity: {entity}")
    assert entity.is_available(), "Entity should be available"


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
#      ROCrate Local Bagit Zip
################################

def test_paths_valid_bagit_rocrate():
    roc = ROCrate(ValidROC().bagit_zip)
    assert isinstance(roc, ROCrateLocalZip)

    # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    assert len(files) == 16, "Should have 16 files"

    # check file paths
    # assert roc.has_file(Path("ro-crate-metadata.json")), "Should have ro-crate-metadata.json file"
    # # assert roc.has_file(Path("bagit.txt")), "Should have bagit.txt file"
    # # assert roc.has_file(Path("data/ro-crate-metadata.json")), "Should have data/ro-crate-metadata.json file"
    # assert roc.has_file(Path("pics/2017-06-11%2012.56.14.jpg")
    #                     ), "Should have data/pics/2017-06-11 12.56.14.jpg file"

    assert roc.has_directory(Path("data")), "Should have data/ directory"
    assert roc.has_directory(Path("data/pics/")), "Should have data/pics/ directory"
    assert roc.has_directory(Path("data%20set/")), "Should have data%20set/ directory"

    assert roc.has_directory(Path("data set3")), "Should have data set3/ directory"
    assert roc.has_directory(Path("data set3/")), "Should have data set3/ directory"

    assert roc.has_file("pics/2018-06-11 12.56.14.jpg"), "Should have pics/2018-06-11%2012.56.14.jpg file"

    dataset3 = roc.metadata.get_entity("data set3/")
    assert dataset3 is not None, "Should have data set3/ entity"
    logger.debug(f"Dataset3 entity: {dataset3}")
    assert dataset3.is_dataset(), "data set3/ entity should be a Dataset"
    assert dataset3.is_available(), "data set3/ entity should be available"

    img_2018 = roc.metadata.get_entity("pics/2018-06-11%2012.56.14.jpg")
    assert img_2018 is not None, "Should have pics/2018-06-11%2012.56.14.jpg entity"
    logger.debug(f"Image 2018 entity: {img_2018}")
    assert img_2018.is_available(), "pics/2018-06-11%2012.56.14.jpg entity should be available"

    img_2017 = roc.metadata.get_entity("pics/2017-06-11%252012.56.14.jpg")
    assert img_2017 is not None, "Should have pics/2017-06-11%252012.56.14.jpg entity"
    logger.debug(f"Image 2017 entity: {img_2017}")
    assert img_2017.is_available(), "pics/2017-06-11%252012.56.14.jpg entity should be available"


def test_valid_bagit_zip_rocrate():
    roc = ROCrate(ValidROC().bagit_zip)
    assert isinstance(roc, ROCrateLocalZip)

    # test list files
    files = roc.list_files()
    logger.debug(f"Files: {files}")
    # assert len(files) == 11, "Should have 11 files"

    # test is_file
    assert roc.has_file(metadata_file_descriptor), "Should be a file"

    # test file size
    size = roc.get_file_size(metadata_file_descriptor)
    assert size == 7321, "Size should be 7321"

    # test crate size
    assert roc.size == 4055, "Size should be 4055"

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
    assert root_data_entity.name == "My Pictures", "Name should be sort_and_change"

    # test subEntity mainEntity
    # main_entity = root_data_entity.get_property("mainEntity")
    # logger.error(f"Main entity: {main_entity}")
    # assert isinstance(main_entity, ROCrateEntity), "Entity should be ROCrateEntity"
    # assert main_entity.id == "sort-and-change-case.ga", "Id should be main-entity"
    # assert "ComputationalWorkflow" in main_entity.type, "Type should be ComputationalWorkflow"

    # check metadata consistency
    # assert main_entity.metadata == metadata, "Metadata should be the same"
    # assert main_entity.metadata == roc.metadata, "Metadata should be the same"

    # check availability of 'pics/2017-06-11%2012.56.14.jpg'
    # entity = metadata.get_entity("pics/2017-06-11%2012.56.14.jpg")
    # assert entity.is_available(), "Entity should be available"

    # assert roc.has_directory("data%20set/"), "Should have data%20set/ directory"


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


def test_entity_path_from_identifier():
    rocrate_path = InvalidDataEntity().data_entity_path
    logger.debug(f"RO-Crate path: {rocrate_path}")

    # Test quoted entity id which exists within the ro-crate
    quoted_entity_id = "pics/2017-06-11%2012.56.14.jpg"
    path = ROCrateEntity.get_path_from_identifier(quoted_entity_id, rocrate_path=rocrate_path)
    logger.debug(f"Quoted Entity Path: {path}")
    assert str(path) == f"{rocrate_path}/pics/2017-06-11%2012.56.14.jpg", \
        "Path should be pics/2017-06-11%2012.56.14.jpg"

    # Test quoted entity id which does not exist within the ro-crate
    quoted_entity_id = "pics/2018-06-11%2012.56.14.jpg"
    path = ROCrateEntity.get_path_from_identifier(
        quoted_entity_id, rocrate_path=rocrate_path, decode=True)
    logger.debug(f"Quoted Entity Path: {path}")
    assert str(path) == f"{rocrate_path}/pics/2018-06-11 12.56.14.jpg", \
        "Path should be pics/2018-06-11 12.56.14.jpg"

    # Test unquoted entity id which exists within the ro-crate
    unquoted_entity_id = "pics/2017-06-11 12.56.14.jpg"
    path = ROCrateEntity.get_path_from_identifier(unquoted_entity_id, rocrate_path=rocrate_path)
    logger.debug(f"Unquoted Entity Path: {path}")
    assert str(path) == f"{rocrate_path}/pics/2017-06-11 12.56.14.jpg", \
        "Path should be pics/2017-06-11 12.56.14.jpg"
