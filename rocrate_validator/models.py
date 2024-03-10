from pathlib import Path
from typing import Dict, List

from .checks import CheckIssue, Severity


class ValidationResult:

    def __init__(self, rocrate_path: Path, validation_settings: Dict = None):
        self._issues: List[CheckIssue] = []
        self._rocrate_path = rocrate_path
        self._validation_settings = validation_settings

    def get_rocrate_path(self):
        return self._rocrate_path

    def get_validation_settings(self):
        return self._validation_settings

    def add_issue(self, issue: CheckIssue):
        self._issues.append(issue)

    def add_issues(self, issues: List[CheckIssue]):
        self._issues.extend(issues)

    def get_issues(self, severity: Severity = Severity.WARNING) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity.value >= severity.value]

    def get_issues_by_severity(self, severity: Severity) -> List[CheckIssue]:
        return [issue for issue in self._issues if issue.severity == severity]

    def has_issues(self, severity: Severity = Severity.WARNING) -> bool:
        return any(issue.severity.value >= severity.value for issue in self._issues)

    def passed(self, severity: Severity = Severity.WARNING) -> bool:
        return not any(issue.severity.value >= severity.value for issue in self._issues)

    def __str__(self):
        return f"Validation result: {len(self._issues)} issues"

    def __repr__(self):
        return f"ValidationResult(issues={self._issues})"
