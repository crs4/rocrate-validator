
from typing import Optional

# from .models import RequirementCheck


class ROCValidatorError(Exception):
    pass


class OutOfValidationContext(ROCValidatorError):
    """Raised when a validation check is called outside of a validation context."""

    def __init__(self, message: Optional[str] = None):
        self._message = message

    @property
    def message(self) -> Optional[str]:
        """The error message."""
        return self._message

    def __str__(self) -> str:
        return str(self._message)

    def __repr__(self):
        return f"OutOfValidationContext({self._message!r})"


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
