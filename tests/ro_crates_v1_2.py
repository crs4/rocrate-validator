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


BASE_PATH = CRATES_DATA_PATH / "rocrate-1.2"


class MetadataDocument:

    METADATA_DOCUMENT_CRATES_PATH = BASE_PATH / "1_metadata_document"

    @property
    def invalid_context_reference(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "context_reference" / "invalid"

    @property
    def valid_context_reference(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "context_reference" / "valid"

    @property
    def not_referenced_contextual_entity(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "referenced_contextual_entities" / "invalid"

    @property
    def valid_referenced_contextual_entity(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "referenced_contextual_entities" / "valid"

    @property
    def described_contextual_entity(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "described_contextual_entities" / "valid"

    @property
    def not_described_contextual_entity(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "described_contextual_entities" / "invalid"

    @property
    def valid_no_parent_traversal(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "no_parent_traversal" / "valid"

    @property
    def invalid_no_parent_traversal(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "no_parent_traversal" / "invalid"

    @property
    def valid_utf8_identifiers(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "utf8_identifiers" / "valid"

    @property
    def invalid_utf8_identifiers(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "utf8_identifiers" / "invalid"

    @property
    def valid_named_entity_id_format(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "named_entity_id_format" / "valid"

    @property
    def invalid_named_entity_id_format(self) -> Path:
        return self.METADATA_DOCUMENT_CRATES_PATH / "named_entity_id_format" / "invalid"


class MetadataDocumentFormat:

    METADATA_DOCUMENT_FORMAT_CRATES_PATH = MetadataDocument.METADATA_DOCUMENT_CRATES_PATH / "format"

    @property
    def not_compacted(self) -> Path:
        return self.METADATA_DOCUMENT_FORMAT_CRATES_PATH / "compacted"

    @property
    def not_flattened(self) -> Path:
        return self.METADATA_DOCUMENT_FORMAT_CRATES_PATH / "flattened"

    @property
    def not_jsonld(self) -> Path:
        return self.METADATA_DOCUMENT_FORMAT_CRATES_PATH / "jsonld"

    @property
    def not_utf8(self) -> Path:
        return self.METADATA_DOCUMENT_FORMAT_CRATES_PATH / "utf8"


class AttachedROCrates:

    ATTACHED_ROCRATES_CRATES_PATH = BASE_PATH / "2_attached_rocrates"

    @property
    def valid_preview_not_in_hasPart(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "attached-preview-not-in-hasPart" / "valid"

    @property
    def invalid_preview_not_in_hasPart(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "attached-preview-not-in-hasPart" / "invalid"

    @property
    def valid_non_relative_root_entity_id(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "non-relative-root-identifier" / "valid"

    @property
    def invalid_non_relative_root_entity_id(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "non-relative-root-identifier" / "invalid"

    @property
    def valid_relative_root_entity_id(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "relative-root-identifier" / "valid"

    @property
    def invalid_relative_root_entity_id(self) -> Path:
        return self.ATTACHED_ROCRATES_CRATES_PATH / "relative-root-identifier" / "invalid"


class DetachedROCrates:

    DETACHED_ROCRATES_CRATES_PATH = BASE_PATH / "3_detached_rocrates"

    __remote_sha__ = "1a54cc4c0152575357d937982de3e2567ab4a0f8"

    @property
    def valid_local_descriptor_filename(self) -> Path:
        return self.DETACHED_ROCRATES_CRATES_PATH / "naming-convention" / "local-descriptor" / "valid"

    @property
    def invalid_local_descriptor_filename(self) -> Path:
        return self.DETACHED_ROCRATES_CRATES_PATH / "naming-convention" / "local-descriptor" / "invalid"

    @property
    def valid_root_data_entity_identifier_when_online_available(self) -> Path:
        return self.DETACHED_ROCRATES_CRATES_PATH / "root-data-entity-identifier" / "online-available" / "valid"

    @property
    def invalid_root_data_entity_identifier_when_online_available(self) -> Path:
        return f"https://bitbucket.org/kikkomep/ro-crates/raw/{self.__remote_sha__}"\
            "/online-available/invalid/basic-ro-crate-metadata.json"

    @property
    def valid_web_data_entity(self) -> Path:
        return f"https://bitbucket.org/kikkomep/ro-crates/raw/{self.__remote_sha__}"\
            "/online-available/valid/basic-ro-crate-metadata.json"

    @property
    def invalid_web_data_entity(self) -> Path:
        return f"https://bitbucket.org/kikkomep/ro-crates/raw/{self.__remote_sha__}"\
            "/online-available/invalid/basic-ro-crate-metadata.json"


class MetadataEntities:

    METADATA_ENTITIES_CRATES_PATH = BASE_PATH / "5_metadata_entities"

    @property
    def valid_recommended_schema_type(self) -> Path:
        return self.METADATA_ENTITIES_CRATES_PATH / "recommended_schema_type" / "valid"

    @property
    def invalid_recommended_schema_type(self) -> Path:
        return self.METADATA_ENTITIES_CRATES_PATH / "recommended_schema_type" / "invalid"

    @property
    def valid_recommended_name(self) -> Path:
        return self.METADATA_ENTITIES_CRATES_PATH / "recommended_name" / "valid"

    @property
    def invalid_recommended_name(self) -> Path:
        return self.METADATA_ENTITIES_CRATES_PATH / "recommended_name" / "invalid"


class MetadataDescriptor:

    METADATA_DESCRIPTOR_CRATES_PATH = BASE_PATH / "6_metadata_descriptor"

    @property
    def valid_single_value_conformsTo(self) -> Path:
        return self.METADATA_DESCRIPTOR_CRATES_PATH / "recommended_conformsTo" / "single_value" / "valid"

    @property
    def invalid_single_value_conformsTo(self) -> Path:
        return self.METADATA_DESCRIPTOR_CRATES_PATH / "recommended_conformsTo" / "single_value" / "invalid"

    @property
    def valid_recommended_prefix_conformsTo(self) -> Path:
        return self.METADATA_DESCRIPTOR_CRATES_PATH / "recommended_conformsTo" / "recommended_prefix" / "valid"

    @property
    def invalid_recommended_prefix_conformsTo(self) -> Path:
        return self.METADATA_DESCRIPTOR_CRATES_PATH / "recommended_conformsTo" / "recommended_prefix" / "invalid"


class RootDataEntity:

    ROOT_DATA_ENTITY_CRATES_PATH = BASE_PATH / "7_root_data_entity"

    @property
    def valid_required_datePublished(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_datePublished" / "valid"

    @property
    def invalid_required_datePublished(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_datePublished" / "invalid"

    @property
    def valid_required_downloadable_citeAs(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_downloadable_citeas" / "valid"

    @property
    def invalid_required_downloadable_citeAs(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_downloadable_citeas" / "invalid"

    @property
    def valid_recommended_citeAs_for_resolvable_id(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_citeas_for_resolvable_id" / "valid"

    @property
    def invalid_recommended_citeAs_for_resolvable_id(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_citeas_for_resolvable_id" / "invalid"

    @property
    def valid_additional_conformsTo_reference(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "additional_conformsTo" / "valid"

    @property
    def invalid_additional_conformsTo_reference(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "additional_conformsTo" / "invalid"

    @property
    def missing_root(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root" / "invalid"

    @property
    def invalid_root_type(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "invalid_root_type" / "invalid"

    @property
    def invalid_root_value(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "invalid_root_value" / "invalid"

    @property
    def recommended_root_value(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_root_value" / "valid"

    @property
    def invalid_root_date(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "invalid_root_date" / "invalid"

    @property
    def invalid_recommended_root_date(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "invalid_recommended_root_date" / "invalid"

    @property
    def missing_root_name(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root_name" / "invalid"

    @property
    def missing_root_description(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root_description" / "invalid"

    @property
    def missing_root_license(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root_license" / "invalid"

    @property
    def missing_root_license_name(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root_license_name" / "invalid"

    @property
    def missing_root_license_description(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "missing_root_license_description" / "invalid"

    @property
    def valid_referenced_generic_data_entities(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "valid_referenced_generic_data_entities" / "valid"

    @property
    def valid_recommended_identifier_resolution(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_resolution" / "valid"

    @property
    def invalid_recommended_identifier_resolution(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_resolution" / "invalid"

    @property
    def valid_recommended_publisher(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_publisher" / "valid"

    @property
    def invalid_recommended_publisher(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_publisher" / "invalid"

    @property
    def valid_recommended_funding(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_funding" / "valid"

    @property
    def invalid_recommended_funding_no_funder(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_funding" / "invalid_no_funder"

    @property
    def invalid_recommended_funding_non_org_funder(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_funding" / "invalid_non_org_funder"

    @property
    def invalid_recommended_funding_no_project_funder(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_funding" / "invalid_no_project_funder"

    # R1: datePublished day precision (SHOULD)
    @property
    def valid_recommended_datePublished_day_precision(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_datepublished_day_precision" / "valid"

    @property
    def invalid_recommended_datePublished_day_precision(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_datepublished_day_precision" / "invalid"

    # R2: hasPart MUST reference all Data Entities
    @property
    def valid_required_hasPart_all_data_entities(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_haspart_all_data_entities" / "valid"

    @property
    def invalid_required_hasPart_all_data_entities(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "required_haspart_all_data_entities" / "invalid"

    @property
    def invalid_hasPart_workflow_not_in_haspart(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH \
            / "required_haspart_all_data_entities" / "invalid_workflow_not_in_haspart"

    @property
    def invalid_hasPart_web_entity_not_in_haspart(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH \
            / "required_haspart_all_data_entities" / "invalid_web_entity_not_in_haspart"

    @property
    def invalid_hasPart_dataset_not_in_haspart(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH \
            / "required_haspart_all_data_entities" / "invalid_dataset_not_in_haspart"

    # R3: identifier SHOULD be present if PID exists (SHOULD)
    @property
    def valid_recommended_identifier_if_pid(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_if_pid" / "valid"

    @property
    def invalid_recommended_identifier_if_pid(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_if_pid" / "invalid"

    # R4: identifier SHOULD use PropertyValue approach (SHOULD)
    @property
    def valid_recommended_identifier_propertyvalue(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_propertyvalue" / "valid"

    @property
    def invalid_recommended_identifier_propertyvalue(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_identifier_propertyvalue" / "invalid"

    # R5: conformsTo SHOULD be present if profiles exist (SHOULD)
    @property
    def valid_recommended_conformsto_if_profiles(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_conformsto_if_profiles" / "valid"

    @property
    def invalid_recommended_conformsto_if_profiles(self) -> Path:
        return self.ROOT_DATA_ENTITY_CRATES_PATH / "recommended_conformsto_if_profiles" / "invalid"


class DataEntities:

    DATA_ENTITIES_CRATES_PATH = BASE_PATH / "8_metadata_dataEntities"

    @property
    def valid_local_entity_reference(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "local_entity_reference" / "valid"

    @property
    def invalid_local_entity_reference(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "local_entity_reference" / "invalid"

    @property
    def valid_detached_rocrate_dataEntities(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "detached_rocrate_dataEntities" / "valid"

    @property
    def invalid_detached_rocrate_dataEntities(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "detached_rocrate_dataEntities" / "invalid"

    @property
    def valid_recommended_properties(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_properties" / "valid"

    @property
    def invalid_recommended_properties(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_properties" / "invalid"

    @property
    def valid_recommended_encoding_format(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_encoding_format" / "valid"

    @property
    def invalid_recommended_encoding_format(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_encoding_format" / "invalid"

    @property
    def valid_web_entity_downloadable(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_entity_downloadable" / "valid"

    @property
    def invalid_web_entity_splash_page(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_entity_downloadable" / "invalid"

    @property
    def valid_recommended_content_url(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_entity_content_url" / "valid"

    @property
    def invalid_recommended_content_url(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_entity_content_url" / "invalid"

    @property
    def valid_recommended_distribution(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_dataset_distribution" / "valid"

    @property
    def invalid_recommended_distribution(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_dataset_distribution" / "invalid"

    @property
    def valid_web_directory_distribution(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_directory_distribution" / "valid"

    @property
    def invalid_web_directory_distribution(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "web_directory_distribution" / "invalid"

    @property
    def valid_missing_file_local_path(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "missing_file_local_path" / "valid"

    @property
    def invalid_missing_file_local_path(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "missing_file_local_path" / "invalid"

    @property
    def valid_data_entity_license_divergence(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "data_entity_license" / "valid"

    @property
    def invalid_data_entity_license_divergence(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "data_entity_license" / "invalid"

    @property
    def valid_recommended_contentSize(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_contentSize" / "valid"

    @property
    def invalid_recommended_contentSize(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_contentSize" / "invalid"

    @property
    def valid_recommended_conformsto(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_conformsto" / "valid"

    @property
    def invalid_recommended_conformsto(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_conformsto" / "invalid"

    @property
    def valid_recommended_sdDatePublished(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_sdDatePublished" / "valid"

    @property
    def invalid_recommended_sdDatePublished(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "recommended_sdDatePublished" / "invalid"

    # 4.3 Dataset (Directory) Data Entity — trailing slash
    @property
    def valid_recommended_dataset_trailing_slash(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "dataset_trailing_slash" / "valid"

    @property
    def invalid_recommended_dataset_trailing_slash(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "dataset_trailing_slash" / "invalid"

    # 4.3 Dataset (Directory) Data Entity — hasPart
    @property
    def valid_recommended_dataset_has_part(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "dataset_has_part" / "valid"

    @property
    def invalid_recommended_dataset_has_part(self) -> Path:
        return self.DATA_ENTITIES_CRATES_PATH / "dataset_has_part" / "invalid"


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


class ContextualEntities:

    CONTEXTUAL_ENTITIES_CRATES_PATH = BASE_PATH / "10_metadata_contextualEntities"

    # --- License entity: SHOULD be typed as CreativeWork ---
    @property
    def valid_license_entity(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "license_entity" / "valid"

    @property
    def invalid_license_entity_no_type(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "license_entity" / "invalid_no_type"

    @property
    def invalid_license_entity_no_url(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "license_entity" / "invalid_no_url"

    @property
    def invalid_license_entity_no_name(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "license_entity" / "invalid_no_name"

    @property
    def invalid_license_entity_no_description(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "license_entity" / "invalid_no_description"

    # --- Organization entity: SHOULD have ROR @id and contactPoint ---
    @property
    def valid_organization_entity(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "organization_entity" / "valid"

    @property
    def invalid_organization_no_ror_id(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "organization_entity" / "invalid_no_ror_id"

    @property
    def invalid_organization_no_contactpoint(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "organization_entity" / "invalid_org_no_contactpoint"

    @property
    def invalid_organization_contactpoint_no_entity(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH \
            / "organization_entity" / "invalid_contactpoint_no_contactpoint_entity"

    @property
    def invalid_no_author_publisher_contactpoint(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "organization_entity" / "invalid_no_author_publisher_contactpoint"

    # --- Person entity: SHOULD have ORCID @id and valid affiliation ---
    @property
    def valid_person_entity(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "person_entity" / "valid"

    @property
    def invalid_person_no_orcid(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "person_entity" / "invalid_no_orcid"

    @property
    def invalid_person_affiliation_not_org(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "person_entity" / "invalid_affiliation_not_org"

    # --- Any Contextual Entity: SHOULD have absolute URI or '#'-prefixed @id ---
    @property
    def valid_contextual_entity_id_format(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "contextual_entity_id_format" / "valid"

    @property
    def invalid_contextual_entity_bare_contactpoint(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "contextual_entity_id_format" / "invalid_bare_contactpoint"

    @property
    def invalid_contextual_entity_bare_propertyvalue(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "contextual_entity_id_format" / "invalid_bare_propertyvalue"

    # --- SoftwareApplication / ComputerLanguage: MUST have name, url, version (5.7) ---
    @property
    def valid_software_application(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "valid"

    @property
    def invalid_software_application_no_version(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "invalid_no_version"

    @property
    def invalid_software_application_no_name(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "invalid_no_name"

    @property
    def invalid_software_application_no_url(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "invalid_no_url"

    @property
    def valid_computer_language(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "valid_computer_language"

    @property
    def valid_computer_language_with_alternatename(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "software_application" / "valid_with_alternatename"

    # --- Encoding Format entity: MAY include `WebPageElement` when @id has a fragment (5.8) ---
    @property
    def valid_encoding_format_webpageelement(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "encoding_format" / "valid"

    @property
    def info_encoding_format_no_webpageelement(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "encoding_format" / "info_no_webpageelement"

    @property
    def encoding_format_no_fragment(self) -> Path:
        return self.CONTEXTUAL_ENTITIES_CRATES_PATH / "encoding_format" / "no_fragment"


class InvalidMultiProfileROC:

    @property
    def invalid_multi_profile_crate(self) -> Path:
        return INVALID_CRATES_DATA_PATH / "0_multi_profile_crate"


class ReferencedROCrates:

    REFERENCED_ROCRATES_CRATES_PATH = CRATES_DATA_PATH / "rocrate-1.2" / "9_referenced_rocrate"

    @property
    def valid(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "valid"

    @property
    def invalid_no_versionless_conformsto(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_no_versionless_conformsto"

    @property
    def invalid_root_conformsto_versionless(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_root_conformsto_versionless"

    @property
    def invalid_no_subjectof(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_no_subjectof"

    @property
    def invalid_md_encoding_format(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_md_encoding_format"

    @property
    def invalid_md_conformsto(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_md_conformsto"

    @property
    def invalid_md_about(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_md_about"

    @property
    def invalid_missing_sddatepublished(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "invalid_missing_sddatepublished"

    @property
    def valid_with_identifier(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "valid_with_identifier"

    @property
    def valid_with_relative_path(self) -> Path:
        return self.REFERENCED_ROCRATES_CRATES_PATH / "valid_with_relative_path"


class ValidROCrate12:

    base_path = VALID_CRATES_DATA_PATH

    @property
    def attached(self) -> Path:
        return self.base_path / "ro-crate-1.2-attached"

    @property
    def attached_absolute_root(self) -> Path:
        return self.base_path / "ro-crate-1.2-absolute-root"

    @property
    def detached(self) -> Path:
        return self.base_path / "detached" / "dataset-ro-crate-metadata.json"

    @property
    def detached_prefixed(self) -> Path:
        return self.base_path / "detached" / "test-ro-crate-metadata.json"


class InvalidROCrate12:

    base_path = INVALID_CRATES_DATA_PATH / "ro-crate-1.2"

    @property
    def invalid_context(self) -> Path:
        return self.base_path / "invalid-context"

    @property
    def invalid_date_published(self) -> Path:
        return self.base_path / "invalid-date-published"

    @property
    def detached_relative_entity(self) -> Path:
        return self.base_path / "detached-relative-entity" / "dataset-ro-crate-metadata.json"

    @property
    def detached_bad_filename(self) -> Path:
        return self.base_path / "detached-bad-filename" / "ro-crate-metadata.json"
