
from typing import Optional


class ROCValidatorError(Exception):
    pass


class ProfilesDirectoryNotFound(ROCValidatorError):
    """Raised when the profiles directory is not found."""

    def __init__(self, profiles_path: Optional[str] = None):
        self._profiles_path = profiles_path

    @property
    def profiles_path(self) -> Optional[str]:
        """The path to the profiles directory."""
        return self._profiles_path

    def __str__(self) -> str:
        return f"Profiles directory not found: {self._profiles_path!r}"

    def __repr__(self):
        return f"ProfilesDirectoryNotFound({self._profiles_path!r})"


class InvalidProfilePath(ROCValidatorError):
    """Raised when an invalid profile path is provided."""

    def __init__(self, profile_path: Optional[str] = None):
        self._profile_path = profile_path

    @property
    def profile_path(self) -> Optional[str]:
        """The invalid profile path."""
        return self._profile_path

    def __str__(self) -> str:
        return f"Invalid profile path: {self._profile_path!r}"

    def __repr__(self):
        return f"InvalidProfilePath({self._profile_path!r})"


class ProfileNotFound(ROCValidatorError):
    """Raised when a profile is not found."""

    def __init__(self, profile_name: Optional[str] = None):
        self._profile_name = profile_name

    @property
    def profile_name(self) -> Optional[str]:
        """The name of the profile."""
        return self._profile_name

    def __str__(self) -> str:
        return f"Profile not found: {self._profile_name!r}"

    def __repr__(self):
        return f"ProfileNotFound({self._profile_name!r})"


class InvalidSerializationFormat(ROCValidatorError):
    """Raised when an invalid serialization format is provided."""

    def __init__(self, format: Optional[str] = None):
        self._format = format

    @property
    def serialization_format(self) -> Optional[str]:
        """The invalid serialization format."""
        return self._format

    def __str__(self) -> str:
        return f"Invalid serialization format: {self._format!r}"

    def __repr__(self):
        return f"InvalidSerializationFormat({self._format!r})"


class BadSyntaxError(ROCValidatorError):
    """Raised when a syntax error occurs."""

    def __init__(self, message, path: str = ".", code: int = -1):
        self._message = message
        self._path = path
        self._code = code

    @property
    def message(self) -> str:
        """The error message."""
        return self._message

    @property
    def path(self) -> str:
        """The path where the error occurred."""
        return self._path

    @property
    def code(self) -> int:
        """The error code."""
        return self._code

    def __str__(self) -> str:
        return self._message

    def __repr__(self):
        return f"BadSyntaxError({self._message!r}, {self._path!r})"


class ValidationError(ROCValidatorError):
    """Raised when a validation error occurs."""

    def __init__(self, message, path: str = ".", code: int = -1):
        self._message = message
        self._path = path
        self._code = code

    @property
    def message(self) -> str:
        """The error message."""
        return self._message

    @property
    def path(self) -> str:
        """The path where the error occurred."""
        return self._path

    @property
    def code(self) -> int:
        """The error code."""
        return self._code

    def __str__(self) -> str:
        return self._message

    def __repr__(self):
        return f"ValidationError({self._message!r}, {self._path!r})"


class CheckValidationError(ValidationError):
    """Raised when a validation check fails."""

    def __init__(self,
                 check,
                 message,
                 path: str = ".",
                 code: int = -1):
        super().__init__(message, path, code)
        self._check = check

    @property
    def check(self):
        """The check that failed."""
        return self._check

    def __repr__(self):
        return f"CheckValidationError({self._check!r}, {self._message!r}, {self._path!r})"
