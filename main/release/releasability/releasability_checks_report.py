from typing import List

from release.releasability.releasability_check_result import ReleasabilityCheckResult


class ReleasabilityChecksReport:

    NEW_LINE = "\n"

    def __init__(self):
        self.__checks = list[ReleasabilityCheckResult]()

    def add_check(self, check: ReleasabilityCheckResult):
        self.__checks.append(check)

    def get_checks(self) -> List[ReleasabilityCheckResult]:
        return self.__checks

    def __str__(self):
        return self.NEW_LINE.join(str(check) for check in self.__checks)

    def contains_error(self) -> bool:
        return any(filter(lambda check: (check.passed is not True), self.__checks))
