import unittest

from release.releasability.releasability_check_result import ReleasabilityCheckResult


class ReleasabilityCheckResultTest(unittest.TestCase):

    def test_to_string_method_of_successful_check_should_print_expected_output(self):
        successful_check = ReleasabilityCheckResult(
            name="license is valid",
            message="use Sonar license",
            passed=True,
            state="PASSED"
        )

        output = str(successful_check)

        self.assertEquals(output, "✅ license is valid  - use Sonar license")

    def test_to_string_method_of_failed_check_should_print_expected_output(self):
        failed_check = ReleasabilityCheckResult(
            name="license is not valid",
            message="use BSD license",
            passed=False,
            state="ERROR"
        )

        output = str(failed_check)

        self.assertEquals(output, "❌ license is not valid  - use BSD license")

    def test_to_string_method_of_not_relevant_check_should_print_expected_output(self):
        failed_check = ReleasabilityCheckResult(
            name="emacs vs vim",
            message="choose your battle",
            passed=True,
            state="NOT_RELEVANT"
        )

        output = str(failed_check)

        self.assertEquals(output, "✓ emacs vs vim  - choose your battle")
