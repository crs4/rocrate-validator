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

from rocrate_validator.utils import log as logging
from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import (PyFunctionCheck, check,
                                                   requirement)

# set up logging
logger = logging.getLogger(__name__)


@requirement(name="Entity reachability")
class EntityReachabilityChecker(PyFunctionCheck):
    """
    Entities SHOULD be referenced from the Root Data Entity (directly or indirectly).
    """

    @check(name="Entity reachability from root")
    def check_reachability(self, context: ValidationContext) -> bool:
        try:
            graph = context.ro_crate.metadata.as_dict().get("@graph", [])
            ids = {e.get("@id") for e in graph if e.get("@id")}
            referenced = set()

            def collect_refs(value):
                if isinstance(value, dict):
                    if "@id" in value:
                        referenced.add(value["@id"])
                    for v in value.values():
                        collect_refs(v)
                elif isinstance(value, list):
                    for v in value:
                        collect_refs(v)

            for entity in graph:
                for key, value in entity.items():
                    if key in ("@id", "@type", "@context"):
                        continue
                    collect_refs(value)

            root_id = context.ro_crate.metadata.get_root_data_entity().id
            always_allowed = {context.ro_crate.metadata_descriptor_id, root_id}
            unreferenced = [i for i in ids if i not in referenced and i not in always_allowed]
            if unreferenced:
                context.result.add_issue(
                    f"Entities not referenced from the graph: {unreferenced}", self)
                return False
            return True
        except Exception as e:
            context.result.add_issue(
                f"Error checking entity reachability: {str(e)}", self)
            return False
