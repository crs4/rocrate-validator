from rocrate_validator.models import ValidationContext
from rocrate_validator.requirements.python import PyFunctionCheck, check, requirement


@requirement(name="Source checks")
class SourceChecks(PyFunctionCheck):
    @check(name="Shared check")
    def shared_check(self, _context: ValidationContext) -> bool:
        """Check implemented by both the source and overlay profiles."""
        return True

    @check(name="Inherited check")
    def inherited_check(self, _context: ValidationContext) -> bool:
        """Check implemented only by the source profile."""
        return True
