from typing import List

from release.releasability.releasability_check_result import ReleasabilityCheckResult


class ReleasabilityChecksReport:

    NEW_LINE = "\n"

    def __init__(self, release_check_results: List[ReleasabilityCheckResult]):
        self.__checks = release_check_results

    def __str__(self):
        return self.NEW_LINE.join(str(check) for check in self.__checks)

    def get_checks(self) -> List[ReleasabilityCheckResult]:
        return self.__checks

    def contains_error(self) -> bool:
        return any(filter(lambda check: (check.passed is not True), self.__checks))
