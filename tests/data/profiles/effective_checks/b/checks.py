from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Overlay checks")
class OverlayChecks(PyFunctionCheck):
    @check(name="Shared check")
    def shared_check(self, _context: ValidationContext) -> bool:
        """Local implementation replacing the source profile check."""
        return True
