

class ReleasabilityCheckResult:
    CHECK_OPTIONAL_PREFIX = "\u2713"
    SUCCESS_PREFIX = "\u2705"
    FAILURE_PREFIX = "\u274c"
    UNKNOWN_PREFIX = "\u2753"

    CHECK_PASSED = 'PASSED'
    CHECK_NOT_RELEVANT = 'NOT_RELEVANT'
    CHECK_FAILED = 'ERROR'

    name: str
    state: str
    passed: bool
    message: str

    def __init__(self, name: str, state: str, message: str = None):
        self.name = name
        self.state = state
        self.message = message
        self.passed = self.has_passed(state)

    def __str__(self):
        prefix = self._get_prefix()

        note = ''
        if self.message is not None:
            note = f' - {self.message}'

        return f'{prefix} {self.name} {note}'

    def _get_prefix(self):
        match self.state:
            case self.CHECK_PASSED:
                return self.SUCCESS_PREFIX
            case self.CHECK_NOT_RELEVANT:
                return self.CHECK_OPTIONAL_PREFIX
            case self.CHECK_FAILED:
                return self.FAILURE_PREFIX
            case _:
                return self.UNKNOWN_PREFIX

    def has_passed(self, state: str) -> bool:
        match state:
            case self.CHECK_PASSED:
                return True
            case self.CHECK_NOT_RELEVANT:
                return True
            case _:
                return False
