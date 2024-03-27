class OutOfValidationContext(Exception):
    """Raised when a validation check is called outside of a validation context."""

    def __init__(self, message: str = None):
        self._message = message

    @property
    def message(self) -> str:
        """The error message."""
        return self._message

    def __str__(self):
        return self._message

    def __repr__(self):
        return f"OutOfValidationContext({self._message!r})"


class InvalidSerializationFormat(Exception):
    """Raised when an invalid serialization format is provided."""

    def __init__(self, serialization_format: str = None):
        self._format = serialization_format

    @property
    def serialization_format(self):
        """The invalid serialization format."""
        return self._format

    def __str__(self):
        return f"Invalid serialization format: {self._format!r}"

    def __repr__(self):
        return f"InvalidSerializationFormat({self._format!r})"


class ValidationError(Exception):
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

    def __str__(self):
        return self._message

    def __repr__(self):
        return f"ValidationError({self._message!r}, {self._path!r})"


class CheckValidationError(ValidationError):
    """Raised when a validation check fails."""

    def __init__(self, check, message, path: str = ".", code: int = -1):
        super().__init__(message, path, code)
        self._check = check

    @property
    def check(self):
        """The check that failed."""
        return self._check

    def __repr__(self):
        return f"CheckValidationError({self._check!r}, {self._message!r}, {self._path!r})"
