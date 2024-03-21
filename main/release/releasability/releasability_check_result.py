

class ReleasabilityCheckResult:
    CHECK_PREFIX = "\u2713"  # TODO: this name is not explicit, should find a better replacement
    SUCCESS_PREFIX = "\u2705"
    FAILURE_PREFIX = "\u274c"

    CHECK_PASSED = 'PASSED'
    CHECK_NOT_RELEVANT = 'NOT_RELEVANT'

    passed: bool  # TODO: passed is not really clear :/ maybe passedOrIgnored or mandatory ?
    name: str
    state: str
    message: str

    def __init__(self, name: str, state: str, passed: bool, message: str = None):
        self.name = name
        self.state = state
        self.passed = passed
        self.message = message

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
                return self.CHECK_PREFIX
            case _:
                return self.FAILURE_PREFIX
