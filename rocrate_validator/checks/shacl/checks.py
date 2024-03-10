from ...checks import Check as BaseCheck


class Check(BaseCheck):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "SHACL"
        self.description = "SHACL validation"
        self.issues = []

    def check(self):
        pass
