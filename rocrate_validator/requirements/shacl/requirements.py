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
from typing import Any, Optional, cast

from rdflib import RDF

from rocrate_validator.constants import VALIDATOR_NS
from rocrate_validator.models import (
    Profile,
    Requirement,
    RequirementCheck,
    RequirementLevel,
    RequirementLoader,
    ValidationContext,
)
from rocrate_validator.requirements.shacl.checks import SHACLCheck
from rocrate_validator.requirements.shacl.models import Shape, ShapesRegistry
from rocrate_validator.utils import log as logging

# set up logging
logger = logging.getLogger(__name__)


class SHACLRequirement(Requirement):
    def __init__(self, shape: Shape, profile: Profile, path: Path):
        self._shape = shape
        super().__init__(
            profile, shape.name or "", shape.description or "", path
        )
        # init checks
        self._checks = self.__init_checks__()
        # assign check IDs
        self.__reorder_checks__()

    def __reorder_checks__(self) -> None:
        for i, check in enumerate(self._checks):
            check.order_number = i

    def __init_checks__(self) -> list[RequirementCheck]:
        # check if the shape is not None before creating checks
        assert self.shape is not None, "The shape cannot be None"
        assert self.shape.node is not None, "The shape node cannot be None"
        # assign a check to each property of the shape
        checks: list[RequirementCheck] = []
        # check if the shape has nested properties
        has_properties = hasattr(self.shape, "properties") and len(cast("Any", self.shape).properties) > 0
        # create a check for the shape itself, hidden if the shape has nested properties
        checks.append(
            SHACLCheck(
                self,
                self.shape,
                name=f"Check {self.shape.name}" if has_properties else None,
                hidden=has_properties,
                root=True,
            )
        )
        # create a check for each property if the shape has nested properties
        if has_properties:
            for prop in cast("Any", self.shape).properties:
                logger.debug("Creating check for property %s %s", prop.name, prop.description)
                property_check = SHACLCheck(self, prop)
                logger.debug("Property check %s: %s", property_check.name, property_check.description)
                checks.append(property_check)

        return checks

    @property
    def shape(self) -> Shape:
        return self._shape

    @property
    def hidden(self) -> bool:
        return bool(
            self.shape.node is not None
            and (self.shape.node, RDF.type, VALIDATOR_NS.HiddenShape) in self.shape.graph
        )

    @classmethod
    def finalize(cls, context: ValidationContext) -> None:
        """ "
        Finalize the SHACL requirement by ensuring that a SHACL validation run is triggered for the target profile
        if it has no shapes of its own (e.g. an extension profile that purely inherits or only deactivates).

        SHACL is normally driven by the first execute_check of a check
        belonging to the target profile (see SHACLValidationContextManager).
        If the target has zero SHACL checks of its own (e.g. an extension
        profile that purely inherits or only deactivates), no pyshacl run
        is ever triggered and inherited shapes are never evaluated.
        Force one final run on the merged shapes graph in that case.
        """

        logger.debug("Starting %s requirement finalization for context %s", cls.__name__, context)

        # extract profiles and target profile from context
        profiles = context.profiles

        from rocrate_validator.requirements.shacl.checks import SHACLCheck  # noqa: PLC0415
        from rocrate_validator.requirements.shacl.validator import SHACLValidationContext  # noqa: PLC0415

        target = next((p for p in profiles if p.identifier == context.settings.profile_identifier), None)
        if target is None:
            return

        shacl_context = SHACLValidationContext.get_instance(context)
        # If pyshacl already ran for the target during the main loop there is
        # nothing to do.
        if shacl_context.get_validation_result(target) is not None:
            return

        # Pick any SHACLCheck across the loaded profiles to drive the run; the
        # check identity is only used for logging inside __do_execute_check__,
        # the actual validation is graph-wide.
        runner = next(
            (c for p in profiles for r in p.requirements for c in r.get_checks() if isinstance(c, SHACLCheck)),
            None,
        )
        if runner is None:
            return

        # Make sure the target's shapes (if any) are in the merged registry
        # and switch the current profile so violations are attributed under
        # the target profile in the report.
        shacl_context.__set_current_validation_profile__(target)
        shacl_context._current_validation_profile = target
        try:
            runner.__do_execute_check__(shacl_context)
        except Exception as e:
            if context.maybe_warn_offline_cache_miss(e):
                logger.debug(
                    "Forced SHACL run for zero-shape target profile %s skipped due to offline cache miss: %s",
                    target.identifier, e,
                )
            else:
                logger.warning("Forced SHACL run for zero-shape target profile %s failed: %s", target.identifier, e)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
        finally:
            shacl_context.__unset_current_validation_profile__()

        # do finalization logic here (empty for now)
        logger.debug("Completed %s requirement finalization for context %s", cls.__name__, context)


class SHACLRequirementLoader(RequirementLoader):
    def __init__(self, profile: Profile):
        super().__init__(profile)
        self._shape_registry = ShapesRegistry.get_instance(profile)
        # reset the shapes registry
        self._shape_registry.clear()  # should be removed

    @property
    def shapes_registry(self) -> ShapesRegistry:
        return self._shape_registry

    def load(
        self, profile: Profile, requirement_level: RequirementLevel, file_path: Path, publicID: Optional[str] = None
    ) -> list[Requirement]:
        assert file_path is not None, "The file path cannot be None"
        shapes: list[Shape] = self.shapes_registry.load_shapes(file_path, publicID)
        logger.debug("Loaded %s shapes: %s", len(shapes), shapes)
        requirements: list[Requirement] = [
            SHACLRequirement(shape, profile, file_path)
            for shape in shapes
            if shape is not None and shape.level >= requirement_level
        ]
        return requirements
