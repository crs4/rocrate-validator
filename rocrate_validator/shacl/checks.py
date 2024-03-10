from ..checks import Check


class SHACLCheck(Check):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "SHACL"
        self.description = "SHACL validation"
        self.issues = []

    def check(self):
        pass
