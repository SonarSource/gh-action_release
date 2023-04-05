import io
import os
import unittest
from contextlib import redirect_stdout

from parameterized import parameterized
from release.utils.dryrun import DryRunHelper


class DryRunUtilTest(unittest.TestCase):

    @parameterized.expand([
        "True", "true"
    ])
    def test_is_dry_run_enabled_should_return_true_given_input_is(self, parametrized_value):
        os.environ["INPUT_DRY_RUN"] = parametrized_value

        result = DryRunHelper.is_dry_run_enabled()

        self.assertTrue(result)

    @parameterized.expand([
        "False", "false", "", "some"
    ])
    def test_is_dry_run_enabled_should_return_false_given_input_is(self, parametrized_value):
        os.environ["INPUT_DRY_RUN"] = parametrized_value

        result = DryRunHelper.is_dry_run_enabled()

        self.assertFalse(result)

    def test_init_should_print_disclaimer_given_dry_run_is_true(self):
        os.environ["INPUT_DRY_RUN"] = "true"

        with io.StringIO() as captured_output, redirect_stdout(captured_output):

            DryRunHelper.init()

            printed_text = captured_output.getvalue()
            self.assertTrue(printed_text.startswith(DryRunHelper.disclaimer_message))

    def test_init_should_not_print_disclaimer_given_dry_run_is_false(self):
        os.environ["INPUT_DRY_RUN"] = "false"

        with io.StringIO() as captured_output, redirect_stdout(captured_output):

            DryRunHelper.init()

            printed_text = captured_output.getvalue()
            self.assertFalse(printed_text.startswith(DryRunHelper.disclaimer_message))
