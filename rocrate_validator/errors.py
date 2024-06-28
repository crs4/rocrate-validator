
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


class ProfileSpecificationNotFound(ROCValidatorError):
    """Raised when the profile specification is not found."""

    def __init__(self, profile_name: Optional[str] = None, spec_file: Optional[str] = None):
        self._profile_name = profile_name
        self._spec_file = spec_file

    @property
    def profile_name(self) -> Optional[str]:
        """The name of the profile."""
        return self._profile_name

    @property
    def spec_file(self) -> Optional[str]:
        """The name of the profile specification file."""
        return self._spec_file

    def __str__(self) -> str:
        msg = f"Unable to find the `profile.ttl` specification for the profile \"{self._profile_name!r}\""
        if self._spec_file:
            msg += f" in the file {self._spec_file!r}"
        return msg

    def __repr__(self):
        return f"ProfileSpecificationNotFound({self._profile_name!r})"


class ProfileSpecificationError(ROCValidatorError):

    def __init__(self, profile_name: Optional[str] = None, message: Optional[str] = None):
        self._profile_name = profile_name
        self._message = message

    @property
    def profile_name(self) -> Optional[str]:
        """The name of the profile."""
        return self._profile_name

    @property
    def message(self) -> Optional[str]:
        """The error message."""
        return self._message

    def __str__(self) -> str:
        return f"Error in the `profile.ttl` specification for the profile \"{self._profile_name!r}\": {self._message!r}"

    def __repr__(self):
        return f"ProfileSpecificationError({self._profile_name!r}, {self._message!r})"


class DuplicateRequirementCheck(ROCValidatorError):
    """Raised when a duplicate requirement check is found."""

    def __init__(self, check_name: str, profile_name: Optional[str] = None):
        self._check_name = check_name
        self._profile_name = profile_name

    @property
    def check_name(self) -> str:
        """The name of the duplicate requirement check."""
        return self._check_name

    @property
    def profile_name(self) -> Optional[str]:
        """The name of the profile."""
        return self._profile_name

    def __str__(self) -> str:
        return f"Duplicate requirement check found: {self._check_name!r} in profile {self._profile_name!r}"

    def __repr__(self):
        return f"DuplicateRequirementCheck({self._check_name!r}, {self._profile_name!r})"


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
