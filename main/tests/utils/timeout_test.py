import time
import unittest

from release.utils.timeout import has_exceeded_timeout


class TimeoutTest(unittest.TestCase):
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def setUp(self):
        # Define the emulated time
        self.emulated_time = time.mktime(
            time.strptime("1971-06-28 01:23:45", TimeoutTest.DATETIME_FORMAT))

        # Register the time.time function and patch it then
        self.original_time_method = time.time
        time.time = self._get_mocked_time

    def tearDown(self):
        # Restore the original time.time function
        time.time = self.original_time_method

    def _get_mocked_time(self):
        """
        Returns: emulated time
        """
        return self.emulated_time

    def _set_mocked_time(self, moment: str):
        """
        Defines emulated time
        Args:
            moment: Date time in format TimeoutTest.DATETIME_FORMAT to set so that time.time() will
            return it
        """
        self.emulated_time = time.mktime(time.strptime(moment, TimeoutTest.DATETIME_FORMAT))

    def test_has_exceeded_timeout_should_return_true_given_timeout_expired(self):
        self._set_mocked_time("2024-01-01 00:00:00")

        now = time.time()
        timeout = 10

        self._set_mocked_time(f"2024-01-01 00:00:{timeout + 1}")

        exceeded_timeout = has_exceeded_timeout(now, timeout)

        self.assertTrue(exceeded_timeout)

    def test_has_exceeded_timeout_should_return_false_given_timeout_is_not_strictly_expired(self):
        self._set_mocked_time("2024-01-01 00:00:00")

        now = time.time()
        timeout = 10

        self._set_mocked_time(f"2024-01-01 00:00:{timeout}")

        not_strictly_exceeded_timeout = has_exceeded_timeout(now, timeout)

        self.assertFalse(not_strictly_exceeded_timeout)

    def test_has_exceeded_timeout_should_return_false_given_timeout_is_not_expired(self):
        self._set_mocked_time("2024-01-01 00:00:00")

        now = time.time()
        timeout = 10

        self._set_mocked_time(f"2024-01-01 00:00:{timeout - 5}")

        not_exceeded_timeout = has_exceeded_timeout(now, timeout)

        self.assertFalse(not_exceeded_timeout)
