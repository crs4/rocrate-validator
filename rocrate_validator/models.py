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
from urllib.error import HTTPError

import enum_tools
from rdflib import RDF, RDFS, Graph, Namespace, URIRef

import rocrate_validator.log as logging
from rocrate_validator import __version__
from rocrate_validator.constants import (DEFAULT_ONTOLOGY_FILE,
                                         DEFAULT_PROFILE_IDENTIFIER,
                                         DEFAULT_PROFILE_README_FILE,
                                         IGNORED_PROFILE_DIRECTORIES,
                                         JSON_OUTPUT_FORMAT_VERSION, PROF_NS,
                                         PROFILE_FILE_EXTENSIONS,
                                         PROFILE_SPECIFICATION_FILE,
                                         ROCRATE_METADATA_FILE, SCHEMA_ORG_NS)
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
@enum_tools.documentation.document_enum
@total_ordering
class Severity(enum.Enum):
    """
    Enum ordering "strength" of conditions to be verified
    """

    #: the condition is not mandatory
    OPTIONAL = 0
    #: the condition is recommended
    RECOMMENDED = 2
    #: the condition is mandatory
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

    """
    Represents a requirement level.

    A requirement has a name and a severity level of type :class:`.Severity`.
    It implements the comparison operators to allow ordering of the requirement levels.
    """
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
    Collection of :class:`.RequirementLevel` instances.

    Provides a set of predefined RequirementLevel instances
    that can be used to define the severity of a requirement.
    They map the keywords defined in **RFC 2119** to the corresponding severity levels.

    .. note::
        The keywords **MUST**, **MUST NOT**, **REQUIRED**,
        **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**,
        **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document
        are to be interpreted as described in **RFC 2119**.

    """
    #: The requirement level OPTIONAL is mapped to the OPTIONAL severity level
    OPTIONAL = RequirementLevel('OPTIONAL', Severity.OPTIONAL)
    #: The requirement level MAY is mapped to the OPTIONAL severity level
    MAY = RequirementLevel('MAY', Severity.OPTIONAL)
    #: The requirement level REQUIRED is mapped to the REQUIRED severity level
    REQUIRED = RequirementLevel('REQUIRED', Severity.REQUIRED)
    #: The requirement level SHOULD is mapped to the RECOMMENDED severity level
    SHOULD = RequirementLevel('SHOULD', Severity.RECOMMENDED)
    #: The requirement level SHOULD NOT is mapped to the RECOMMENDED severity level
    SHOULD_NOT = RequirementLevel('SHOULD_NOT', Severity.RECOMMENDED)
    #: The requirement level RECOMMENDED is mapped to the RECOMMENDED severity level
    RECOMMENDED = RequirementLevel('RECOMMENDED', Severity.RECOMMENDED)

    #: The requirement level MUST is mapped to the REQUIRED severity level
    MUST = RequirementLevel('MUST', Severity.REQUIRED)
    #: The requirement level MUST_NOT is mapped to the REQUIRED severity level
    MUST_NOT = RequirementLevel('MUST_NOT', Severity.REQUIRED)
    #: The requirement level SHALL is mapped to the REQUIRED severity level
    SHALL = RequirementLevel('SHALL', Severity.REQUIRED)
    #: The requirement level SHALL_NOT is mapped to the REQUIRED severity level
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

    """
    RO-Crate Validator profile.

    A profile is a named set of requirements that can be used to validate an RO-Crate.
    """

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
        """
        Initialize the Profile instance

        :param profile_path: the path of the profile
        :type profile_path: Path

        :param requirements: the list of requirements of the profile
        :type requirements: list[Requirement]

        :param identifier: the identifier of the profile
        :type identifier: str

        :param publicID: the public identifier of the profile
        :type publicID: str
        :meta private:

        :param severity: the severity of the profile
        :type severity: Severity

        : raises ProfileSpecificationNotFound: if the profile specification file is not found
        : raises ProfileSpecificationError: if the profile specification file contains more than one profile
        : raises InvalidProfilePath: if the profile path is not a directory

        :meta private:
        """
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
        """
        The path of the profile directory
        """
        return self._profile_path

    @property
    def identifier(self) -> str:
        """
        The identifier of the profile.
        """
        if not self._identifier:
            version = self.version
            self._identifier = f"{self.token}-{version}" if version else self.token
        return self._identifier

    @property
    def name(self):
        """
        The name of the profile as specified in the profile specification file
        (i.e., the value of the rdfs: label property in the `profile.ttl` file) or
        a default name if the label is not specified.
        """
        return self.label or f"Profile {self.uri}"

    @property
    def profile_node(self):
        return self._profile_node

    @property
    def token(self):
        """
        A token that uniquely identifies the profile
        as specified in the profile specification file
        (i.e., the value of the prof: hasToken property
        in the `profile.ttl` file).
        """
        return self._token

    @property
    def uri(self):
        """
        The URI of the profile.
        """
        return self._profile_node.toPython()

    @property
    def label(self):
        return self.__get_specification_property__("label", RDFS)

    @property
    def comment(self):
        """
        The comment added to the profile in the profile specification file
        (i.e., the value of the rdfs: comment property in the `profile.ttl` file).
        """
        return self.__get_specification_property__("comment", RDFS)

    @property
    def version(self):
        """
        The version of the profile as specified in the profile specification file
        (i.e., the value of the prof: version property in the `profile.ttl` file).
        """
        return self._version

    @property
    def is_profile_of(self) -> list[str]:
        """
        The list of profiles that this profile is a profile of
        as specified in the profile specification file
        (i.e., the value of the prof: isProfileOf property in the `profile.ttl` file).
        """
        return self.__get_specification_property__("isProfileOf", PROF_NS, pop_first=False)

    @property
    def is_transitive_profile_of(self) -> list[str]:
        """
        The list of profiles that this profile is a transitive profile of
        as specified in the profile specification file
        (i.e., the value of the prof: isTransitiveProfileOf property in the `profile.ttl` file).
        """
        return self.__get_specification_property__("isTransitiveProfileOf", PROF_NS, pop_first=False)

    @property
    def parents(self) -> list[Profile]:
        """
        The list of profiles that this profile is a profile of
        as specified in the profile specification file.
        """
        return [self.__profiles_map.get_by_key(_) for _ in self.is_profile_of]

    @property
    def siblings(self) -> list[Profile]:
        """
        The list of profiles that are siblings of this profile
        (i.e., profiles that share the same parent profile).
        """
        return self.get_sibling_profiles(self)

    @property
    def readme_file_path(self) -> Path:
        """
        The path of the README file of the profile.
        """
        return self.path / DEFAULT_PROFILE_README_FILE

    @property
    def profile_specification_file_path(self) -> Path:
        """
        The path of the profile specification file.
        """
        return self.path / PROFILE_SPECIFICATION_FILE

    @property
    def publicID(self) -> Optional[str]:
        """
        The public identifier of the RO-Crate which is validated by the profile.

        :meta private:
        """
        return self._publicID

    @property
    def severity(self) -> Severity:
        """
        The severity of the profile which the profile is loaded with,
        i.e., the minimum severity level of the requirements of the profile.
        """
        return self._severity

    @property
    def description(self) -> str:
        """
        The description of the profile as specified in the profile specification file
        (i.e., the value of the rdfs: comment property in the `profile.ttl` file).
        """
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with open(self.readme_file_path, "r") as f:
                    self._description = f.read()
            else:
                self._description = self.comment
        return self._description

    @property
    def requirements(self) -> list[Requirement]:
        """
        The list of requirements of the profile.
        """
        if not self._requirements:
            self._requirements = \
                RequirementLoader.load_requirements(self, severity=self.severity)
        return self._requirements

    def get_requirements(
            self, severity: Severity = Severity.REQUIRED,
            exact_match: bool = False) -> list[Requirement]:
        """
        Get the requirements of the profile with the given severity level.
        If the exact_match flag is set to `True`, only the requirements with the exact severity level
        are returned; otherwise, the requirements with severity level greater than or equal to
        the given severity level are returned.
        """
        return [requirement for requirement in self.requirements
                if (not exact_match and
                    (not requirement.severity_from_path or requirement.severity_from_path >= severity)) or
                (exact_match and requirement.severity_from_path == severity)]

    def get_requirement(self, name: str) -> Optional[Requirement]:
        """
        Get the requirement with the given name
        """
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

    def to_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "uri": self.uri,
            "name": self.name,
            "description": self.description
        }

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
        """
        Get the profile with the given identifier

        :param identifier: the identifier
        :type identifier: str

        :return: the profile
        :rtype: Profile
        """
        return cls.__profiles_map.get_by_index("identifier", identifier)

    @classmethod
    def get_by_uri(cls, uri: str) -> Profile:
        """
        Get the profile with the given URI

        :param uri: the URI
        :type uri: str

        :return: the profile
        :rtype: Profile
        """
        return cls.__profiles_map.get_by_key(uri)

    @classmethod
    def get_by_name(cls, name: str) -> list[Profile]:
        """
        Get the profile with the given name

        :param name: the name
        :type name: str

        :return: the profile
        :rtype: Profile
        """
        return cls.__profiles_map.get_by_index("name", name)

    @classmethod
    def get_by_token(cls, token: str) -> Profile:
        """
        Get the profile with the given token

        :param token: the token
        :type token: str

        :return: the profile
        :rtype: Profile
        """
        return cls.__profiles_map.get_by_index("token", token)

    @classmethod
    def get_sibling_profiles(cls, profile: Profile) -> list[Profile]:
        """
        Get the sibling profiles of the given profile

        :param profile: the profile
        :type profile: Profile

        :return: the list of sibling profiles
        :rtype: list[Profile]
        """
        return [p for p in cls.__profiles_map.values() if profile in p.parents]

    @classmethod
    def all(cls) -> list[Profile]:
        """
        Get all the profiles

        :return: the list of profiles
        :rtype: list[Profile]
        """
        return cls.__profiles_map.values()


class SkipRequirementCheck(Exception):
    def __init__(self, check: RequirementCheck, message: str = ""):
        self.check = check
        self.message = message

    def __str__(self):
        return f"SkipRequirementCheck(check={self.check})"


@total_ordering
class Requirement(ABC):
    """
    Abstract class representing a requirement of a profile.
    A requirement is a named set of checks that can be used to validate an RO-Crate.
    """

    def __init__(self,
                 profile: Profile,
                 name: str = "",
                 description: Optional[str] = None,
                 path: Optional[Path] = None,
                 initialize_checks: bool = True):
        """
        Initialize the Requirement instance

        :meta private:
        """
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
        """
        The order number of the requirement in the profile

        :return: the order number
        :rtype: int
        """
        assert self._order_number is not None
        return self._order_number

    @property
    def identifier(self) -> str:
        """
        The identifier of the requirement

        :return: the identifier
        :rtype: str
        """
        return f"{self.profile.identifier}_{self.relative_identifier}"

    @property
    def relative_identifier(self) -> str:
        """
        The relative identifier of the requirement

        :return: the relative identifier
        :rtype: str

        :meta private:
        """
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

    def _do_validate_(self, context: ValidationContext) -> bool:
        """
        Internal method to perform the validation
        Returns whether all checks in this requirement passed.

        :meta private:
        """
        logger.debug("Validating Requirement %s with %s checks", self.name, len(self._checks))

        logger.debug("Running %s checks for Requirement '%s'", len(self._checks), self.name)
        all_passed = True
        for check in [_ for _ in self._checks
                      if not context.settings.skip_checks
                      or _.identifier not in context.settings.skip_checks]:

            try:
                if check.overridden and not check.requirement.profile.identifier == context.profile_identifier:
                    logger.debug("Skipping check '%s' because overridden by '%r'",
                                 check.identifier, [_.identifier for _ in check.overridden_by])
                    continue
                context.validator.notify(RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_START, check))
                check_result = check.execute_check(context)
                logger.debug("Result of check %s: %s", check.identifier, check_result)
                context.result._add_executed_check(check, check_result)
                context.validator.notify(RequirementCheckValidationEvent(
                    EventType.REQUIREMENT_CHECK_VALIDATION_END, check, validation_result=check_result))
                logger.debug("Ran check '%s'. Got result %s", check.identifier, check_result)
                if not isinstance(check_result, bool):
                    logger.warning("Ignoring the check %s as it returned the value %r instead of a boolean", check.name)
                    raise RuntimeError(f"Ignoring invalid result from check {check.name}")
                all_passed = all_passed and check_result
                if not all_passed and context.fail_fast:
                    break
            except SkipRequirementCheck as e:
                logger.debug("Skipping check '%s' because: %s", check.name, e)
                context.result._add_skipped_check(check)
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

    def to_dict(self, with_profile: bool = True, with_checks: bool = True) -> dict:
        result = {
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "order": self.order_number
        }
        if with_profile:
            result["profile"] = self.profile.to_dict()
        if with_checks:
            result["checks"] = [_.to_dict(with_requirement=False, with_profile=False) for _ in self._checks]
        return result


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
                 description: Optional[str] = None,
                 hidden: Optional[bool] = None):
        self._requirement: Requirement = requirement
        self._order_number = 0
        self._name = name
        self._level = level
        self._description = description
        self._hidden = hidden

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
    def overrides(self) -> list[RequirementCheck]:
        overrides = []
        for parent in self.requirement.profile.parents:
            check = parent.get_requirement_check(self.name)
            if check:
                overrides.append(check)
        return overrides

    @property
    def overridden(self) -> bool:
        return len(self.overridden_by) > 0

    @property
    def hidden(self) -> bool:
        if self._hidden is not None:
            return self._hidden
        return self.requirement.hidden

    @abstractmethod
    def execute_check(self, context: ValidationContext) -> bool:
        raise NotImplementedError()

    def to_dict(self, with_requirement: bool = True, with_profile: bool = True) -> dict:
        result = {
            "identifier": self.identifier,
            "label": self.relative_identifier,
            "order": self.order_number,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.name
        }
        if with_requirement:
            result["requirement"] = self.requirement.to_dict(with_profile=with_profile, with_checks=False)
        return result

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


@total_ordering
class CheckIssue:
    """
    Represents an issue with a check that has been executed
    during the validation process.
    """

    def __init__(self,
                 check: RequirementCheck,
                 message: Optional[str] = None,
                 violatingProperty: Optional[str] = None,
                 violatingEntity: Optional[str] = None,
                 value: Optional[str] = None):
        self._message = message
        self._check: RequirementCheck = check
        self._violatingProperty = violatingProperty
        self._violatingEntity = violatingEntity
        self._propertyValue = value

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
        return self._check.severity

    @property
    def level_name(self) -> str:
        return self.level.name

    @property
    def check(self) -> RequirementCheck:
        """The check that generated the issue"""
        return self._check

    @property
    def violatingEntity(self) -> Optional[str]:
        """
        It represents the specific element being evaluated that fails
        to meet the defined rules or constraints within a validation process.
        Also referred to as `focusNode` in SHACL terminology
        in the context of an RDF graph, it is the subject of a triple
        that violates a given constraint on the subject’s property/predicate,
        represented by the violatingProperty.
        """
        return self._violatingEntity

    @property
    def violatingProperty(self) -> Optional[str]:
        """
        It refers to the specific property or relationship within an item
        that leads to a validation failure.
        It identifies the part of the data structure that is causing the issue.
        Also referred to as `resultPath` in SHACL terminology,
        in the context of an RDF graph, it is the predicate of a triple
        that violates a given constraint on the subject’s property/predicate,
        represented by the violatingProperty.
        """
        return self._violatingProperty

    @property
    def violatingPropertyValue(self) -> Optional[str]:
        """
        It represents the value of the violatingProperty
        that leads to a validation failure.
        """
        return self._propertyValue

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CheckIssue) and \
            self._check == other._check and \
            self._message == other._message

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CheckIssue):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return (self._check, self._message) < (other._check, other._message)

    def __hash__(self) -> int:
        return hash((self._check, self._message))

    def __repr__(self) -> str:
        return f'CheckIssue(severity={self.severity}, check={self.check}, message={self.message})'

    def __str__(self) -> str:
        return f"Issue of severity {self.severity.name} with check \"{self.check.identifier}\": {self.message}"

    def to_dict(self, with_check: bool = True,
                with_requirement: bool = True, with_profile: bool = True) -> dict:
        result = {
            "severity": self.severity.name,
            "message": self.message,
            "violatingEntity": self.violatingEntity,
            "violatingProperty": self.violatingProperty,
            "violatingPropertyValue": self.violatingPropertyValue
        }
        if with_check:
            result["check"] = self.check.to_dict(with_requirement=with_requirement, with_profile=with_profile)
        return result

    def to_json(self,
                with_checks: bool = True,
                with_requirements: bool = True,
                with_profile: bool = True) -> str:
        return json.dumps(
            self.to_dict(
                with_check=with_checks,
                with_requirement=with_requirements,
                with_profile=with_profile
            ), indent=4, cls=CustomEncoder)


class ValidationResult:
    """
    Represents the result of a validation.

    :param context: The validation context
    :type context: ValidationContext
    :param rocrate_uri: The URI of the RO-Crate
    :type rocrate_uri: str
    :param validation_settings: The validation settings
    :type validation_settings: ValidationSettings
    :param issues: The issues found during the validation
    :type issues: list[CheckIssue]
    """

    def __init__(self, context: ValidationContext):
        # reference to the validation context
        self._context = context
        # reference to the ro-crate URI
        self._rocrate_uri = context.rocrate_uri
        # reference to the validation settings
        self._validation_settings: ValidationSettings = context.settings
        # keep track of the issues found during the validation
        self._issues: list[CheckIssue] = []
        # keep track of the checks that have been executed
        self._executed_checks: set[RequirementCheck] = set()
        self._executed_checks_results: dict[str, bool] = {}
        # keep track of the checks that have been skipped
        self._skipped_checks: set[RequirementCheck] = set()

    @property
    def context(self) -> ValidationContext:
        """
        The validation context
        """
        return self._context

    @property
    def rocrate_uri(self):
        """
        The URI of the RO-Crate
        """
        return self._rocrate_uri

    @property
    def validation_settings(self):
        """
        The validation settings
        """
        return self._validation_settings

    # --- Checks ---
    @property
    def executed_checks(self) -> set[RequirementCheck]:
        """
        The checks that have been executed
        """
        return self._executed_checks

    def _add_executed_check(self, check: RequirementCheck, result: bool):
        """
        Internal method to add a check to the executed checks
        """
        self._executed_checks.add(check)
        self._executed_checks_results[check.identifier] = result
        # remove the check from the skipped checks if it was skipped
        if check in self._skipped_checks:
            self._skipped_checks.remove(check)
            logger.debug("Removing check '%s' from skipped checks", check.name)

    def get_executed_check_result(self, check: RequirementCheck) -> Optional[bool]:
        """
        Get the result of an executed check
        """
        return self._executed_checks_results.get(check.identifier)

    @property
    def skipped_checks(self) -> set[RequirementCheck]:
        """
        The checks that have been skipped
        """
        return self._skipped_checks

    def _add_skipped_check(self, check: RequirementCheck):
        """
        Internal method to add a check to the skipped checks
        """
        self._skipped_checks.add(check)

    def _remove_skipped_check(self, check: RequirementCheck):
        """
        Internal method to remove a check from the skipped checks
        """
        self._skipped_checks.remove(check)

    #  --- Issues ---
    @property
    def issues(self) -> list[CheckIssue]:
        """
        The issues found during the validation
        """
        return self._issues.copy()

    def get_issues(self, min_severity: Optional[Severity] = None) -> list[CheckIssue]:
        """
        Get the issues found during the validation with a severity greater than or equal to `min_severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.severity >= min_severity]

    def get_issues_by_check(self,
                            check: RequirementCheck,
                            min_severity: Severity = None) -> list[CheckIssue]:
        """
        Get the issues found during the validation for a specific check
        with a severity greater than or equal to `min_severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return [issue for issue in self._issues if issue.check == check and issue.severity >= min_severity]

    # def get_issues_by_check_and_severity(self, check: RequirementCheck, severity: Severity) -> list[CheckIssue]:
    #     return [issue for issue in self.issues if issue.check == check and issue.severity == severity]

    def has_issues(self, min_severity: Optional[Severity] = None) -> bool:
        """
        Check if there are issues with a severity greater than or equal to the given `severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return any(issue.severity >= min_severity for issue in self._issues)

    def passed(self, min_severity: Optional[Severity] = None) -> bool:
        """
        Check if all checks passed with a severity greater than or equal to the given `severity`
        """
        min_severity = min_severity or self.context.requirement_severity
        return not any(issue.severity >= min_severity for issue in self._issues)

    def add_issue(self,
                  message: str,
                  check: RequirementCheck,
                  violatingEntity: Optional[str] = None,
                  violatingProperty: Optional[str] = None,
                  violatingPropertyValue: Optional[str] = None) -> CheckIssue:
        """
        Add an issue to the validation result

        Parameters:
            message(str): The message of the issue
            check(RequirementCheck): The check that generated the issue
            violatingEntity(Optional[str]): The entity that caused the issue (if any)
            violatingProperty(Optional[str]): The property that caused the issue (if any)
            violatingPropertyValue(Optional[str]): The value of the violatingProperty (if any)
        """
        c = CheckIssue(check, message, violatingProperty=violatingProperty,
                       violatingEntity=violatingEntity, value=violatingPropertyValue)
        bisect.insort(self._issues, c)
        return c

    #  --- Requirements ---
    @property
    def failed_requirements(self) -> Collection[Requirement]:
        """
        Get the requirements that failed
        """
        return set(issue.check.requirement for issue in self._issues)

    #  --- Checks ---
    @property
    def failed_checks(self) -> Collection[RequirementCheck]:
        """
        Get the checks that failed
        """
        return set(issue.check for issue in self._issues)

    def get_failed_checks_by_requirement(self, requirement: Requirement) -> Collection[RequirementCheck]:
        """
        Get the checks that failed for a specific requirement
        """
        return [check for check in self.failed_checks if check.requirement == requirement]

    def get_failed_checks_by_requirement_and_severity(
            self, requirement: Requirement, severity: Severity) -> Collection[RequirementCheck]:
        """
        Get the checks that failed for a specific requirement and severity
        """
        return [check for check in self.failed_checks
                if check.requirement == requirement
                and check.severity == severity]

    def __str__(self) -> str:
        return f"Validation result: passed={len(self.failed_checks)==0}, {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(passed={len(self.failed_checks)==0},issues={self._issues})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationResult):
            raise TypeError(f"Cannot compare ValidationResult with {type(other)}")
        return self._issues == other._issues

    def to_dict(self) -> dict:
        """
        Convert the ValidationResult to a dictionary
        """
        allowed_properties = ["profile_identifier", "enable_profile_inheritance",
                              "requirement_severity", "abort_on_first"]
        validation_settings = {key: value for key, value in self.validation_settings.to_dict().items()
                               if key in allowed_properties}
        result = {
            "meta": {
                "version": JSON_OUTPUT_FORMAT_VERSION
            },
            "validation_settings": validation_settings,
            "passed": self.passed(self.context.settings.requirement_severity),
            "issues": [issue.to_dict() for issue in self.issues]
        }
        # add validator version to the settings
        result["validation_settings"]["rocrate_validator_version"] = __version__
        return result

    def to_json(self, path: Optional[Path] = None) -> str:
        """
        Convert the ValidationResult to a JSON string
        """
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
    """
    Represents the settings for RO-Crate validation.

    It includes the following attributes:
    """
    #: The URI of the RO-Crate
    rocrate_uri: URI
    # Profile settings
    #: The path to the profiles
    profiles_path: Path = DEFAULT_PROFILES_PATH
    #: The profile identifier to validate against
    profile_identifier: str = DEFAULT_PROFILE_IDENTIFIER
    #: Flag to enable profile inheritance
    enable_profile_inheritance: bool = True
    # Validation settings
    #: Flag to abort on first error
    abort_on_first: Optional[bool] = False
    #: Flag to disable inherited profiles reporting
    disable_inherited_profiles_reporting: bool = False
    #: Flag to disable remote crate download
    disable_remote_crate_download: bool = True
    # Requirement settings
    #: The requirement severity
    requirement_severity: Union[str, Severity] = Severity.REQUIRED
    #: Flag to validate requirement severity only skipping check with lower or higher severity
    requirement_severity_only: bool = False
    # Requirement check settings
    #: Flag to allow requirement check override
    allow_requirement_check_override: bool = True
    #: Flag to disable the check for duplicates
    disable_check_for_duplicates: bool = False
    #: Checks to skip
    skip_checks: list[str] = None

    def __post_init__(self):
        # if requirement_severity is a str, convert to Severity
        if isinstance(self.requirement_severity, str):
            self.requirement_severity = Severity[self.requirement_severity]

    def to_dict(self):
        """
        Convert the ValidationSettings to a dictionary
        """
        result = asdict(self)
        result['rocrate_uri'] = str(self.rocrate_uri)
        return result

    @property
    def rocrate_uri(self) -> Optional[URI]:
        """
        Get the RO-Crate URI

        :return: The RO-Crate URI
        :rtype: URI
        """
        return self._rocrate_uri

    @rocrate_uri.setter
    def rocrate_uri(self, value: URI):
        """
        Set the RO-Crate URI.

        :param value: The RO-Crate URI.
        :type value: URI
        """
        if not value:
            raise ValueError("Invalid RO-Crate URI")
        self._rocrate_uri: URI = URI(value)

    @classmethod
    def parse(cls, settings: Union[dict, ValidationSettings]) -> ValidationSettings:
        """
        Parse the settings to a ValidationSettings object.

        :param settings: The settings to parse.
        :type settings: Union[dict, ValidationSettings]

        :return: The parsed settings.
        :rtype: ValidationSettings

        :raises ValueError: If the settings type is invalid.
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

    def __str__(self) -> str:
        return f"ProfileValidationEvent({self.event_type}, {self.profile})"

    def __repr__(self) -> str:
        return f"ProfileValidationEvent(event_type={self.event_type}, profile={self.profile})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfileValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.profile == other.profile

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.profile))


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

    def __str__(self) -> str:
        return f"RequirementValidationEvent({self.event_type}, {self.requirement})"

    def __repr__(self) -> str:
        return f"RequirementValidationEvent(event_type={self.event_type}, requirement={self.requirement})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.requirement == other.requirement

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.requirement))


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

    def __str__(self) -> str:
        return f"RequirementCheckValidationEvent({self.event_type}, {self.requirement_check})"

    def __repr__(self) -> str:
        return f"RequirementCheckValidationEvent(event_type={self.event_type}, " \
               f"requirement_check={self.requirement_check})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RequirementCheckValidationEvent):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")
        return self.event_type == other.event_type and self.requirement_check == other.requirement_check

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.event_type, self.requirement_check))


class Validator(Publisher):
    """
    Validator class for validating Research Object Crates(RO-Crate)
    against specified profiles according to the validation settings.

    Attributes:
        validation_settings(ValidationSettings): The settings used for validation.

    Methods:
        __init__(settings: Union[str, ValidationSettings]):
            Initializes the Validator with the given settings.
        validation_settings() -> ValidationSettings:
            Returns the validation settings.
        detect_rocrate_profiles() -> list[Profile]:
            Detects the profiles to validate against.
        validate() -> ValidationResult:
            Validate the RO-Crate against the detected profiles according to the validation settings
        validate_requirements(requirements: list[Requirement]) -> ValidationResult:
            Validates the RO-Crate against the specified subset of the profile requirements.
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
            context = ValidationContext(self, self.validation_settings)
            candidate_profiles_uris = set()
            try:
                candidate_profiles_uris.update(context.ro_crate.metadata.get_conforms_to())
            except Exception as e:
                logger.debug("Error while getting candidate profiles URIs: %s", e)
            try:
                candidate_profiles_uris.update(context.ro_crate.metadata.get_root_data_entity_conforms_to())
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
        """
        Validate the RO-Crate against the detected profiles according to the validation settings
        """
        return self.__do_validate__()

    def validate_requirements(self, requirements: list[Requirement]) -> ValidationResult:
        """
        Validates the RO-Crate against the specified subset of the profile requirements
        """
        assert all(isinstance(requirement, Requirement) for requirement in requirements), \
            "Invalid requirement type"
        # perform the requirements validation
        return self.__do_validate__(requirements)

    def __do_validate__(self,
                        requirements: Optional[list[Requirement]] = None) -> ValidationResult:

        # initialize the validation context
        context = ValidationContext(self, self.validation_settings)

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
                passed = requirement._do_validate_(context)
                logger.debug("Requirement %s passed: %s", requirement.identifier, passed)
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
    """
    Class that represents the context for the validation process.
    """

    def __init__(self, validator: Validator, settings: ValidationSettings):
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

        # initialize the ROCrate object
        self._rocrate = ROCrate.new_instance(settings.rocrate_uri)
        assert isinstance(self._rocrate, ROCrate), "Invalid RO-Crate instance"

    @property
    def ro_crate(self) -> ROCrate:
        """
        The RO-Crate instance

        :return: The RO-Crate instance
        :rtype: ROCrate
        """
        return self._rocrate

    @property
    def validator(self) -> Validator:
        """
        The validator instance which this context belongs to

        :return: The validator instance
        :rtype: Validator
        """
        return self._validator

    @property
    def result(self) -> ValidationResult:
        """
        The validation result

        :return: The validation result
        :rtype: ValidationResult
        """
        if self._result is None:
            self._result = ValidationResult(self)
        return self._result

    @property
    def settings(self) -> ValidationSettings:
        """
        The validation settings

        :return: The validation settings
        :rtype: ValidationSettings
        """
        return self._settings

    @property
    def publicID(self) -> str:
        """
        The root URI of the RO-Crate
        """
        path = str(self.ro_crate.uri.base_uri)
        if not path.endswith("/"):
            path = f"{path}/"
        return path

    @property
    def profiles_path(self) -> Path:
        """
        The path to the profiles

        :return: The path to the profiles
        :rtype: Path
        """
        profiles_path = self.settings.profiles_path
        if isinstance(profiles_path, str):
            profiles_path = Path(profiles_path)
        return profiles_path

    @property
    def requirement_severity(self) -> Severity:
        """
        The requirement severity to validate against

        :return: The requirement severity
        :rtype: Severity
        """
        severity = self.settings.requirement_severity
        if isinstance(severity, str):
            severity = Severity[severity]
        elif not isinstance(severity, Severity):
            raise ValueError(f"Invalid severity type: {type(severity)}")
        return severity

    @property
    def requirement_severity_only(self) -> bool:
        """
        Flag to validate requirement severity only skipping check with lower or higher severity

        :return: The flag to validate requirement severity only
        :rtype: bool
        """
        return self.settings.requirement_severity_only

    @property
    def rocrate_uri(self) -> URI:
        """
        The URI of the RO-Crate

        :return: The URI of the RO-Crate
        :rtype: Path
        """
        return self.settings.rocrate_uri

    @property
    def fail_fast(self) -> bool:
        """
        Flag to abort on first error

        :return: The flag to abort on first error
        :rtype: bool
        """
        return self.settings.abort_on_first

    @property
    def rel_fd_path(self) -> Path:
        """
        The relative path to the file descriptor

        :return: The relative path to the file descriptor
        :rtype: Path
        """
        return Path(ROCRATE_METADATA_FILE)

    def __load_data_graph__(self) -> Graph:
        data_graph = Graph()
        logger.debug("Loading RO-Crate metadata of: %s", self.ro_crate.uri)
        _ = data_graph.parse(data=self.ro_crate.metadata.as_dict(),
                             format="json-ld", publicID=self.publicID)
        logger.debug("RO-Crate metadata loaded: %s", data_graph)
        return data_graph

    def get_data_graph(self, refresh: bool = False) -> Graph:
        """
        Utility method to get the data graph of the RO-Crate,
        i.e., the metadata of the RO-Crate as an RDF graph.

        :param refresh: Flag to refresh the data graph
        :type refresh: bool

        :return: The data graph of the RO-Crate
        :rtype: :py:class:rdflib.Graph

        :raises ROCrateMetadataNotFoundError: If the RO-Crate metadata is not found
        """
        # load the data graph
        try:
            if not self._data_graph or refresh:
                self._data_graph = self.__load_data_graph__()
            return self._data_graph
        except (HTTPError, FileNotFoundError) as e:
            logger.debug("Error loading data graph: %s", e)
            raise ROCrateMetadataNotFoundError(self.rocrate_uri)

    @property
    def data_graph(self) -> Graph:
        """
        The data graph of the RO-Crate,
        i.e., the metadata of the RO-Crate as an RDF graph.

        :return: The data graph of the RO-Crate
        :rtype: Graph
        """
        return self.get_data_graph()

    @property
    def inheritance_enabled(self) -> bool:
        """
        Flag which indicates if profile inheritance is enabled

        :return: The flag to enable profile inheritance
        :rtype: bool
        """
        return self.settings.enable_profile_inheritance

    @property
    def profile_identifier(self) -> str:
        """
        The profile identifier to validate against

        :return: The profile identifier
        :rtype: str
        """
        return self.settings.profile_identifier

    @property
    def allow_requirement_check_override(self) -> bool:
        """
        Flag that indicates if requirement check override is allowed

        :return: The flag to allow requirement check override
        :rtype: bool
        """
        return self.settings.allow_requirement_check_override

    @property
    def disable_check_for_duplicates(self) -> bool:
        """
        Flag that indicates if the check for duplicates is disabled

        :return: The flag to disable the check for duplicates
        :rtype: bool
        """
        return self.settings.disable_check_for_duplicates

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
                    self.settings.profile_identifier = profile.identifier
                    logger.debug("Profile with the highest version number: %s", profile)
                # if the profile is found by token, set the profile name to the identifier
                self.settings.profile_identifier = profile.identifier
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
        """
        The profiles to validate against,
        i.e., the target profile and its inherited profiles

        :return: The profiles to validate against
        :rtype: list[Profile]
        """
        if not self._profiles:
            self._profiles = self.__load_profiles__()
        return self._profiles.copy()

    @property
    def target_profile(self) -> Profile:
        """
        The target profile to validate against

        :return: The target profile
        :rtype: Profile
        """
        profiles = self.profiles
        assert len(profiles) > 0, "No profiles to validate"
        return self.profiles[-1]

    def get_profile_by_token(self, token: str) -> list[Profile]:
        """
        Get the profile by token from the profiles to validate against

        :param token: The token of the profile
        :type token: str

        :return: The profile with the given token
        :rtype: Profile
        """
        return [p for p in self.profiles if p.token == token]

    def get_profile_by_identifier(self, identifier: str) -> list[Profile]:
        """
        Get the profile by identifier from the profiles to validate against

        :param identifier: The identifier of the profile
        :type identifier: str

        :return: The profile with the given identifier
        :rtype: Profile
        """
        for p in self.profiles:
            if p.identifier == identifier:
                return p
        raise ProfileNotFound(identifier)
