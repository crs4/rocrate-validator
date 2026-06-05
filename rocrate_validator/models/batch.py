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

import json
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rocrate_validator import __version__
from rocrate_validator.models.result import CustomEncoder, ValidationResult


@dataclass
class BatchCrateEntry:
    """Represents a single entry in a batch validation session."""

    path: str
    status: str  # pending | in_progress | completed | failed | skipped
    passed: bool | None = None
    duration: float | None = None
    error: str | None = None
    issues: list[Any] | None = None  # serialized CheckIssue dicts
    statistics: dict[str, Any] | None = None  # ValidationStatistics.to_dict()
    size_bytes: int | None = None  # disk size of the crate at validation time
    profiles: list[str] | None = None  # profile identifier(s) the crate was validated against

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "passed": self.passed,
            "profiles": self.profiles or [],
            "duration": self.duration,
            "error": self.error,
            "issues": self.issues or [],
            "statistics": self.statistics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BatchCrateEntry:
        field_names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})


class BatchSession:
    """
    Manages a batch validation session with incremental save/resume support.
    """

    SESSION_VERSION = "1.0"

    def __init__(
        self,
        validation_settings: dict,
        crate_paths: list[str],
        session_path: Path | None = None,
    ):
        self.version: str = self.SESSION_VERSION
        self.rocrate_validator_version: str = __version__
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = self.created_at
        self.status: str = "in_progress"
        self.total_crates: int = len(crate_paths)
        self.completed_crates: int = 0
        self.failed_crates: int = 0
        self.validation_settings: dict = validation_settings
        self.session_path: Path | None = session_path
        self.crates: list[BatchCrateEntry] = [BatchCrateEntry(path=p, status="pending") for p in crate_paths]
        # Per-crate profile resolution options, persisted so an interrupted
        # session can be resumed (via `sessions resume`) with the exact same
        # criteria even outside the original `validate` invocation.
        self.profile_identifiers: list[str] | None = None
        self.no_auto_profile: bool = False
        # `requirement_severity_only` is dropped by ``ValidationSettings.to_dict()``,
        # so it is tracked here to faithfully reconstruct the settings on resume.
        self.requirement_severity_only: bool = False

    @staticmethod
    def _compute_size_bytes(crate_path: str) -> int | None:
        """Return total disk size in bytes for a crate path, or None on error."""
        try:
            p = Path(crate_path)
            if p.is_dir():
                return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            if p.is_file():
                return p.stat().st_size
        except OSError:
            pass
        return None

    def add_result(self, crate_path: str, result: ValidationResult, duration: float):
        """Record a single-profile validation result for a crate."""
        self.add_results(crate_path, [result], duration)

    def add_results(
        self,
        crate_path: str,
        results: list[ValidationResult] | list[tuple[str, ValidationResult]],
        duration: float,
    ):
        """
        Record the validation result(s) for a crate and update session state.

        A crate may be validated against more than one profile; in that case the
        per-profile outcomes are combined: the crate passes only when it passes
        every profile, its issues are the union across profiles, and the headline
        statistics counters are summed.
        """
        entry = self._find_entry(crate_path)
        if entry is None:
            return
        # Accept both bare results and (profile, result) pairs.
        normalized = [r[1] if isinstance(r, tuple) else r for r in results]
        profiles = [r[0] for r in results if isinstance(r, tuple) and r[0]]
        passed = all(r.passed() for r in normalized)
        issues: list[Any] = []
        for r in normalized:
            issues.extend(i.to_dict() for i in r.issues)
        entry.status = "completed"
        entry.passed = passed
        entry.profiles = profiles or None
        entry.duration = duration
        entry.issues = issues
        entry.statistics = self._aggregate_statistics(normalized)
        entry.size_bytes = self._compute_size_bytes(crate_path)
        self.completed_crates += 1
        if not passed:
            self.failed_crates += 1

    @staticmethod
    def _aggregate_statistics(results: list[ValidationResult]) -> dict[str, Any] | None:
        """
        Combine the statistics of one or more per-profile results into one dict.

        For a single profile the statistics are returned unchanged. For multiple
        profiles the headline counters (``total_checks``, ``total_passed_checks``,
        ``total_failed_checks``) are summed so the batch summary, CSV and JSON
        reports stay consistent.
        """
        stat_dicts = [r.statistics.to_dict() for r in results if r.statistics]
        if not stat_dicts:
            return None
        if len(stat_dicts) == 1:
            return stat_dicts[0]
        aggregated = dict(stat_dicts[0])
        for key in ("total_checks", "total_passed_checks", "total_failed_checks"):
            aggregated[key] = sum(d.get(key, 0) or 0 for d in stat_dicts)
        return aggregated

    def mark_failed(self, crate_path: str, error: str, duration: float = 0.0):
        """Mark a crate as failed with an error message."""
        entry = self._find_entry(crate_path)
        if entry is None:
            return
        entry.status = "failed"
        entry.passed = False
        entry.duration = duration
        entry.error = error
        entry.size_bytes = self._compute_size_bytes(crate_path)
        self.completed_crates += 1
        self.failed_crates += 1

    def get_pending(self) -> list[BatchCrateEntry]:
        """Return entries that still need validation."""
        return [e for e in self.crates if e.status in ("pending", "in_progress")]

    def is_completed(self) -> bool:
        return self.completed_crates >= self.total_crates

    def save(self, path: Path | None = None):
        """Serialize the session to a JSON file."""
        save_path = path or self.session_path
        if save_path is None:
            return
        self.updated_at = datetime.now(timezone.utc)
        if self.is_completed():
            self.status = "completed"
        data = self.to_dict()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with Path(save_path).open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, cls=CustomEncoder)

    def to_dict(self) -> dict:
        return {
            "session": {
                "version": self.version,
                "rocrate_validator_version": self.rocrate_validator_version,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "status": self.status,
                "total_crates": self.total_crates,
                "completed_crates": self.completed_crates,
                "failed_crates": self.failed_crates,
            },
            "validation_settings": self.validation_settings,
            "batch_options": {
                "profile_identifiers": self.profile_identifiers,
                "no_auto_profile": self.no_auto_profile,
                "requirement_severity_only": self.requirement_severity_only,
            },
            "crates": [c.to_dict() for c in self.crates],
        }

    @classmethod
    def load(cls, path: Path) -> BatchSession:
        """Deserialize a session from a JSON file."""
        with Path(path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        session_data = data["session"]
        instance = cls.__new__(cls)
        instance.version = session_data["version"]
        instance.rocrate_validator_version = session_data.get("rocrate_validator_version", "")
        instance.created_at = datetime.fromisoformat(session_data["created_at"])
        instance.updated_at = datetime.fromisoformat(session_data["updated_at"])
        instance.status = session_data["status"]
        instance.total_crates = session_data["total_crates"]
        instance.completed_crates = session_data["completed_crates"]
        instance.failed_crates = session_data["failed_crates"]
        instance.validation_settings = data.get("validation_settings", {})
        batch_options = data.get("batch_options", {})
        instance.profile_identifiers = batch_options.get("profile_identifiers")
        instance.no_auto_profile = bool(batch_options.get("no_auto_profile", False))
        instance.requirement_severity_only = bool(batch_options.get("requirement_severity_only", False))
        instance.session_path = path
        instance.crates = [BatchCrateEntry.from_dict(c) for c in data.get("crates", [])]
        return instance

    def _find_entry(self, crate_path: str) -> BatchCrateEntry | None:
        for e in self.crates:
            if e.path == crate_path:
                return e
        return None


class BatchValidationResult:
    """
    Aggregated result of a batch validation run.

    Headline figures (totals, pass/fail counts, JSON/CSV/summary rows) are
    sourced from the persistent ``session``, so they remain complete even when
    a run resumes a previously interrupted session. The live ``results`` of the
    crates validated in *this* invocation are kept separately and used only for
    the verbose per-crate details, which require the in-memory result objects.
    """

    def __init__(self, session: BatchSession, results: list[tuple[str, ValidationResult]]):
        self.session = session
        self._results = results

    @property
    def results(self) -> list[tuple[str, ValidationResult]]:
        """Live results for the crates validated in the current invocation."""
        return self._results

    @property
    def crates(self) -> list[BatchCrateEntry]:
        """All session entries (complete across resumes), in discovery order."""
        return self.session.crates

    def passed(self) -> bool:
        return self.session.failed_crates == 0 and self.session.is_completed()

    def total_crates(self) -> int:
        return len(self.session.crates)

    def passed_entries(self) -> list[BatchCrateEntry]:
        return [e for e in self.session.crates if e.passed]

    def failed_entries(self) -> list[BatchCrateEntry]:
        return [e for e in self.session.crates if e.status in ("completed", "failed") and not e.passed]

    def to_dict(self) -> dict:
        session_dict = self.session.to_dict()
        session_dict["results"] = [
            {
                "crate": entry.path,
                "profiles": entry.profiles or [],
                "passed": entry.passed,
                "issues": entry.issues or [],
                "statistics": entry.statistics,
            }
            for entry in self.session.crates
        ]
        session_dict["batch_passed"] = self.passed()
        return session_dict

    def to_json(self, path: Path | None = None) -> str:
        result = json.dumps(self.to_dict(), indent=4, cls=CustomEncoder)
        if path:
            with Path(path).open("w", encoding="utf-8") as f:
                f.write(result)
        return result
