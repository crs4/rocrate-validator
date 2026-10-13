"""Structured results returned by automatic profile detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Sequence

from rocrate_validator.models._logging import logger
from rocrate_validator.models.profile import Profile
from rocrate_validator.rocrate.entity import ROCrateEntity

if TYPE_CHECKING:
    from rocrate_validator.models.validation import ValidationContext


@dataclass(frozen=True)
class ProfileDetectionDiagnostic:
    """Explain a metadata value that could not be used for profile detection."""

    code: str
    property: str | None
    location: str | None
    value: Any
    message: str


@dataclass
class ProfileDetectionResult:
    """Detected profiles, diagnostics, and an optional user-confirmable suggestion."""

    profiles: list[Profile]
    diagnostics: list[ProfileDetectionDiagnostic]
    suggested_profile: Profile | None = None


def detect_rocrate_profiles(
    context: ValidationContext,
    profile_loader: Callable[[], Sequence[Profile]] | None = None,
) -> ProfileDetectionResult:
    """Detect profiles from an existing context and describe unresolved metadata hints."""

    # Keep both the parsed references and malformed raw values: references can
    # select profiles, while malformed values are needed for diagnostics and
    # may allow a cautious suggestion when a URI was written as a string.
    hints, malformed_values = _get_profile_hints(context.ro_crate.metadata)
    candidate_profile_uris = {value.id for _, value in hints if isinstance(value.id, str) and value.id}
    diagnostics = [
        ProfileDetectionDiagnostic(
            code="INVALID_REFERENCE" if prop == "about" else "INVALID_CONFORMS_TO",
            property=prop,
            location=location,
            value=value,
            message=(
                "Expected a JSON-LD reference object containing `@id`; "
                'for example, {"@id": "https://example.org/profile"}.'
            ),
        )
        for prop, location, value in malformed_values
    ]
    for diagnostic in diagnostics:
        logger.warning(
            "Cannot use %s `%s` value %r for profile detection: %s",
            diagnostic.location,
            diagnostic.property,
            diagnostic.value,
            diagnostic.message,
        )

    logger.debug("Candidate profiles: %s", candidate_profile_uris)
    has_malformed_profile_hint = any(prop == "conformsTo" for prop, _, _ in malformed_values)
    has_string_profile_hint = any(
        prop == "conformsTo" and isinstance(value, str) for prop, _, value in malformed_values
    )

    # No hint at all is different from a malformed hint: report absence only
    # when the crate supplied no conformsTo value that we could inspect.
    if not candidate_profile_uris and not has_malformed_profile_hint:
        diagnostics.append(
            ProfileDetectionDiagnostic(
                code="NO_PROFILE_HINT",
                property="conformsTo",
                location=None,
                value=None,
                message="No `conformsTo` profile reference was found in the metadata descriptor or Root Data Entity.",
            )
        )
        logger.debug("Unable to determine the profile to validate against")

    # A string conformsTo is the one malformed form for which we can try to
    # identify the intended profile. Other malformed values cannot match a
    # profile, so avoid loading the profile catalog just to return diagnostics.
    if not candidate_profile_uris and not has_string_profile_hint:
        logger.debug("No usable profile URI or string suggestion candidate found")
        return ProfileDetectionResult([], diagnostics)

    # Load profiles if valid URIs need matching or a string value might support
    # a suggestion. The latter is never treated as a detected profile here.
    if profile_loader is None:
        available_profiles = Profile.load_profiles(
            context.profiles_path,
            extra_profiles_path=context.extra_profiles_path,
            publicID=context.publicID,
            severity=context.requirement_severity,
        )
    else:
        available_profiles = profile_loader()
    matched_profiles = [profile for profile in available_profiles if profile.uri in candidate_profile_uris]
    candidate_profiles = []
    for profile in matched_profiles:
        candidate_profiles.append(profile)
        for inherited_profile in profile.inherited_profiles:
            # Keep the most specific matched profiles; their inherited
            # profiles are applied through the inheritance relationship.
            if inherited_profile in candidate_profiles:
                candidate_profiles.remove(inherited_profile)
    logger.debug("%d Candidate Profiles found: %s", len(candidate_profiles), candidate_profiles)

    unmatched_profile_uris = candidate_profile_uris.difference({profile.uri for profile in matched_profiles})
    logger.debug("Unmatched Candidate Profiles URIs: %s", unmatched_profile_uris)
    if unmatched_profile_uris:
        logger.warning(
            "The conformance to the following profiles could not be verified: %s",
            ", ".join(unmatched_profile_uris),
        )
        for profile_uri in unmatched_profile_uris:
            locations = [location for location, value in hints if value.id == profile_uri]
            diagnostics.append(
                ProfileDetectionDiagnostic(
                    code="PROFILE_NOT_FOUND",
                    property="conformsTo",
                    location=", ".join(locations),
                    value=profile_uri,
                    message="No available validation profile has this URI.",
                )
            )

    # Suggestions are deliberately separate from detected profiles: callers
    # must decide whether to accept one, and validation still checks metadata.
    suggested_profile = _suggest_profile(candidate_profiles, candidate_profile_uris, diagnostics, available_profiles)
    result = ProfileDetectionResult(candidate_profiles, diagnostics, suggested_profile)
    logger.debug("Detailed profile detection result: %s", result)
    return result


def _get_profile_hints(metadata) -> tuple[list[tuple[str, ROCrateEntity]], list[tuple[str, str, Any]]]:
    """Read descriptor and Root Data Entity profile hints and retain their locations."""
    hints: list[tuple[str, ROCrateEntity]] = []
    diagnostics: list[tuple[str, str, Any]] = []
    try:
        descriptor = metadata.get_file_descriptor_entity()
    except Exception:
        # Without a descriptor there is no reliable source for either the
        # descriptor's conformsTo or the Root Data Entity's hints.
        return hints, diagnostics

    root_data_entity = descriptor.get_property("about")
    entities: list[tuple[str, ROCrateEntity]] = [("RO-Crate Metadata Descriptor", descriptor)]
    if isinstance(root_data_entity, ROCrateEntity):
        entities.append(("Root Data Entity", root_data_entity))
    elif root_data_entity is not None:
        # `about` should point to an entity. Preserve a wrong-shaped value as a
        # diagnostic rather than attempting to read properties from it.
        diagnostics.append(("about", "RO-Crate Metadata Descriptor", root_data_entity))

    for location, entity in entities:
        raw_values = entity.get_property("conformsTo", [])
        # JSON-LD permits one value or an array of values for a property.
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        for value in values:
            if value is None:
                continue
            if isinstance(value, ROCrateEntity) and isinstance(value.id, str) and value.id:
                hints.append((location, value))
            else:
                diagnostics.append(("conformsTo", location, value))
    return hints, diagnostics


def _suggest_profile(
    candidates: list[Profile],
    candidate_profile_uris: set[str],
    diagnostics: list[ProfileDetectionDiagnostic],
    available_profiles: list[Profile],
) -> Profile | None:
    """Return one profile only when malformed string form is the sole detection issue."""
    string_diagnostics = [diagnostic for diagnostic in diagnostics if diagnostic.code == "INVALID_CONFORMS_TO"]

    # Do not guess if a valid reference, another kind of metadata problem, or
    # conflicting string values could change which profile the crate intends.
    can_suggest = (
        not candidates
        and not candidate_profile_uris
        and len(string_diagnostics) == len(diagnostics)
        and bool(string_diagnostics)
        and all(isinstance(diagnostic.value, str) for diagnostic in string_diagnostics)
        and len({diagnostic.value for diagnostic in string_diagnostics}) == 1
    )
    if not can_suggest:
        return None

    # Matching must be unique across available profiles; zero matches means
    # unknown URI, while multiple matches would make the suggestion ambiguous.
    suggestion_uri = string_diagnostics[0].value
    matches = [profile for profile in available_profiles if profile.uri == suggestion_uri]
    return matches[0] if len(matches) == 1 else None
