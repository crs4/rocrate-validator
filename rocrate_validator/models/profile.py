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

from __future__ import annotations

import re
from functools import total_ordering
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rdflib import RDF, RDFS, Graph, Namespace, URIRef

from rocrate_validator.constants import (
    DEFAULT_PROFILE_README_FILE,
    IGNORED_PROFILE_DIRECTORIES,
    PROF_NS,
    PROFILE_SPECIFICATION_FILE,
    SCHEMA_ORG_NS,
)
from rocrate_validator.errors import (
    DuplicateRequirementCheck,
    InvalidProfilePath,
    ProfileNotFound,
    ProfileSpecificationError,
    ProfileSpecificationNotFound,
)
from rocrate_validator.models._logging import logger
from rocrate_validator.models.severity import Severity
from rocrate_validator.utils.collections import MapIndex, MultiIndexMap

if TYPE_CHECKING:
    from collections.abc import Collection

    from rocrate_validator.models.requirement import Requirement, RequirementCheck

@total_ordering
class Profile:
    """
    RO-Crate Validator profile.

    A profile is a named set of requirements that can be used to validate an RO-Crate.
    """

    # store the map of profiles: profile URI -> Profile instance
    __profiles_map: MultiIndexMap = MultiIndexMap(
        "uri",
        indexes=[
            MapIndex("name"),
            MapIndex("token", unique=False),
            MapIndex("identifier", unique=True),
            MapIndex("token_path", unique=False),
        ],
    )

    def __init__(
        self,
        profiles_base_path: Path,
        profile_path: Path,
        requirements: list[Requirement] | None = None,
        identifier: str | None = None,
        publicID: str | None = None,
        severity: Severity = Severity.REQUIRED,
    ):
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
        self._identifier: str | None = identifier
        self._profiles_base_path = profiles_base_path
        self._profile_path = profile_path
        self._name: str | None = None
        self._description: str | None = None
        self._requirements: list[Requirement] = requirements if requirements is not None else []
        self._publicID = publicID
        self._severity = severity
        self._overrides: list[Profile] = []
        self._overridden_by: list[Profile] = []

        # init property to store the RDF node which is the root of the profile specification graph
        self._profile_node: Any = None

        # init property to store the RDF graph of the profile specification
        self._profile_specification_graph: Graph | None = None

        # check if the profile specification file exists
        spec_file = self.profile_specification_file_path
        if not spec_file or not spec_file.exists():
            raise ProfileSpecificationNotFound(str(spec_file))
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

            # Check if the profile is overriding an existing profile
            existing_profile = self.__profiles_map.get_by_key(cast("Any", self._profile_node).toPython())
            # If an existing profile is being overridden by a different one, log a warning
            if existing_profile and existing_profile.path != profile_path:
                logger.warning(
                    "Profile with identifier %s at %s is being overridden by the profile loaded from %s.",
                    existing_profile.identifier,
                    existing_profile.path,
                    profile_path,
                )
                # add the existing profile as an override
                self.__add_override__(existing_profile)

            # add the profile to the profiles map
            self.__profiles_map.add(
                cast("Any", self._profile_node).toPython(),
                self,
                token=self.token,
                name=self.name,
                identifier=self.identifier,
                token_path=self.__extract_token_from_path__(),
            )  # add the profile to the profiles map
        else:
            raise ProfileSpecificationError(
                message=f"Profile specification file {spec_file} must contain exactly one profile"
            )

    def __get_specification_property__(
        self,
        prop: str,
        namespace: Namespace,
        pop_first: bool = True,
        as_python_object: bool = True,
    ) -> str | list[str | URIRef] | None:
        assert self._profile_specification_graph is not None, "Profile specification graph not loaded"
        nodes = list(self._profile_specification_graph.objects(self._profile_node, namespace[prop]))
        values: list = [cast("Any", v).toPython() for v in nodes] if (nodes and as_python_object) else list(nodes)
        if pop_first:
            return values[0] if values else None
        return values

    def __add_override__(self, profile: Profile):
        """
        Add an override profile to this profile.

        :param profile: the profile that overrides this profile
        :type profile: Profile
        """
        if not isinstance(profile, Profile):
            raise TypeError(f"Expected a Profile instance, got {type(profile)}")
        if profile not in self._overrides:
            self._overrides.append(profile)
            profile._overridden_by.append(self)

    @property
    def overrides(self) -> list[Profile]:
        """
        The list of profiles that override this profile.
        """
        return self._overrides

    @property
    def overridden_by(self) -> list[Profile]:
        """
        The list of profiles that are overridden by this profile.
        """
        return self._overridden_by

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
    def profile_specification_graph(self) -> Graph:
        """
        The RDF graph of the profile specification.
        """
        return self._profile_specification_graph  # type: ignore[return-value]

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
        return self.__get_specification_property__("label", RDFS)  # type: ignore[arg-type]

    @property
    def comment(self):
        """
        The comment added to the profile in the profile specification file
        (i.e., the value of the rdfs: comment property in the `profile.ttl` file).
        """
        return self.__get_specification_property__("comment", RDFS)  # type: ignore[arg-type]

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
        return cast("list[str]", self.__get_specification_property__("isProfileOf", PROF_NS, pop_first=False))

    @property
    def is_transitive_profile_of(self) -> list[str]:
        """
        The list of profiles that this profile is a transitive profile of
        as specified in the profile specification file
        (i.e., the value of the prof: isTransitiveProfileOf property in the `profile.ttl` file).
        """
        return cast("list[str]", self.__get_specification_property__("isTransitiveProfileOf", PROF_NS, pop_first=False))

    @property
    def parents(self) -> list[Profile]:
        """
        The list of profiles that this profile is a profile of
        as specified in the profile specification file.
        """
        return [
            profile
            for profile in (self.__profiles_map.get_by_key(_) for _ in self.is_profile_of)
            if profile is not None
        ]

    @property
    def siblings(self) -> list[Profile]:
        """
        The list of profiles that are siblings of this profile
        (i.e., profiles that share the same parent profile).
        """
        return self.get_sibling_profiles(self)

    @property
    def descendants(self) -> list[Profile]:
        """
        The list of profiles that are descendants of this profile
        (i.e., profiles that have this profile among their inherited profiles).
        """
        return self.get_descendants(self)

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
    def publicID(self) -> str | None:
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
    def description(self) -> str | None:
        """
        The description of the profile as specified in the profile specification file
        (i.e., the value of the rdfs: comment property in the `profile.ttl` file).
        """
        if not self._description:
            if self.path and self.readme_file_path.exists():
                with self.readme_file_path.open(encoding="utf-8") as f:
                    self._description = f.read()
            else:
                comment = self.comment
                self._description = str(comment) if comment else None
        return self._description

    @property
    def requirements(self) -> list[Requirement]:
        """
        The list of requirements of the profile.
        """
        if not self._requirements:
            from rocrate_validator.models.requirement import RequirementLoader  # noqa: PLC0415

            self._requirements = RequirementLoader.load_requirements(self, severity=self.severity)
        return self._requirements

    def get_requirements(self, severity: Severity = Severity.REQUIRED, exact_match: bool = False) -> list[Requirement]:
        """
        Get the requirements of the profile with the given severity level.
        If the exact_match flag is set to `True`, only the requirements with the exact severity level
        are returned; otherwise, the requirements with severity level greater than or equal to
        the given severity level are returned.
        """
        return [
            requirement
            for requirement in self.requirements
            if (not exact_match and (not requirement.severity_from_path or requirement.severity_from_path >= severity))
            or (exact_match and requirement.severity_from_path == severity)
        ]

    def get_requirement(self, name: str) -> Requirement | None:
        """
        Get the requirement with the given name
        """
        for requirement in self.requirements:
            if requirement.name == name:
                return requirement
        return None

    def get_requirement_check(self, check_name: str) -> RequirementCheck | None:
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
        result: list[str] = []
        visited = []
        queue = [source]
        while len(queue) > 0:
            p = queue.pop()
            if p not in visited:
                visited.append(p)
                profile = cls.__profiles_map.get_by_key(p)
                if profile is None:
                    continue
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
        return [
            profile
            for key in inherited_profiles
            if key in profile_keys
            for profile in [self.__profiles_map.get_by_key(key)]
            if isinstance(profile, Profile)
        ]

    def add_requirement(self, requirement: Requirement):
        self._requirements.append(requirement)

    def remove_requirement(self, requirement: Requirement):
        self._requirements.remove(requirement)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Profile) and self.identifier == other.identifier and self.path == other.path

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
            f"Profile(identifier={self.identifier}, name={self.name}, path={self.path}, "
            if self.path
            else f"requirements={self.requirements})"
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.identifier})"

    def to_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
        }

    @staticmethod
    def __extract_version_from_token__(token: str) -> str | None:
        if not token:
            return None
        pattern = r"\Wv?(\d+(\.\d+(\.\d+)?)?)"
        matches = re.findall(pattern, token)
        if matches:
            return matches[-1][0]
        return None

    def __get_consistent_version__(self, candidate_token: str) -> str | None:
        candidates = {
            _
            for _ in [
                cast("str | None", self.__get_specification_property__("version", SCHEMA_ORG_NS)),
                self.__extract_version_from_token__(candidate_token),
                self.__extract_version_from_token__(str(self.path.relative_to(self._profiles_base_path))),
                self.__extract_version_from_token__(str(self.uri)),
            ]
            if _ is not None
        }
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
        return identifier.replace("/", "-")

    def __init_token_version__(self) -> tuple[str, str | None]:
        # try to extract the token from the specs or the path
        candidate_token = cast("str | None", self.__get_specification_property__("hasToken", PROF_NS))
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
    def __load_profile_path__(
        cls,
        profiles_base_path: str | Path,
        profile_path: str | Path,
        publicID: str | None = None,
        severity: Severity = Severity.REQUIRED,
    ) -> Profile:
        # if the path is a string, convert it to a Path
        if isinstance(profile_path, str):
            profile_path = Path(profile_path)
        # check if the path is a directory
        if not profile_path.is_dir():
            raise InvalidProfilePath(str(profile_path))
        # create a new profile
        profile = Profile(
            profiles_base_path=Path(profiles_base_path),
            profile_path=profile_path,
            publicID=publicID,
            severity=severity,
        )
        logger.debug("Loaded profile: %s", profile)
        return profile

    @classmethod
    def __load_profiles_paths__(
        cls,
        profiles_path: str | Path | None = None,
        extra_profiles_path: str | Path | None = None,
    ) -> list[tuple[Path, Path]]:
        """
        Load the paths of the profiles from the given profiles path and extra profiles path.

        :param profiles_path: the path to the profiles directory
        :type profiles_path: Union[str, Path]
        :param extra_profiles_path: an additional path to search for profiles
        :type extra_profiles_path: Union[str, Path]

        :return: a list of tuples containing the root profile directory and the profile directory
        :rtype: list[Tuple[Path, Path]]

        :raises InvalidProfilePath: if the profiles path is not a directory
        """
        result = []
        # set the list of root profile directories
        root_profile_directories = [profiles_path] if profiles_path else []
        if extra_profiles_path is not None and extra_profiles_path != profiles_path:
            root_profile_directories.append(extra_profiles_path)
        # collect profiles nested in the root profile directories
        for root_profile_directory in root_profile_directories:
            # if the path is a string, convert it to a Path
            profile_root_directory = (
                Path(root_profile_directory) if isinstance(root_profile_directory, str) else root_profile_directory
            )
            # check if the path is a directory and raise an error if not
            if not profile_root_directory.is_dir():
                raise InvalidProfilePath(str(profile_root_directory))
            # if the path is a directory, get the profile directories
            result.extend(
                [
                    (profile_root_directory, p.parent)
                    for p in profile_root_directory.rglob("*.*")
                    if p.name == PROFILE_SPECIFICATION_FILE
                ]
            )
        # return the list of profile directories
        return result

    @classmethod
    def load_profiles(
        cls,
        profiles_path: str | Path,
        extra_profiles_path: str | Path | None = None,
        publicID: str | None = None,
        severity: Severity = Severity.REQUIRED,
        allow_requirement_check_override: bool = True,
    ) -> list[Profile]:
        # initialize the profiles list
        profiles: list[Profile] = []
        # calculate the list of profiles path as the subdirectories of the profiles path
        # where the profile specification file is present
        profiles_paths = cls.__load_profiles_paths__(profiles_path, extra_profiles_path)

        # iterate through the directories and load the profiles
        for root_profile_path, profile_path in profiles_paths:
            logger.debug(
                "Checking profile path: %s %s %r",
                profile_path,
                profile_path.is_dir(),
                IGNORED_PROFILE_DIRECTORIES,
            )
            # check if the profile path is a directory and not in the ignored directories
            if profile_path.is_dir() and profile_path not in IGNORED_PROFILE_DIRECTORIES:
                profile = Profile.__load_profile_path__(
                    root_profile_path,
                    profile_path,
                    publicID=publicID,
                    severity=severity,
                )
                # if the profile overrides another profile,
                # remove the overridden profiles from the list of profiles
                # to avoid duplicates and ensure that the most specific profile is used
                if profile.overrides:
                    for overridden_profile in profile.overrides:
                        if overridden_profile in profiles:
                            profiles.remove(overridden_profile)
                # add the profile to the list of profiles
                profiles.append(profile)
                logger.debug("Loaded profile: %s (%s)", profile.identifier, profile.path)

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
        return sorted(
            profiles,
            key=lambda x: f"{len(x.inherited_profiles)}_{x.identifier}",
        )

    @classmethod
    def get_by_identifier(cls, identifier: str) -> Profile | None:
        """
        Get the profile with the given identifier

        :param identifier: the identifier
        :type identifier: str

        :return: the profile
        :rtype: Profile
        """
        profile = cls.__profiles_map.get_by_index("identifier", identifier)
        if isinstance(profile, list):
            return cast("Profile | None", profile[0] if profile else None)
        return cast("Profile | None", profile)

    @classmethod
    def get_by_uri(cls, uri: str) -> Profile | None:
        """
        Get the profile with the given URI

        :param uri: the URI
        :type uri: str

        :return: the profile
        :rtype: Profile
        """
        return cast("Profile | None", cls.__profiles_map.get_by_key(uri))

    @classmethod
    def get_by_name(cls, name: str) -> list[Profile]:
        """
        Get the profile with the given name

        :param name: the name
        :type name: str

        :return: the profile
        :rtype: Profile
        """
        return cast("list[Profile]", cls.__profiles_map.get_by_index("name", name) or [])

    @classmethod
    def get_by_token(cls, token: str) -> list[Profile]:
        """
        Get the profile with the given token

        :param token: the token
        :type token: str

        :return: the profile
        :rtype: Profile
        """
        return cast("list[Profile]", cls.__profiles_map.get_by_index("token", token) or [])

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
    def get_descendants(cls, profile: Profile) -> list[Profile]:
        """
        Get the transitive descendants of the given profile (any profile
        that has `profile` among its `inherited_profiles`).

        :param profile: the profile
        :type profile: Profile

        :return: the list of descendant profiles
        :rtype: list[Profile]
        """
        return [p for p in cls.__profiles_map.values() if profile in p.inherited_profiles]

    @classmethod
    def all(cls) -> list[Profile]:
        """
        Get all the profiles

        :return: the list of profiles
        :rtype: list[Profile]
        """
        return list(cls.__profiles_map.values())

    @classmethod
    def find_in_list(cls, profiles: Collection[Profile], profile_identifier: str) -> Profile | None:
        """
        Find a profile with the given identifier in the given list of profiles

        :param profiles: the list of profiles
        :type profiles: Collection[Profile]

        :param identifier: the identifier
        :type identifier: str

        :return: the profile if found, None otherwise
        :rtype: Optional[Profile]
        """
        profile = next((p for p in profiles if p.identifier == profile_identifier), None) or next(
            (p for p in profiles if str(p.identifier).replace(f"-{p.version}", "") == profile_identifier),
            None,
        )
        if not profile:
            raise ProfileNotFound(profile_identifier)
        return profile
