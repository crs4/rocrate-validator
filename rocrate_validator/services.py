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


import shutil
import signal
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path

from rocrate_validator.constants import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_GATEWAY_TIMEOUT,
    ROCRATE_METADATA_FILE,
)
from rocrate_validator.errors import ProfileNotFound
from rocrate_validator.events import Subscriber
from rocrate_validator.models import (
    BatchCrateEntry,
    BatchSession,
    BatchValidationResult,
    Profile,
    Severity,
    ValidationResult,
    ValidationSettings,
    Validator,
)
from rocrate_validator.utils import log as logging
from rocrate_validator.utils.http import HttpRequester
from rocrate_validator.utils.paths import get_batch_session_path, get_profiles_path
from rocrate_validator.utils.uri import URI

# set the default profiles path
DEFAULT_PROFILES_PATH = get_profiles_path()

# set up logging
logger = logging.getLogger(__name__)


def detect_profiles(settings: dict | ValidationSettings) -> list[Profile]:
    # initialize the validator
    validator = __initialise_validator__(settings)
    # detect the profiles
    profiles = validator.detect_rocrate_profiles()
    logger.debug("Profiles detected: %s", profiles)
    return profiles


def validate_metadata_as_dict(
    metadata_dict: dict, settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None
) -> ValidationResult:
    """
    Validate the RO-Crate metadata only against a profile and return the validation result.
    """
    assert metadata_dict is not None, "Metadata dictionary cannot be None"
    assert isinstance(metadata_dict, dict), "Metadata must be a dictionary"
    # set the RO-Crate metadata dictionary in the settings
    if isinstance(settings, dict):
        settings["metadata_dict"] = metadata_dict
        settings["metadata_only"] = True
    else:
        settings.metadata_dict = metadata_dict
        settings.metadata_only = True
    # validate the RO-Crate metadata
    return validate(settings, subscribers)


def validate(settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None) -> ValidationResult:
    """
    Validate a RO-Crate against a profile and return the validation result

    :param settings: the validation settings
    :type settings: Union[dict, ValidationSettings]

    :param subscribers: the list of subscribers
    :type subscribers: Optional[list[Subscriber]]

    :return: the validation result
    :rtype: ValidationResult

    """
    # initialize the validator
    validator = __initialise_validator__(settings, subscribers)
    # validate the RO-Crate
    result = validator.validate()
    logger.debug("Validation completed: %s", result)
    return result


def _build_validator(settings: ValidationSettings, subscribers: list[Subscriber] | None) -> Validator:
    """Create a validator for the given settings and register any subscribers."""
    validator = Validator(settings)
    logger.debug("Validator created. Starting validation...")
    if subscribers:
        for subscriber in subscribers:
            validator.add_subscriber(subscriber)
    return validator


def _extract_and_validate(
    settings: ValidationSettings, subscribers: list[Subscriber] | None, rocrate_path: Path
) -> Validator:
    """Extract a (local or downloaded) zipped RO-Crate to a temp dir and validate it."""
    original_data_path = settings.rocrate_uri
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            with zipfile.ZipFile(rocrate_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)
                logger.debug("RO-Crate extracted to temporary directory: %s", tmp_dir)
            settings.rocrate_uri = URI(str(tmp_dir))
            return _build_validator(settings, subscribers)
        finally:
            if original_data_path is not None:
                settings.rocrate_uri = original_data_path
                logger.debug("Original data path restored: %s", original_data_path)


def _download_remote_rocrate(
    settings: ValidationSettings, subscribers: list[Subscriber] | None, rocrate_path: URI
) -> Validator:
    """Download a remote (http/https/ftp) RO-Crate to a temp file, then extract and validate it."""
    logger.debug("RO-Crate is a remote RO-Crate")
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        requester = HttpRequester()
        offline = bool(getattr(settings, "offline", False))
        # In offline mode, the cache is the only source of truth. Otherwise,
        # bypass the cache to refresh the stored copy so that subsequent
        # offline runs validate against the latest known remote state.
        if offline:
            response = requester.get(rocrate_path.uri, stream=True, allow_redirects=True)
        else:
            response = requester.fetch_fresh(rocrate_path.uri, stream=True, allow_redirects=True)
        with response as r:
            if r.status_code >= HTTP_STATUS_BAD_REQUEST:
                if offline and r.status_code == HTTP_STATUS_GATEWAY_TIMEOUT:
                    raise FileNotFoundError(
                        f"Remote RO-Crate '{rocrate_path.uri}' is not available in the HTTP cache. "
                        f"Validate it online first, or run "
                        f"`rocrate-validator cache warm --crate '{rocrate_path.uri}'`."
                    )
                raise FileNotFoundError(
                    f"Failed to download remote RO-Crate '{rocrate_path.uri}' (status {r.status_code})."
                )
            with Path(tmp_file.name).open("wb") as f:
                shutil.copyfileobj(r.raw, f)
        logger.debug("RO-Crate downloaded to temporary file: %s", tmp_file.name)
        return _extract_and_validate(settings, subscribers, Path(tmp_file.name))


def __initialise_validator__(
    settings: dict | ValidationSettings, subscribers: list[Subscriber] | None = None
) -> Validator:
    """
    Validate a RO-Crate against a profile
    """
    # if settings is a dict, convert to ValidationSettings
    settings = ValidationSettings.parse(settings)

    # parse the rocrate path
    assert settings.rocrate_uri is not None, "RO-Crate URI is required"
    rocrate_path: URI = URI(str(settings.rocrate_uri))
    logger.debug("Validating RO-Crate: %s", rocrate_path)

    # check if the RO-Crate exists
    if (
        not getattr(settings, "metadata_only", False)
        and getattr(settings, "metadata_dict", None) is None
        and not rocrate_path.is_available()
    ):
        raise FileNotFoundError(f"RO-Crate not found: {rocrate_path}")

    # check if remote validation is enabled
    disable_remote_crate_download = settings.disable_remote_crate_download
    logger.debug("Remote validation: %s", disable_remote_crate_download)
    if disable_remote_crate_download:
        return _build_validator(settings, subscribers)

    # Resolve the RO-Crate source: remote URL, local ZIP, or local directory.
    # We support http/https/ftp protocols to download a remote RO-Crate.
    if rocrate_path.scheme in ("http", "https", "ftp"):
        return _download_remote_rocrate(settings, subscribers, rocrate_path)
    if rocrate_path.as_path().suffix == ".zip":
        logger.debug("RO-Crate is a local ZIP file")
        return _extract_and_validate(settings, subscribers, rocrate_path.as_path())
    if rocrate_path.is_local_directory():
        logger.debug("RO-Crate is a local directory")
        settings.rocrate_uri = URI(str(rocrate_path.as_path()))
        return _build_validator(settings, subscribers)
    raise ValueError(
        f"Invalid RO-Crate URI: {rocrate_path}. It MUST be a local directory or a ZIP file (local or remote)."
    )


def discover_ro_crates(
    directory: Path,
    pattern: str = "*",
) -> list[Path]:
    """
    Scan a directory for the RO-Crates it directly contains.

    The directory is treated as the root of a flat list of crates. Only the
    immediate level is inspected; crate payloads (data entities nested inside a
    crate) are intentionally not descended into. A crate is discovered when:

    - the scan directory itself holds an ``ro-crate-metadata.json`` (a crate
      defined directly in the scan root);
    - an immediate subdirectory holds an ``ro-crate-metadata.json``;
    - an immediate entry is a ``.zip`` file (a zipped crate);
    - an immediate file is a detached crate metadata file, i.e. its name ends
      with ``ro-crate-metadata.json`` (e.g. ``crate_0001-ro-crate-metadata.json``);
      several such files can coexist in the same directory.

    All results are filtered by the glob ``pattern`` against the entry name.

    :param directory: the directory to scan
    :param pattern: glob pattern to filter entries by name (default: ``*``)
    :return: sorted list of discovered RO-Crate paths
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    crates: set[Path] = set()

    # The scan root itself may be a crate (its own ``ro-crate-metadata.json``).
    if (directory / ROCRATE_METADATA_FILE).exists() and fnmatch(directory.name, pattern):
        crates.add(directory)

    # Immediate children: subdirectory crates, zipped crates and detached crate
    # metadata files (single pass).
    for entry in directory.iterdir():
        if not fnmatch(entry.name, pattern):
            continue
        if entry.is_dir():
            if (entry / ROCRATE_METADATA_FILE).exists():
                crates.add(entry)
        elif entry.suffix == ".zip":
            crates.add(entry)
        elif entry.name.endswith(ROCRATE_METADATA_FILE) and entry.name != ROCRATE_METADATA_FILE:
            # A detached crate defined directly as a (prefixed) metadata file;
            # the plain ``ro-crate-metadata.json`` is covered by the scan-root
            # check above (it makes the directory itself the crate).
            crates.add(entry)

    return sorted(crates)


def resolve_batch_session_path(
    settings: ValidationSettings,
    scan_root: Path,
    pattern: str,
    profile_identifiers: list[str] | None = None,
    no_auto_profile: bool = False,
) -> Path:
    """
    Resolve the auto-managed session file path for a batch target.

    The path is derived deterministically from the scan root, the discovery
    options and the validation settings that affect the outcome (profiles and
    severity), so that re-running the same command resolves to the same file
    and can be auto-resumed. Changing the profile selection or severity
    intentionally starts a new session.

    The profile part reflects what is *actually* applied per crate: the explicit
    ``profile_identifiers`` list (order-independent), or the auto-detection mode
    when no profile is given. This keeps distinct profile selections (e.g. two
    different multi-profile sets) on separate sessions.
    """
    settings_dict = settings.to_dict() if hasattr(settings, "to_dict") else {}
    if profile_identifiers:
        profile_key = str(sorted(profile_identifiers))
    else:
        # No explicit profile: per-crate auto-detection, or the base-profile
        # fallback when auto-detection is disabled.
        profile_key = f"auto:{not no_auto_profile}"
    # `requirement_severity_only` is dropped by ``ValidationSettings.to_dict()``,
    # so read it from the settings object directly rather than from the dict.
    severity_only = bool(getattr(settings, "requirement_severity_only", settings_dict.get("requirement_severity_only", False)))
    key_parts = [
        str(Path(scan_root).resolve()),
        pattern,
        profile_key,
        str(settings_dict.get("requirement_severity", "")),
        str(severity_only),
    ]
    return get_batch_session_path(key_parts)


def _load_previous_session(session_path: Path | None) -> BatchSession | None:
    """Load an existing batch session for auto-resume, or ``None`` if unavailable."""
    if not session_path or not Path(session_path).exists():
        return None
    try:
        return BatchSession.load(Path(session_path))
    except Exception:
        logger.warning("Could not load batch session at %s; starting a fresh session.", session_path)
        return None


def _prepare_batch_session(
    settings: ValidationSettings,
    rocrate_uris: list[str],
    session_path: Path | None,
    fresh: bool,
) -> tuple[BatchSession, list[str]]:
    """
    Create or auto-resume a batch session and return it together with the
    URIs that still need to be validated.

    A previous session is resumed only when it exists and is *not* already
    completed (i.e. it was interrupted): in that case the crates that were
    already validated are carried over and only the remaining (plus any newly
    discovered) crates are validated. A completed or missing session — or an
    explicit ``fresh`` request — starts a brand-new session that revalidates
    everything.
    """
    settings_dict = settings.to_dict() if hasattr(settings, "to_dict") else {}
    session = BatchSession(
        validation_settings=settings_dict,
        crate_paths=rocrate_uris,
        session_path=session_path,
    )

    previous = None if fresh else _load_previous_session(session_path)
    if previous is None or previous.is_completed():
        return session, list(rocrate_uris)

    # Resume an interrupted session: carry over already-completed crates and
    # validate the rest. Newly discovered crates are included as pending.
    completed = {e.path: e for e in previous.crates if e.status == "completed"}
    session.crates = [completed.get(p) or BatchCrateEntry(path=p, status="pending") for p in rocrate_uris]
    session.total_crates = len(session.crates)
    session.completed_crates = sum(1 for e in session.crates if e.status == "completed")
    session.failed_crates = sum(1 for e in session.crates if e.status == "completed" and e.passed is False)
    pending = [e.path for e in session.crates if e.status != "completed"]
    logger.info(
        "Resuming batch session: %d/%d crates already validated, %d to validate",
        session.completed_crates,
        session.total_crates,
        len(pending),
    )
    return session, pending


def _resolve_crate_profiles(
    settings: ValidationSettings,
    crate_path: str,
    profile_identifiers: list[str] | None,
    no_auto_profile: bool,
) -> list[str]:
    """
    Resolve the profile identifier(s) to validate a single batch crate against.

    Mirrors single-crate behaviour: an explicit ``--profile-identifier`` list wins
    and is applied to every crate; otherwise the profile is auto-detected from the
    crate itself (unless auto-detection is disabled); falling back to the base
    ``ro-crate`` profile when nothing can be resolved.
    """
    if profile_identifiers:
        return list(profile_identifiers)
    if not no_auto_profile:
        try:
            crate_settings_dict = settings.to_dict() if hasattr(settings, "to_dict") else {}
            crate_settings = ValidationSettings.parse({**crate_settings_dict, "rocrate_uri": str(crate_path)})
            detected = detect_profiles(crate_settings)
            if detected:
                return [p.identifier for p in detected]
        except Exception as e:  # pragma: no cover - detection is best-effort
            logger.debug("Per-crate profile auto-detection failed for %s: %s", crate_path, e)
    return ["ro-crate"]


def _validate_one_in_batch(
    settings: ValidationSettings,
    session: BatchSession,
    crate_path: str,
    idx: int,
    total: int,
    progress_callback: Callable[..., None] | None,
    profile_identifiers: list[str] | None = None,
    no_auto_profile: bool = False,
) -> list[tuple[str, ValidationResult]] | None:
    """
    Validate a single crate inside a batch, updating the session and emitting progress.

    The crate is validated against each profile resolved for it (see
    :func:`_resolve_crate_profiles`) and the per-profile outcomes are combined into
    a single session entry (the crate passes only when it passes every profile).

    Returns the list of ``(path, result)`` pairs (one per profile) on success, or
    ``None`` if validation raised.
    """
    start = time.time()
    entry = session._find_entry(str(crate_path))
    if entry:
        entry.status = "in_progress"
    if progress_callback:
        progress_callback(str(crate_path), idx + 1, total, "validating", None)

    try:
        crate_settings_dict = settings.to_dict() if hasattr(settings, "to_dict") else {}
        profiles = _resolve_crate_profiles(settings, str(crate_path), profile_identifiers, no_auto_profile)
        profile_results: list[tuple[str, ValidationResult]] = []
        for profile in profiles:
            crate_settings = ValidationSettings.parse(
                {
                    **crate_settings_dict,
                    "rocrate_uri": str(crate_path),
                    "profile_identifier": profile,
                }
            )
            profile_results.append((profile, validate(crate_settings)))
        session.add_results(str(crate_path), profile_results, time.time() - start)
        if progress_callback:
            passed = all(r.passed() for _, r in profile_results)
            status = "passed" if passed else "failed"
            total_issues = sum(len(r.issues) for _, r in profile_results)
            # The view styles the line; pass the issue-count message and the
            # profile(s) the crate was validated against separately.
            progress_callback(str(crate_path), idx + 1, total, status, f"({total_issues} issues)", profiles)
        return [(str(crate_path), r) for _, r in profile_results]
    except Exception as e:
        session.mark_failed(str(crate_path), str(e), time.time() - start)
        if progress_callback:
            progress_callback(str(crate_path), idx + 1, total, "error", str(e))
        return None


# Minimum interval between incremental session saves during a batch run. The
# session is always saved once more at the end, so this only throttles the
# intermediate (crash/interrupt-recovery) saves.
_SESSION_SAVE_INTERVAL_SECONDS = 2.0


def batch_validate(
    settings: ValidationSettings,
    rocrate_uris: list[str],
    session_path: Path | None = None,
    fresh: bool = False,
    progress_callback: Callable | None = None,
    profile_identifiers: list[str] | None = None,
    no_auto_profile: bool = False,
) -> BatchValidationResult:
    """
    Validate multiple RO-Crates in batch mode.

    The batch session is always persisted incrementally to ``session_path`` and
    auto-resumed when an interrupted session for the same target already exists
    (unless ``fresh`` is set). The session path is managed automatically by the
    caller (see :func:`resolve_batch_session_path`); callers do not need to
    supply or track a session file by hand.

    Profiles are resolved *per crate*: an explicit ``profile_identifiers`` list is
    applied to every crate, otherwise each crate's profile is auto-detected
    (unless ``no_auto_profile`` is set), matching single-crate validation.

    :param settings: shared validation settings (severity, cache, availability, etc.)
    :param rocrate_uris: list of RO-Crate paths to validate
    :param session_path: auto-managed path where the session is saved/resumed
    :param fresh: ignore any existing session and revalidate everything
    :param progress_callback: optional callable(crate_path, index, total, status, message)
    :param profile_identifiers: explicit profiles to validate every crate against
    :param no_auto_profile: disable per-crate profile auto-detection
    :return: aggregated batch validation result
    """
    session, rocrate_uris = _prepare_batch_session(settings, rocrate_uris, session_path, fresh)
    # Persist the profile resolution options on the session so it can be resumed
    # later (e.g. via `sessions resume`) with exactly the same criteria.
    session.profile_identifiers = list(profile_identifiers) if profile_identifiers else None
    session.no_auto_profile = no_auto_profile
    session.requirement_severity_only = bool(getattr(settings, "requirement_severity_only", False))
    results: list[tuple[str, ValidationResult]] = []

    # Register SIGINT handler for graceful interruption
    def _sigint_handler(_signum, _frame):
        session.status = "interrupted"
        session.save()
        print("\n⚠  Batch interrupted. Re-run the same command to resume.", file=sys.stderr)
        sys.exit(130)

    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _sigint_handler)

    try:
        total = len(rocrate_uris)
        last_save = time.time()
        for idx, crate_path in enumerate(rocrate_uris):
            outcome = _validate_one_in_batch(
                settings,
                session,
                crate_path,
                idx,
                total,
                progress_callback,
                profile_identifiers,
                no_auto_profile,
            )
            if outcome is not None:
                results.extend(outcome)
            # Save the session incrementally for crash/interrupt recovery, but
            # throttle it: re-serialising the whole (possibly large) session
            # after every crate is O(n^2) and dominates the run for big batches.
            now = time.time()
            if now - last_save >= _SESSION_SAVE_INTERVAL_SECONDS:
                session.save()
                last_save = now
    finally:
        signal.signal(signal.SIGINT, original_handler)

    # Final save (always). Announce it first so the UI can show activity, since
    # writing a large session to disk may take a moment.
    if progress_callback:
        progress_callback("", total, total, "saving", None)
    session.status = "completed" if session.is_completed() else "interrupted"
    session.save()

    return BatchValidationResult(session, results)


def get_profiles(
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    severity=Severity.OPTIONAL,
    allow_requirement_check_override: bool = ValidationSettings.allow_requirement_check_override,
) -> list[Profile]:
    """
    Get the list of profiles supported by the package.
    The profile source path can be overridden by specifying ``profiles_path``.

    :param profiles_path: the path to the profiles directory
    :type profiles_path: Path

    :param severity: the severity level
    :type severity: Severity

    :param allow_requirement_check_override: a flag to enable or disable
        the requirement check override (default: ``True``).
        If ``True``, the requirement check of a profile ``A`` can be overridden
        by the requirement check of a profile extension ``B`` (i.e., when ``B extends A``)
        if they share the same name.
        If ``False``, a profile extension ``B`` can only
        add new requirements to the profile ``A`` (i.e., checks with name not present in ``A``)
        and an error is raised if a check with the same name is found in both profiles.
    :type allow_requirement_check_override: bool

    :return: the list of profiles
    :rtype: list[Profile]
    """
    profiles = Profile.load_profiles(
        profiles_path,
        extra_profiles_path=extra_profiles_path,
        severity=severity,
        allow_requirement_check_override=allow_requirement_check_override,
    )
    logger.debug("Profiles loaded: %s", profiles)
    return profiles


def get_profile(
    profile_identifier: str,
    profiles_path: Path = DEFAULT_PROFILES_PATH,
    extra_profiles_path: Path | None = None,
    severity=Severity.OPTIONAL,
    allow_requirement_check_override: bool = ValidationSettings.allow_requirement_check_override,
) -> Profile:
    """
    Get the profile with the given identifier.
    The profile source path can be overridden through ``profiles_path``.
    The profile is loaded based on the given severity level and the requirement check override flag.

    :param profile_identifier: the profile identifier
    :type profile_identifier: str

    :param profiles_path: the path to the profiles directory
    :type profiles_path: Path

    :param severity: the severity level
    :type severity: Severity

    :param allow_requirement_check_override: a flag to enable or disable
        the requirement check override (default: ``True``).
        If ``True``, the requirement check of a profile ``A`` can be overridden
        by the requirement check of a profile extension ``B`` (i.e., when ``B extends A``)
        if they share the same name.
        If ``False``, a profile extension ``B`` can only
        add new requirements to the profile ``A`` (i.e., checks with name not present in ``A``)
        and an error is raised if a check with the same name is found in both profiles.
    :type allow_requirement_check_override: bool

    :return: the profile
    :rtype: Profile

    """
    profiles = get_profiles(
        profiles_path,
        extra_profiles_path=extra_profiles_path,
        severity=severity,
        allow_requirement_check_override=allow_requirement_check_override,
    )
    profile = Profile.find_in_list(profiles, profile_identifier)
    if profile is None:
        raise ProfileNotFound(profile_identifier)
    return profile
