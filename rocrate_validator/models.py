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

from __future__ import annotations

import bisect
import enum
import inspect
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Collection
from dataclasses import asdict, dataclass
from functools import total_ordering
from pathlib import Path
from typing import Optional, Tuple, Union

from rdflib import RDF, RDFS, Graph, Namespace, URIRef

import rocrate_validator.log as logging
from rocrate_validator.constants import (DEFAULT_ONTOLOGY_FILE,
                                         DEFAULT_PROFILE_IDENTIFIER,
                                         DEFAULT_PROFILE_README_FILE,
                                         IGNORED_PROFILE_DIRECTORIES, PROF_NS,
                                         PROFILE_FILE_EXTENSIONS,
                                         PROFILE_SPECIFICATION_FILE,
                                         RDF_SERIALIZATION_FORMATS_TYPES,
                                         ROCRATE_METADATA_FILE, SCHEMA_ORG_NS,
                                         VALID_INFERENCE_OPTIONS_TYPES)
from rocrate_validator.errors import (DuplicateRequirementCheck,
                                      InvalidProfilePath, ProfileNotFound,
                                      ProfileSpecificationError,
                                      ProfileSpecificationNotFound,
                                      ROCrateMetadataNotFoundError)
from rocrate_validator.events import Event, EventType, Publisher
from rocrate_validator.rocrate import ROCrate
from rocrate_validator.utils import (URI, MapIndex, MultiIndexMap,
                                     get_profiles_path,
                                     get_requirement_name_from_file)

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

logger = logging.getLogger(__name__)

BaseTypes = Union[str, Path, bool, int, None]


@enum.unique
@total_ordering
class Severity(enum.Enum):
    """Enum ordering "strength" of conditions to be verified"""
    OPTIONAL = 0
    RECOMMENDED = 2
    REQUIRED = 4

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self.value < other.value
        else:
            raise TypeError(f"Comparison not supported between instances of {type(self)} and {type(other)}")

    @staticmethod
    def get(name: str) -> Severity:
        return getattr(Severity, name.upper())


@total_ordering
@dataclass
class RequirementLevel:
    name: str
    severity: Severity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementLevel):
            return False
        return self.name == other.name and self.severity == other.severity

    def __lt__(self, other: object) -> bool:
        # TODO: this ordering is not totally coherent, since for two objects a and b
        # with equal Severity but different names you would have
        #       not a < b, which implies a >= b
        #       and also a != b and not a > b, which is incoherent with a >= b
        if not isinstance(other, RequirementLevel):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.severity < other.severity

    def __hash__(self) -> int:
        return hash((self.name, self.severity))

    def __repr__(self) -> str:
        return f'RequirementLevel(name={self.name}, severity={self.severity})'

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.severity.value

    def __index__(self) -> int:
        return self.severity.value


class LevelCollection:
    """
    * The keywords MUST, MUST NOT, REQUIRED,
    * SHALL, SHALL NOT, SHOULD, SHOULD NOT,
    * RECOMMENDED, MAY, and OPTIONAL in this document
    * are to be interpreted as described in RFC 2119.
    """
    OPTIONAL = RequirementLevel('OPTIONAL', Severity.OPTIONAL)
    MAY = RequirementLevel('MAY', Severity.OPTIONAL)

    REQUIRED = RequirementLevel('REQUIRED', Severity.REQUIRED)
    SHOULD = RequirementLevel('SHOULD', Severity.RECOMMENDED)
    SHOULD_NOT = RequirementLevel('SHOULD_NOT', Severity.RECOMMENDED)
    RECOMMENDED = RequirementLevel('RECOMMENDED', Severity.RECOMMENDED)

    MUST = RequirementLevel('MUST', Severity.REQUIRED)
    MUST_NOT = RequirementLevel('MUST_NOT', Severity.REQUIRED)
    SHALL = RequirementLevel('SHALL', Severity.REQUIRED)
    SHALL_NOT = RequirementLevel('SHALL_NOT', Severity.REQUIRED)

    def __init__(self):
        raise NotImplementedError(f"{type(self)} can't be instantiated")

    @staticmethod
    def all() -> list[RequirementLevel]:
        return [level for name, level in inspect.getmembers(LevelCollection)
                if not inspect.isroutine(level)
                and not inspect.isdatadescriptor(level) and not name.startswith('__')]

    @staticmethod
    def get(name: str) -> RequirementLevel:
        try:
            return getattr(LevelCollection, name.upper())
        except AttributeError:
            raise ValueError(f"Invalid RequirementLevel: {name}")


@total_ordering
class Profile:

    # store the map of profiles: profile URI -> Profile instance
    __profiles_map: MultiIndexMap = \
        MultiIndexMap("uri", indexes=[
            MapIndex("name"), MapIndex("token", unique=False), MapIndex("identifier", unique=True)
        ])

    def __init__(self,
                 profiles_base_path: Path,
                 profile_path: Path,
                 requirements: Optional[list[Requirement]] = None,
                 identifier: str = None,
                 publicID: Optional[str] = None,
                 severity: Severity = Severity.REQUIRED):
        self._identifier: Optional[str] = identifier
        self._profiles_base_path = profiles_base_path
        self._profile_path = profile_path
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._requirements: list[Requirement] = requirements if requirements is not None else []
        self._publicID = publicID
        self._severity = severity

        # init property to store the RDF node which is the root of the profile specification graph
        self._profile_node = None

        # init property to store the RDF graph of the profile specification
        self._profile_specification_graph = None

        # check if the profile specification file exists
        spec_file = self.profile_specification_file_path
        if not spec_file or not spec_file.exists():
            raise ProfileSpecificationNotFound(spec_file)
        # load the profile specification expressed using the Profiles Vocabulary
        profile = Graph()
        profile.parse(str(spec_file), format="turtle")
        # check that the specification Graph hosts only one profile
        profiles = list(profile.subjects(predicate=RDF.type, object=PROF_NS.Profile))
        if len(profiles) == 1:
            self._profile_node = profiles[0]
            self._profile_specification_graph = profile
            # initialize the token and version
            self._token, self._version = self.__init_token_version__()
            # add the profile to the profiles map
            self.__profiles_map.add(
                self._profile_node.toPython(),
                self, token=self.token,
                name=self.name, identifier=self.identifier
            )  # add the profile to the profiles map
        else:
            raise ProfileSpecificationError(
                message=f"Profile specification file {spec_file} must contain exactly one profile")

    def __get_specification_property__(
            self, property: str, namespace: Namespace,
            pop_first: bool = True, as_Python_object: bool = True) -> Union[str, list[Union[str, URIRef]]]:
        assert self._profile_specification_graph is not None, "Profile specification graph not loaded"
        values = list(self._profile_specification_graph.objects(self._profile_node, namespace[property]))
        if values and as_Python_object:
            values = [v.toPython() for v in values]
        if pop_first:
            return values[0] if values and len(values) >= 1 else None
        return values

    @property
    def path(self):
        return self._profile_path

    @property
    def identifier(self) -> str:
        if not self._identifier:
            version = self.version
            self._identifier = f"{self.token}-{version}" if version else self.token
        return self._identifier

    @property
    def name(self):
        return self.label or f"Profile {self.uri}"

    @property
    def profile_node(self):
        return self._profile_node

    @property
    def token(self):
        return self._token

    @property
    def uri(self):
        return self._profile_node.toPython()

    @property
    def label(self):
        return self.__get_specification_property__("label", RDFS)

    @property
    def comment(self):
        return self.__get_specification_property__("comment", RDFS)

    @property
    def version(self):
        return self._version

    @property
    def is_profile_of(self) -> list[str]:
        return self.__get_specification_property__("isProfileOf", PROF_NS, pop_first=False)

    @property
    def is_transitive_profile_of(self) -> list[str]:
        return self.__get_specification_property__("isTransitiveProfileOf", PROF_NS, pop_first=False)

    @property
    def parents(self) -> list[Profile]:
        return [self.__profiles_map.get_by_key(_) for _ in self.is_profile_of]

    @property
    def siblings(self) -> list[Profile]:
        return self.get_sibling_profiles(self)

    @property
    def readme_file_path(self) -> Path:
        return self.path / DEFAULT_PROFILE_README_FILE

    @property
    def profile_specification_file_path(self) -> Path:
        return self.path / PROFILE_SPECIFICATION_FILE

    @property
    def publicID(self) -> Optional[str]:
        return self._publicID

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    def description(self) -> str:
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with open(self.readme_file_path, "r") as f:
                    self._description = f.read()
            else:
                self._description = self.comment
        return self._description

    @property
    def requirements(self) -> list[Requirement]:
        if not self._requirements:
            self._requirements = \
                RequirementLoader.load_requirements(self, severity=self.severity)
        return self._requirements

    def get_requirements(
            self, severity: Severity = Severity.REQUIRED,
            exact_match: bool = False) -> list[Requirement]:
        return [requirement for requirement in self.requirements
                if (not exact_match and
                    (not requirement.severity_from_path or requirement.severity_from_path >= severity)) or
                (exact_match and requirement.severity_from_path == severity)]

    def get_requirement(self, name: str) -> Optional[Requirement]:
        for requirement in self.requirements:
            if requirement.name == name:
                return requirement
        return None

    def get_requirement_check(self, check_name: str) -> Optional[RequirementCheck]:
        """
        Get the requirement check with the given name
        """
        for requirement in self.requirements:
            check = requirement.get_check(check_name)
            if check:
                return check
        return None

    @classmethod
    def __get_nested_profiles__(cls, source: str) -> list[str]:
        result = []
        visited = []
        queue = [source]
        while len(queue) > 0:
            p = queue.pop()
            if p not in visited:
                visited.append(p)
                profile = cls.__profiles_map.get_by_key(p)
                inherited_profiles = profile.is_profile_of
                if inherited_profiles:
                    for p in sorted(inherited_profiles, reverse=True):
                        if p not in visited:
                            queue.append(p)
                        if p not in result:
                            result.insert(0, p)
        return result

    @property
    def inherited_profiles(self) -> list[Profile]:
        inherited_profiles = self.is_transitive_profile_of
        if not inherited_profiles or len(inherited_profiles) == 0:
            inherited_profiles = Profile.__get_nested_profiles__(self.uri)
        profile_keys = self.__profiles_map.keys
        return [self.__profiles_map.get_by_key(_) for _ in inherited_profiles if _ in profile_keys]

    def add_requirement(self, requirement: Requirement):
        self._requirements.append(requirement)

    def remove_requirement(self, requirement: Requirement):
        self._requirements.remove(requirement)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Profile) \
            and self.identifier == other.identifier \
            and self.path == other.path

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Profile):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        # If one profile is a parent of the other, the parent is greater
        if other in self.parents:
            return False
        # If the number of inherited profiles is the same, compare based on identifier
        return self.identifier < other.identifier

    def __hash__(self) -> int:
        return hash((self.identifier, self.path))

    def __repr__(self) -> str:
        return (
            f'Profile(identifier={self.identifier}, '
            f'name={self.name}, '
            f'path={self.path}, ' if self.path else ''
            f'requirements={self.requirements})'
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.identifier})"

    @staticmethod
    def __extract_version_from_token__(token: str) -> Optional[str]:
        if not token:
            return None
        pattern = r"\Wv?(\d+(\.\d+(\.\d+)?)?)"
        matches = re.findall(pattern, token)
        if matches:
            return matches[-1][0]
        return None

    def __get_consistent_version__(self, candidate_token: str) -> str:
        candidates = {_ for _ in [
            self.__get_specification_property__("version", SCHEMA_ORG_NS),
            self.__extract_version_from_token__(candidate_token),
            self.__extract_version_from_token__(str(self.path.relative_to(self._profiles_base_path))),
            self.__extract_version_from_token__(str(self.uri))
        ] if _ is not None}
        if len(candidates) > 1:
            raise ProfileSpecificationError(f"Inconsistent versions found: {candidates}")
        logger.debug("Candidate versions: %s", candidates)
        return candidates.pop() if len(candidates) == 1 else None

    def __extract_token_from_path__(self) -> str:
        base_path = str(self._profiles_base_path.absolute())
        identifier = str(self.path.absolute())
        # Check if the path starts with the base path
        if not identifier.startswith(base_path):
            raise ValueError("Path does not start with the base path")
        # Remove the base path from the identifier
        identifier = identifier.replace(f"{base_path}/", "")
        # Replace slashes with hyphens
        identifier = identifier.replace('/', '-')
        return identifier

    def __init_token_version__(self) -> Tuple[str, str, str]:
        # try to extract the token from the specs or the path
        candidate_token = self.__get_specification_property__("hasToken", PROF_NS)
        if not candidate_token:
            candidate_token = self.__extract_token_from_path__()
        logger.debug("Candidate token: %s", candidate_token)

        # try to extract the version from the specs or the token or the path or the URI
        version = self.__get_consistent_version__(candidate_token)
        logger.debug("Extracted version: %s", version)

        # remove the version from the token if it is present
        if version:
            candidate_token = re.sub(r"[\W|_]+" + re.escape(version) + r"$", "", candidate_token)

        # return the candidate token and version
        return candidate_token, version

    @classmethod
    def load(cls, profiles_base_path: str,
             profile_path: Union[str, Path],
             publicID: Optional[str] = None,
             severity:  Severity = Severity.REQUIRED) -> Profile:
        # if the path is a string, convert it to a Path
        if isinstance(profile_path, str):
            profile_path = Path(profile_path)
        # check if the path is a directory
        if not profile_path.is_dir():
            raise InvalidProfilePath(profile_path)
        # create a new profile
        profile = Profile(profiles_base_path=profiles_base_path,
                          profile_path=profile_path, publicID=publicID, severity=severity)
        logger.debug("Loaded profile: %s", profile)
        return profile

    @classmethod
    def load_profiles(cls, profiles_path: Union[str, Path],
                      publicID: Optional[str] = None,
                      severity:  Severity = Severity.REQUIRED,
                      allow_requirement_check_override: bool = True) -> list[Profile]:
        # if the path is a string, convert it to a Path
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        # check if the path is a directory
        if not profiles_path.is_dir():
            raise InvalidProfilePath(profiles_path)
        # initialize the profiles list
        profiles = []
        # calculate the list of profiles path as the subdirectories of the profiles path
        # where the profile specification file is present
        profile_paths = [p.parent for p in profiles_path.rglob('*.*') if p.name == PROFILE_SPECIFICATION_FILE]

        # iterate through the directories and load the profiles
        for profile_path in profile_paths:
            logger.debug("Checking profile path: %s %s %r", profile_path,
                         profile_path.is_dir(), IGNORED_PROFILE_DIRECTORIES)
            if profile_path.is_dir() and profile_path not in IGNORED_PROFILE_DIRECTORIES:
                profile = Profile.load(profiles_path, profile_path, publicID=publicID, severity=severity)
                profiles.append(profile)

        # order profiles based on the inheritance hierarchy,
        # from the most specific to the most general
        # (i.e., from the leaves of the graph to the root)
        profiles = sorted(profiles, reverse=True)

        # Check for overridden checks
        if not allow_requirement_check_override:
            # Navigate the profiles to check for overridden checks.
            # If the override is not enabled in the settings raise an error.
            profiles_checks = set()
            # Search for duplicated checks in the profiles
            for profile in profiles:
                profile_checks = [_ for r in profile.get_requirements() for _ in r.get_checks()]
                for check in profile_checks:
                    # If the check is already present in the list of checks,
                    # raise an error if the override is not enabled.
                    if check in profiles_checks:
                        raise DuplicateRequirementCheck(check.name, profile.identifier)
                    # Add the check to the list of checks
                    profiles_checks.add(check)

        #  order profiles according to the number of profiles they depend on:
        # i.e, first the profiles that do not depend on any other profile
        # then the profiles that depend on the previous ones, and so on
        return sorted(profiles, key=lambda x: f"{len(x.inherited_profiles)}_{x.identifier}")

    @classmethod
    def get_by_identifier(cls, identifier: str) -> Profile:
        return cls.__profiles_map.get_by_index("identifier", identifier)

    @classmethod
    def get_by_uri(cls, uri: str) -> Profile:
        return cls.__profiles_map.get_by_key(uri)

    @classmethod
    def get_by_name(cls, name: str) -> list[Profile]:
        return cls.__profiles_map.get_by_index("name", name)

    @classmethod
    def get_by_token(cls, token: str) -> Profile:
        return cls.__profiles_map.get_by_index("token", token)

    @classmethod
    def get_sibling_profiles(cls, profile: Profile) -> list[Profile]:
        return [p for p in cls.__profiles_map.values() if profile in p.parents]

    @classmethod
    def all(cls) -> list[Profile]:
        return cls.__profiles_map.values()


class SkipRequirementCheck(Exception):
    def __init__(self, check: RequirementCheck, message: str = ""):
        self.check = check
        self.message = message

    def __str__(self):
        return f"SkipRequirementCheck(check={self.check})"


@total_ordering
class Requirement(ABC):

    def __init__(self,
                 profile: Profile,
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None,
                 initialize_checks: bool = True):
        self._order_number: Optional[int] = None
        self._profile = profile
        self._description = description
        self._path = path  # path of code implementing the requirement
        self._level_from_path = None
        self._checks: list[RequirementCheck] = []
        self._overridden = None

        if not name and path:
            self._name = get_requirement_name_from_file(path)
        else:
            self._name = name

        # set flag to indicate if the checks have been initialized
        self._checks_initialized = False
        # initialize the checks if the flag is set
        if initialize_checks:
            _ = self.__init_checks__()
            # assign order numbers to checks
            self.__reorder_checks__()
            # update the checks initialized flag
            self._checks_initialized = True

    @property
    def order_number(self) -> int:
        assert self._order_number is not None
        return self._order_number

    @property
    def identifier(self) -> str:
        return f"{self.profile.identifier}.{self.relative_identifier}"

    @property
    def relative_identifier(self) -> str:
        return f"{self.order_number}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def severity_from_path(self) -> Severity:
        return self.requirement_level_from_path.severity if self.requirement_level_from_path else None

    @property
    def requirement_level_from_path(self) -> RequirementLevel:
        if not self._level_from_path:
            try:
                self._level_from_path = LevelCollection.get(self._path.parent.name)
            except ValueError:
                logger.debug("The requirement level could not be determined from the path: %s", self._path)
        return self._level_from_path

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def description(self) -> str:
        if not self._description:
            self._description = self.__class__.__doc__.strip(
            ) if self.__class__.__doc__ else f"Profile Requirement {self.name}"
        return self._description

    @property
    def overridden(self) -> bool:
        # Check if the requirement has been overridden.
        # The requirement can be considered overridden if all its checks have been overridden
        if self._overridden is None:
            self._overridden = len([_ for _ in self._checks if not _.overridden]) == 0
        return self._overridden

    @property
    @abstractmethod
    def hidden(self) -> bool:
        pass

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @abstractmethod
    def __init_checks__(self) -> list[RequirementCheck]:
        pass

    def get_checks(self) -> list[RequirementCheck]:
        return self._checks.copy()

    def get_check(self, name: str) -> Optional[RequirementCheck]:
        for check in self._checks:
            if check.name == name:
                return check
        return None

    def get_checks_by_level(self, level: RequirementLevel) -> list[RequirementCheck]:
        return list({check for check in self._checks if check.level.severity == level.severity})

    def __reorder_checks__(self) -> None:
        for i, check in enumerate(self._checks):
            check.order_number = i + 1

    def __do_validate__(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the validation
        Returns whether all checks in this requirement passed.
        """
        logger.debug("Validating Requirement %s with %s checks", self.name, len(self._checks))

        logger.debug("Running %s checks for Requirement '%s'", len(self._checks), self.name)
        all_passed = True
        for check in self._checks:
            try:
                logger.debug("Running check '%s' - Desc: %s - overridden: %s",
                             check.name, check.description, [_.identifier for _ in check.overridden_by])
                if check.overridden:
                    logger.debug("Skipping check '%s' because overridden by '%r'",
                                 check.identifier, [_.identifier for _ in check.overridden_by])
                    continue
                context.validator.notify(RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_START, check))
                check_result = check.execute_check(context)
                logger.debug("Result of check %s: %s", check.identifier, check_result)
                context.result.add_executed_check(check, check_result)
                context.validator.notify(RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_END, check, validation_result=check_result))
                logger.debug("Ran check '%s'. Got result %s", check.name, check_result)
                if not isinstance(check_result, bool):
                    logger.warning("Ignoring the check %s as it returned the value %r instead of a boolean", check.name)
                    raise RuntimeError(f"Ignoring invalid result from check {check.name}")
                all_passed = all_passed and check_result
                if not all_passed and context.fail_fast:
                    break
            except SkipRequirementCheck as e:
                logger.debug("Skipping check '%s' because: %s", check.name, e)
                context.result.add_skipped_check(check)
                continue
            except Exception as e:
                # Ignore the fact that the check failed as far as the validation result is concerned.
                logger.warning("Unexpected error during check %s.  Exception: %s", check, e)
                logger.warning("Consider reporting this as a bug.")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)

        logger.debug("Checks for Requirement '%s' completed. Checks passed? %s", self.name, all_passed)
        return all_passed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.name == other.name \
            and self.description == other.description \
            and self.path == other.path

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.description, self.path))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Requirement):
            raise ValueError(f"Cannot compare Requirement with {type(other)}")
        return (self._order_number, self.name) < (other._order_number, other.name)

    def __repr__(self):
        return (
            f'ProfileRequirement('
            f'_order_number={self._order_number}, '
            f'name={self.name}, '
            f'description={self.description}'
            f', path={self.path}, ' if self.path else ''
            ')'
        )

    def __str__(self) -> str:
        return self.name


class RequirementLoader:

    def __init__(self, profile: Profile):
        self._profile = profile

    @property
    def profile(self) -> Profile:
        return self._profile

    @staticmethod
    def __get_requirement_type__(requirement_path: Path) -> str:
        if requirement_path.suffix == ".py":
            return "python"
        elif requirement_path.suffix == ".ttl":
            return "shacl"
        else:
            raise ValueError(f"Unsupported requirement type: {requirement_path.suffix}")

    @classmethod
    def __get_requirement_loader__(cls, profile: Profile, requirement_path: Path) -> RequirementLoader:
        import importlib
        requirement_type = cls.__get_requirement_type__(requirement_path)
        loader_instance_name = f"_{requirement_type}_loader_instance"
        loader_instance = getattr(profile, loader_instance_name, None)
        if loader_instance is None:
            module_name = f"rocrate_validator.requirements.{requirement_type}"
            logger.debug("Loading module: %s", module_name)
            module = importlib.import_module(module_name)
            loader_class_name = f"{'Py' if requirement_type == 'python' else 'SHACL'}RequirementLoader"
            loader_class = getattr(module, loader_class_name)
            loader_instance = loader_class(profile)
            setattr(profile, loader_instance_name, loader_instance)
        return loader_instance

    @staticmethod
    def load_requirements(profile: Profile, severity: Severity = None) -> list[Requirement]:
        """
        Load the requirements related to the profile
        """
        def ok_file(p: Path) -> bool:
            return p.is_file() \
                and p.suffix in PROFILE_FILE_EXTENSIONS \
                and not p.name == DEFAULT_ONTOLOGY_FILE \
                and not p.name == PROFILE_SPECIFICATION_FILE \
                and not p.name.startswith('.') \
                and not p.name.startswith('_')

        files = sorted((p for p in profile.path.rglob('*.*') if ok_file(p)),
                       key=lambda x: (not x.suffix == '.py', x))

        # set the requirement level corresponding to the severity
        requirement_level = LevelCollection.get(severity.name)

        requirements = []
        for requirement_path in files:
            try:
                requirement_level_from_path = LevelCollection.get(requirement_path.parent.name)
                if requirement_level_from_path < requirement_level:
                    continue
            except ValueError:
                logger.debug("The requirement level could not be determined from the path: %s", requirement_path)
            requirement_loader = RequirementLoader.__get_requirement_loader__(profile, requirement_path)
            for requirement in requirement_loader.load(
                    profile, requirement_level,
                    requirement_path, publicID=profile.publicID):
                requirements.append(requirement)
        # sort the requirements by severity
        requirements = sorted(requirements,
                              key=lambda x: (-x.severity_from_path.value, x.path.name, x.name)
                              if x.severity_from_path is not None else (0, x.path.name, x.name),
                              reverse=False)
        # assign order numbers to requirements
        for i, requirement in enumerate(requirements):
            requirement._order_number = i + 1
        # log and return the requirements
        logger.debug("Profile %s loaded %s requirements: %s",
                     profile.identifier, len(requirements), requirements)
        return requirements


@total_ordering
class RequirementCheck(ABC):

    def __init__(self,
                 requirement: Requirement,
                 name: str,
                 level: Optional[RequirementLevel] = LevelCollection.REQUIRED,
                 description: Optional[str] = None):
        self._requirement: Requirement = requirement
        self._order_number = 0
        self._name = name
        self._level = level
        self._description = description

    @property
    def order_number(self) -> int:
        return self._order_number

    @order_number.setter
    def order_number(self, value: int) -> None:
        if value < 0:
            raise ValueError("order_number can't be < 0")
        self._order_number = value

    @property
    def identifier(self) -> str:
        return f"{self.requirement.identifier}.{self.order_number}"

    @property
    def relative_identifier(self) -> str:
        return f"{self.level.name} {self.requirement.relative_identifier}.{self.order_number}"

    @property
    def name(self) -> str:
        if not self._name:
            return self.__class__.__name__.replace("Check", "")
        return self._name

    @property
    def description(self) -> str:
        if not self._description:
            return self.__class__.__doc__.strip() if self.__class__.__doc__ else f"Check {self.name}"
        return self._description

    @property
    def requirement(self) -> Requirement:
        return self._requirement

    @property
    def level(self) -> RequirementLevel:
        return self._level or \
            self.requirement.requirement_level_from_path or \
            LevelCollection.REQUIRED

    @property
    def severity(self) -> Severity:
        return self.level.severity

    @property
    def overridden_by(self) -> list[RequirementCheck]:
        overridden_by = []
        for sibling_profile in self.requirement.profile.siblings:
            check = sibling_profile.get_requirement_check(self.name)
            if check:
                overridden_by.append(check)
        return overridden_by

    @property
    def override(self) -> list[RequirementCheck]:
        overrides = []
        for parent in self.requirement.profile.parents:
            check = parent.get_requirement_check(self.name)
            if check:
                overrides.append(check)
        return overrides

    @property
    def overridden(self) -> bool:
        return len(self.overridden_by) > 0

    @abstractmethod
    def execute_check(self, context: ValidationContext) -> bool:
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise ValueError(f"Cannot compare RequirementCheck with {type(other)}")
        return self.requirement == other.requirement and self.name == other.name

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheck):
            raise ValueError(f"Cannot compare RequirementCheck with {type(other)}")
        return (self.requirement, self.identifier) < (other.requirement, other.identifier)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.requirement, self.name or ""))

    # TODO: delete these?
    #
    # @property
    # def issues(self) -> list[CheckIssue]:
    #    """Return the issues found during the check"""
    #    assert self.result, "Issues not set before the check"
    #    return self.result.get_issues_by_check(self, Severity.OPTIONAL)

    # def get_issues_by_severity(self, severity: Severity = Severity.RECOMMENDED) -> list[CheckIssue]:
    #    return self.result.get_issues_by_check_and_severity(self, severity)


# TODO: delete this?

# def issue_types(issues: list[Type[CheckIssue]]) -> Type[RequirementCheck]:
#     def class_decorator(cls):
#         cls.issue_types = issues
#         return cls
#     return class_decorator


@total_ordering
class CheckIssue:
    """
    Class to store an issue found during a check

    Attributes:
        severity (IssueSeverity): The severity of the issue
        message (str): The message
        code (int): The code
        check (RequirementCheck): The check that generated the issue
    """

    # TODO:
    # 2. CheckIssue has the check, so it is able to determine the level and the Severity
    #    without having it provided through an additional argument.
    def __init__(self, severity: Severity,
                 check: RequirementCheck,
                 message: Optional[str] = None,
                 resultPath: Optional[str] = None,
                 focusNode: Optional[str] = None,
                 value: Optional[str] = None):
        if not isinstance(severity, Severity):
            raise TypeError(f"CheckIssue constructed with a severity '{severity}' of type {type(severity)}")
        self._severity = severity
        self._message = message
        self._check: RequirementCheck = check
        self._resultPath = resultPath
        self._focusNode = focusNode
        self._value = value

    @property
    def message(self) -> Optional[str]:
        """The message associated with the issue"""
        return self._message

    @property
    def level(self) -> RequirementLevel:
        """The level of the issue"""
        return self._check.level

    @property
    def severity(self) -> Severity:
        """Severity of the RequirementLevel associated with this check."""
        return self._severity

    @property
    def level_name(self) -> str:
        return self.level.name

    @property
    def check(self) -> RequirementCheck:
        """The check that generated the issue"""
        return self._check

    @property
    def resultPath(self) -> Optional[str]:
        return self._resultPath

    @property
    def focusNode(self) -> Optional[str]:
        return self._focusNode

    @property
    def value(self) -> Optional[str]:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CheckIssue) and \
            self._check == other._check and \
            self._severity == other._severity and \
            self._message == other._message

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CheckIssue):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return (self._check, self._severity, self._message) < (other._check, other._severity, other._message)

    def __hash__(self) -> int:
        return hash((self._check, self._severity, self._message))

    def __repr__(self) -> str:
        return f'CheckIssue(severity={self.severity}, check={self.check}, message={self.message})'

    def __str__(self) -> str:
        return f"{self.severity}: {self.message} ({self.check})"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.name,
            "message": self.message,
            "check": self.check.name,
            "resultPath": self.resultPath,
            "focusNode": self.focusNode,
            "value": self.value
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4, cls=CustomEncoder)

    # @property
    # def code(self) -> int:
    #     breakpoint()
    #     # If the code has not been set, calculate it
    #     if not self._code:
    #         """
    #         Calculate the code based on the severity, the class name and the message.
    #         - All issues with the same severity, class name and message will have the same code.
    #         - All issues with the same severity and class name but different message will have different codes.
    #         - All issues with the same severity but different class name and message will have different codes.
    #         - All issues with the same severity should start with the same number.
    #         - All codes should be positive numbers.
    #         """
    #         # Concatenate the level, class name and message into a single string
    #         issue_string = self.level.name + self.__class__.__name__ + str(self.message)
    #
    #         # Use the built-in hash function to generate a unique code for this string
    #         # The modulo operation ensures that the code is a positive number
    #         self._code = hash(issue_string) % ((1 << 31) - 1)
    #     # Return the code
    #     return self._code


class ValidationResult:

    def __init__(self, context: ValidationContext):
        # reference to the validation context
        self._context = context
        # reference to the ro-crate path
        self._rocrate_path = context.rocrate_path
        # reference to the validation settings
        self._validation_settings: dict[str, BaseTypes] = context.settings
        # keep track of the issues found during the validation
        self._issues: list[CheckIssue] = []
        # keep track of the checks that have been executed
        self._executed_checks: set[RequirementCheck] = set()
        self._executed_checks_results: dict[str, bool] = {}
        # keep track of the checks that have been skipped
        self._skipped_checks: set[RequirementCheck] = set()

    @property
    def context(self) -> ValidationContext:
        return self._context

    @property
    def rocrate_path(self):
        return self._rocrate_path

    @property
    def validation_settings(self):
        return self._validation_settings

    # --- Checks ---
    @property
    def executed_checks(self) -> set[RequirementCheck]:
        return self._executed_checks

    def add_executed_check(self, check: RequirementCheck, result: bool):
        self._executed_checks.add(check)
        self._executed_checks_results[check.identifier] = result
        # remove the check from the skipped checks if it was skipped
        if check in self._skipped_checks:
            self._skipped_checks.remove(check)
            logger.debug("Removing check '%s' from skipped checks", check.name)

    def get_executed_check_result(self, check: RequirementCheck) -> Optional[bool]:
        return self._executed_checks_results.get(check.identifier)

    @property
    def skipped_checks(self) -> set[RequirementCheck]:
        return self._skipped_checks

    def add_skipped_check(self, check: RequirementCheck):
        self._skipped_checks.add(check)

    def remove_skipped_check(self, check: RequirementCheck):
        self._skipped_checks.remove(check)

    #  --- Issues ---
    @property
    def issues(self) -> list[CheckIssue]:
        return self._issues

    def get_issues(self, min_severity: Optional[Severity] = None) -> list[CheckIssue]:
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.severity >= min_severity]

    def get_issues_by_check(self,
                            check: RequirementCheck,
                            min_severity: Severity = None) -> list[CheckIssue]:
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.check == check and issue.severity >= min_severity]

    # def get_issues_by_check_and_severity(self, check: RequirementCheck, severity: Severity) -> list[CheckIssue]:
    #     return [issue for issue in self.issues if issue.check == check and issue.severity == severity]

    def has_issues(self, severity: Optional[Severity] = None) -> bool:
        severity = severity or self.context.requirement_severity
        return any(issue.severity >= severity for issue in self._issues)

    def passed(self, severity: Optional[Severity] = None) -> bool:
        severity = severity or self.context.requirement_severity
        return not any(issue.severity >= severity for issue in self._issues)

    def add_issue(self, issue: CheckIssue):
        bisect.insort(self._issues, issue)

    def add_check_issue(self,
                        message: str,
                        check: RequirementCheck,
                        severity: Optional[Severity] = None,
                        resultPath: Optional[str] = None,
                        focusNode: Optional[str] = None,
                        value: Optional[str] = None) -> CheckIssue:
        sev_value = severity if severity is not None else check.severity
        c = CheckIssue(sev_value, check, message, resultPath=resultPath, focusNode=focusNode, value=value)
        # self._issues.append(c)
        bisect.insort(self._issues, c)
        return c

    def add_error(self, message: str, check: RequirementCheck) -> CheckIssue:
        return self.add_check_issue(message, check, Severity.REQUIRED)

    #  --- Requirements ---
    @property
    def failed_requirements(self) -> Collection[Requirement]:
        return set(issue.check.requirement for issue in self._issues)

    #  --- Checks ---
    @property
    def failed_checks(self) -> Collection[RequirementCheck]:
        return set(issue.check for issue in self._issues)

    def get_failed_checks_by_requirement(self, requirement: Requirement) -> Collection[RequirementCheck]:
        return [check for check in self.failed_checks if check.requirement == requirement]

    def get_failed_checks_by_requirement_and_severity(
            self, requirement: Requirement, severity: Severity) -> Collection[RequirementCheck]:
        return [check for check in self.failed_checks
                if check.requirement == requirement
                and check.severity == severity]

    def __str__(self) -> str:
        return f"Validation result: {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(issues={self._issues})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationResult):
            raise TypeError(f"Cannot compare ValidationResult with {type(other)}")
        return self._issues == other._issues

    def to_dict(self) -> dict:
        allowed_properties = ["data_path", "profiles_path",
                              "profile_identifier", "inherit_profiles", "requirement_severity", "abort_on_first"]
        return {
            "rocrate": str(self.rocrate_path),
            "validation_settings": {key: self.validation_settings[key]
                                    for key in allowed_properties if key in self.validation_settings},
            "passed": self.passed(self.context.settings["requirement_severity"]),
            "issues": [issue.to_dict() for issue in self.issues]
        }

    def to_json(self, path: Optional[Path] = None) -> str:

        result = json.dumps(self.to_dict(), indent=4, cls=CustomEncoder)
        if path:
            with open(path, "w") as f:
                f.write(result)
        return result


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, CheckIssue):
            return obj.__dict__
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Severity):
            return obj.name
        if isinstance(obj, RequirementCheck):
            return obj.identifier
        if isinstance(obj, Requirement):
            return obj.identifier
        if isinstance(obj, RequirementLevel):
            return obj.name

        return super().default(obj)


@dataclass
class ValidationSettings:

    # Data settings
    data_path: Path
    # Profile settings
    profiles_path: Path = DEFAULT_PROFILES_PATH
    profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER
    inherit_profiles: bool = True
    allow_requirement_check_override: bool = True
    disable_check_for_duplicates: bool = False
    # Ontology and inference settings
    ontology_path: Optional[Path] = None
    inference: Optional[VALID_INFERENCE_OPTIONS_TYPES] = None
    # Validation strategy settings
    advanced: bool = True  # enable SHACL Advanced Validation
    inplace: Optional[bool] = False
    abort_on_first: Optional[bool] = True
    inplace: Optional[bool] = False
    meta_shacl: bool = False
    iterate_rules: bool = True
    target_only_validation: bool = True
    remote_validation: bool = True
    http_cache_timeout: int = 60
    # Requirement severity settings
    requirement_severity: Union[str, Severity] = Severity.REQUIRED
    requirement_severity_only: bool = False
    allow_infos: Optional[bool] = True
    allow_warnings: Optional[bool] = True
    # Output serialization settings
    serialization_output_path: Optional[Path] = None
    serialization_output_format: RDF_SERIALIZATION_FORMATS_TYPES = "turtle"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # if requirement_severity is a str, convert to Severity
        severity = getattr(self, "requirement_severity")
        if isinstance(severity, str):
            setattr(self, "requirement_severity", Severity[severity])

    def to_dict(self):
        return asdict(self)

    @classmethod
    def parse(cls, settings: Union[dict, ValidationSettings]) -> ValidationSettings:
        """
        Parse the settings into a ValidationSettings object

        Args:
            settings (Union[dict, ValidationSettings]): The settings to parse

        Returns:
            ValidationSettings: The parsed settings

        Raises:
            ValueError: If the settings type is invalid
        """
        if isinstance(settings, dict):
            return cls(**settings)
        elif isinstance(settings, ValidationSettings):
            return settings
        else:
            raise ValueError(f"Invalid settings type: {type(settings)}")


class ValidationEvent(Event):
    def __init__(self, event_type: EventType,
                 validation_result: Optional[ValidationResult] = None, message: Optional[str] = None):
        super().__init__(event_type, message)
        self._validation_result = validation_result

    @property
    def validation_result(self) -> Optional[ValidationResult]:
        return self._validation_result


class ProfileValidationEvent(Event):
    def __init__(self, event_type: EventType, profile: Profile, message: Optional[str] = None):
        assert event_type in (EventType.PROFILE_VALIDATION_START, EventType.PROFILE_VALIDATION_END)
        super().__init__(event_type, message)
        self._profile = profile

    @property
    def profile(self) -> Profile:
        return self._profile


class RequirementValidationEvent(Event):
    def __init__(self,
                 event_type: EventType,
                 requirement: Requirement,
                 validation_result: Optional[bool] = None,
                 message: Optional[str] = None):
        assert event_type in (EventType.REQUIREMENT_VALIDATION_START, EventType.REQUIREMENT_VALIDATION_END)
        super().__init__(event_type, message)
        self._requirement = requirement
        self._validation_result = validation_result

    @property
    def requirement(self) -> Requirement:
        return self._requirement

    @property
    def validation_result(self) -> Optional[bool]:
        return self._validation_result


class RequirementCheckValidationEvent(Event):
    def __init__(self, event_type: EventType,
                 requirement_check: RequirementCheck,
                 validation_result: Optional[bool] = None, message: Optional[str] = None):
        assert event_type in (EventType.REQUIREMENT_CHECK_VALIDATION_START, EventType.REQUIREMENT_CHECK_VALIDATION_END)
        super().__init__(event_type, message)
        self._requirement_check = requirement_check
        self._validation_result = validation_result

    @property
    def requirement_check(self) -> RequirementCheck:
        return self._requirement_check

    @property
    def validation_result(self) -> Optional[bool]:
        return self._validation_result


class Validator(Publisher):
    """
    Can validate conformance to a single Profile (including any requirements
    inherited by parent profiles).
    """

    def __init__(self, settings: Union[str, ValidationSettings]):
        self._validation_settings = ValidationSettings.parse(settings)
        super().__init__()

    @property
    def validation_settings(self) -> ValidationSettings:
        return self._validation_settings

    def detect_rocrate_profiles(self) -> list[Profile]:
        """
        Detect the profiles to validate against
        """
        try:
            # initialize the validation context
            context = ValidationContext(self, self.validation_settings.to_dict())
            candidate_profiles_uris = set()
            try:
                candidate_profiles_uris.add(context.ro_crate.metadata.get_conforms_to())
            except Exception as e:
                logger.debug("Error while getting candidate profiles URIs: %s", e)
            try:
                candidate_profiles_uris.add(context.ro_crate.metadata.get_root_data_entity_conforms_to())
            except Exception as e:
                logger.debug("Error while getting candidate profiles URIs: %s", e)

            logger.debug("Candidate profiles: %s", candidate_profiles_uris)
            if not candidate_profiles_uris:
                logger.debug("Unable to determine the profile to validate against")
                return None
            # load the profiles
            profiles = []
            candidate_profiles = []
            available_profiles = Profile.load_profiles(context.profiles_path, publicID=context.publicID,
                                                       severity=context.requirement_severity)
            profiles = [p for p in available_profiles if p.uri in candidate_profiles_uris]
            # get the candidate profiles
            for profile in profiles:
                candidate_profiles.append(profile)
                inherited_profiles = profile.inherited_profiles
                for inherited_profile in inherited_profiles:
                    if inherited_profile in candidate_profiles:
                        candidate_profiles.remove(inherited_profile)
            logger.debug("%d Candidate Profiles found: %s", len(candidate_profiles), candidate_profiles)
            return candidate_profiles

        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)
            return None

    def validate(self) -> ValidationResult:
        return self.__do_validate__()

    def validate_requirements(self, requirements: list[Requirement]) -> ValidationResult:
        # check if requirement is an instance of Requirement
        assert all(isinstance(requirement, Requirement) for requirement in requirements), \
            "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def __do_validate__(self,
                        requirements: Optional[list[Requirement]] = None) -> ValidationResult:

        # initialize the validation context
        context = ValidationContext(self, self.validation_settings.to_dict())

        # set the profiles to validate against
        profiles = context.profiles
        assert len(profiles) > 0, "No profiles to validate"
        self.notify(EventType.VALIDATION_START)
        for profile in profiles:
            logger.debug("Validating profile %s (id: %s)", profile.name, profile.identifier)
            self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_START, profile=profile))
            # perform the requirements validation
            requirements = profile.get_requirements(
                context.requirement_severity, exact_match=context.requirement_severity_only)
            logger.debug("Validating profile %s with %s requirements", profile.identifier, len(requirements))
            logger.debug("For profile %s, validating these %s requirements: %s",
                         profile.identifier, len(requirements), requirements)
            terminate = False
            for requirement in requirements:
                if not requirement.overridden:
                    self.notify(RequirementValidationEvent(
                        EventType.REQUIREMENT_VALIDATION_START, requirement=requirement))
                passed = requirement.__do_validate__(context)
                logger.debug("Requirement %s passed: %s", requirement, passed)
                if not requirement.overridden:
                    self.notify(RequirementValidationEvent(
                        EventType.REQUIREMENT_VALIDATION_END, requirement=requirement, validation_result=passed))
                if passed:
                    logger.debug("Validation Requirement passed")
                else:
                    logger.debug(f"Validation Requirement {requirement} failed (profile: {profile.identifier})")
                    if context.fail_fast:
                        logger.debug("Aborting on first requirement failure")
                        terminate = True
                        break
            self.notify(ProfileValidationEvent(EventType.PROFILE_VALIDATION_END, profile=profile))
            if terminate:
                break
        self.notify(ValidationEvent(EventType.VALIDATION_END,
                    validation_result=context.result))

        return context.result


class ValidationContext:

    def __init__(self, validator: Validator, settings: dict[str, object]):
        # reference to the validator
        self._validator = validator
        # reference to the settings
        self._settings = settings
        # reference to the data graph
        self._data_graph = None
        # reference to the profiles
        self._profiles = None
        # reference to the validation result
        self._result = None
        # additional properties for the context
        self._properties = {}

        # parse the rocrate path
        rocrate_path: URI = URI(settings.get("data_path"))
        logger.debug("Validating RO-Crate: %s", rocrate_path)

        # initialize the ROCrate object
        self._rocrate = ROCrate.new_instance(rocrate_path)
        assert isinstance(self._rocrate, ROCrate), "Invalid RO-Crate instance"

    @property
    def ro_crate(self) -> ROCrate:
        return self._rocrate

    @property
    def validator(self) -> Validator:
        return self._validator

    @property
    def result(self) -> ValidationResult:
        if self._result is None:
            self._result = ValidationResult(self)
        return self._result

    @property
    def settings(self) -> dict[str, object]:
        return self._settings

    @property
    def publicID(self) -> str:
        path = str(self.ro_crate.uri.base_uri)
        if not path.endswith("/"):
            path = f"{path}/"
        return path

    @property
    def profiles_path(self) -> Path:
        profiles_path = self.settings.get("profiles_path")
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        return profiles_path

    @property
    def requirement_severity(self) -> Severity:
        severity = self.settings.get("requirement_severity", Severity.REQUIRED)
        if isinstance(severity, str):
            severity = Severity[severity]
        elif not isinstance(severity, Severity):
            raise ValueError(f"Invalid severity type: {type(severity)}")
        return severity

    @property
    def requirement_severity_only(self) -> bool:
        return self.settings.get("requirement_severity_only", False)

    @property
    def rocrate_path(self) -> Path:
        return self.settings.get("data_path")

    @property
    def fail_fast(self) -> bool:
        return self.settings.get("abort_on_first", True)

    @property
    def rel_fd_path(self) -> Path:
        return Path(ROCRATE_METADATA_FILE)

    def __load_data_graph__(self):
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata of: %s", self.ro_crate.uri)
        _ = data_graph.parse(data=self.ro_crate.metadata.as_dict(),
                             format="json-ld", publicID=self.publicID)
        logger.debug("RO-Crate metadata loaded: %s", data_graph)
        return data_graph

    def get_data_graph(self, refresh: bool = False):
        # load the data graph
        try:
            if not self._data_graph or refresh:
                self._data_graph = self.__load_data_graph__()
            return self._data_graph
        except FileNotFoundError as e:
            logger.debug("Error loading data graph: %s", e)
            raise ROCrateMetadataNotFoundError(self.rocrate_path)

    @property
    def data_graph(self) -> Graph:
        return self.get_data_graph()

    @property
    def inheritance_enabled(self) -> bool:
        return self.settings.get("inherit_profiles", False)

    @property
    def profile_identifier(self) -> str:
        return self.settings.get("profile_identifier")

    @property
    def allow_requirement_check_override(self) -> bool:
        return self.settings.get("allow_requirement_check_override", True)

    @property
    def disable_check_for_duplicates(self) -> bool:
        return self.settings.get("disable_check_for_duplicates", False)

    def __load_profiles__(self) -> list[Profile]:

        # if the inheritance is disabled, load only the target profile
        if not self.inheritance_enabled:
            profile = Profile.load(
                self.profiles_path,
                self.profiles_path / self.profile_identifier,
                publicID=self.publicID,
                severity=self.requirement_severity)
            return [profile]

        # load all profiles
        profiles = Profile.load_profiles(
            self.profiles_path,
            publicID=self.publicID,
            severity=self.requirement_severity,
            allow_requirement_check_override=self.allow_requirement_check_override)

        # Check if the target profile is in the list of profiles
        profile = Profile.get_by_identifier(self.profile_identifier)
        if not profile:
            try:
                candidate_profiles = Profile.get_by_token(self.profile_identifier)
                logger.debug("Candidate profiles found by token: %s", profile)
                if candidate_profiles:
                    # Find the profile with the highest version number
                    profile = max(candidate_profiles, key=lambda p: p.version)
                    self.settings["profile_identifier"] = profile.identifier
                    logger.debug("Profile with the highest version number: %s", profile)
                # if the profile is found by token, set the profile name to the identifier
                self.settings["profile_identifier"] = profile.identifier
            except AttributeError as e:
                # raised when the profile is not found
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception(e)
                raise ProfileNotFound(
                    self.profile_identifier,
                    message=f"Profile '{self.profile_identifier}' not found in '{self.profiles_path}'") from e

        # Set the profiles to validate against as the target profile and its inherited profiles
        profiles = profile.inherited_profiles + [profile]

        # if the check for duplicates is disabled, return the profiles
        if self.disable_check_for_duplicates:
            return profiles

        return profiles

    @property
    def profiles(self) -> list[Profile]:
        if not self._profiles:
            self._profiles = self.__load_profiles__()
        return self._profiles.copy()

    @property
    def target_profile(self) -> Profile:
        profiles = self.profiles
        assert len(profiles) > 0, "No profiles to validate"
        return self.profiles[-1]

    def get_profile_by_token(self, token: str) -> list[Profile]:
        return [p for p in self.profiles if p.token == token]

    def get_profile_by_identifier(self, identifier: str) -> list[Profile]:
        for p in self.profiles:
            if p.identifier == identifier:
                return p
        raise ProfileNotFound(identifier)
