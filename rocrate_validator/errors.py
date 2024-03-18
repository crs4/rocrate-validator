class OutOfValidationContext(Exception):
    def __init__(self, message: str = None):
        self._message = message

    @property
    def message(self) -> str:
        return self._message

    def __str__(self):
        return self._message

    def __repr__(self):
        return f"OutOfValidationContext({self._message!r})"


class InvalidSerializationFormat(Exception):
    def __init__(self, format: str = None):
        self._format = format

    @property
    def format(self):
        return self._format

    def __str__(self):
        return f"Invalid serialization format: {self._format!r}"

    def __repr__(self):
        return f"InvalidSerializationFormat({self._format!r})"


class ValidationError(Exception):
    def __init__(self, message, path: str = ".", code: int = -1):
        self._message = message
        self._path = path
        self._code = code

    @property
    def message(self) -> str:
        return self._message

    @property
    def path(self) -> str:
        return self._path

    @property
    def code(self) -> int:
        return self._code

    def __str__(self):
        return self._message

    def __repr__(self):
        return f"ValidationError({self._message!r}, {self._path!r})"


class CheckValidationError(ValidationError):
    def __init__(self, check, message, path: str = ".", code: int = -1):
        super().__init__(message, path, code)
        self._check = check

    @property
    def check(self):
        return self._check

    def __repr__(self):
        return f"CheckValidationError({self._check!r}, {self._message!r}, {self._path!r})"
