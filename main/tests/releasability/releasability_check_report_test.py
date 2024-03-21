import unittest

from release.releasability.releasability_check_result import ReleasabilityCheckResult
from release.releasability.releasability_checks_report import ReleasabilityChecksReport


class ReleasabilityCheckReportTest(unittest.TestCase):

    def test_contains_error_should_return_true_given_there_is_a_failing_check(self):
        report = ReleasabilityChecksReport()
        report.add_check(self._build_failed_check("failed check"))
        report.add_check(self._build_successful_check("success check"))

        self.assertTrue(report.contains_error())

    def test_contains_error_should_return_false_given_there_is_no_failing_check(self):
        report = ReleasabilityChecksReport()
        report.add_check(self._build_successful_check("success check"))

        self.assertFalse(report.contains_error())

    def test_get_checks_should_contain_all_added_checks(self):
        check_a = self._build_successful_check("check A")
        check_b = self._build_successful_check("check B")
        check_c = self._build_successful_check("check C")

        report = ReleasabilityChecksReport()
        report.add_check(check_a)
        report.add_check(check_b)
        report.add_check(check_c)

        self.assertEquals(3, len(report.get_checks()))
        self.assertIn(check_a, report.get_checks())
        self.assertIn(check_b, report.get_checks())
        self.assertIn(check_c, report.get_checks())

    def test_to_string_should_print_a_new_line_per_check(self):
        failed_check = self._build_failed_check("failed check")
        success_check = self._build_successful_check("success check")

        report = ReleasabilityChecksReport()
        report.add_check(failed_check)
        report.add_check(success_check)

        print(report)

        self.assertMultiLineEqual(
            str(failed_check) + ReleasabilityChecksReport.NEW_LINE + str(success_check),
            str(report)
        )

    def _build_failed_check(self, name: str) -> ReleasabilityCheckResult:
        return ReleasabilityCheckResult(
            name=name,
            message='',
            state=ReleasabilityCheckResult.CHECK_FAILED
        )

    def _build_successful_check(self, name: str) -> ReleasabilityCheckResult:
        return ReleasabilityCheckResult(
            name=name,
            message='',
            state=ReleasabilityCheckResult.CHECK_PASSED
        )
