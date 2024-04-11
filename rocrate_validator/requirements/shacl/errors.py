from ...errors import ValidationError
from .validator import SHACLValidationResult


class SHACLValidationError(ValidationError):

    def __init__(
        self,
        result: SHACLValidationResult = None,
        message: str = "Document does not conform to SHACL shapes.",
        path: str = ".",
        code: int = 500,
    ):
        super().__init__(message, path, code)
        self._result = result

    @property
    def result(self) -> SHACLValidationResult:
        return self._result

    def __repr__(self):
        return (
            f"SHACLValidationError({self._message!r}, {self._path!r}, {self.result!r})"
        )
