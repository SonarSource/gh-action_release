import unittest

from utils.burgr import format_ra_check, format_failed_releasability

class TestBurgr(unittest.TestCase):

  def test_format_ra_check_passed(self):
    passed = {'name': 'QA', 'state': 'PASSED'}
    self.assertEqual(format_ra_check(passed), '* \u2705 QA: PASSED')

  def test_format_ra_check_failed(self):
    failed = {'name': 'Jira', 'state': 'FAILED', 'message': 'Ticket SLCORE-305 is still Resolved. Ticket SLCORE-300 is still Open.'}
    self.assertEqual(format_ra_check(failed), '* \u274c Jira: FAILED - Ticket SLCORE-305 is still Resolved. Ticket SLCORE-300 is still Open.')

  def test_format_ra_result(self):
    # Example taken from an actual burgr response
    failed_ra = {
      "kee": "19cee9e3-f2b3-4c5d-9cb9-f9fcd2a04935",
      "pipeline": "29791",
      "number": "3052",
      "name": "releasability",
      "system": "releasability",
      "type": "releasability",
      "url": "http:/#",
      "status": "failed",
      "started_at": "2021-04-07T14:16:39Z",
      "finished_at": "2021-04-07T14:16:50Z",
      "metadata": "{\"state\":\"FAILED\",\"checks\":[{\"name\":\"QA\",\"state\":\"PASSED\"},{\"name\":\"CheckDependencies\",\"state\":\"PASSED\"},{\"name\":\"GitHub\",\"state\":\"NOT_RELEVANT\"},{\"name\":\"CheckManifestValues\",\"state\":\"PASSED\"},{\"name\":\"ParentPOM\",\"state\":\"PASSED\"},{\"name\":\"Jira\",\"state\":\"FAILED\",\"message\":\"Ticket SLCORE-305 is still Resolved. Ticket SLCORE-300 is still Open.\"},{\"name\":\"QualityGate\",\"state\":\"PASSED\"}]}",
      "statusColor": "RED"
    }
    self.assertEqual(format_failed_releasability(failed_ra),
                     '''* \u2705 QA: PASSED
* \u2705 CheckDependencies: PASSED
* \u2705 CheckManifestValues: PASSED
* \u2705 ParentPOM: PASSED
* \u274c Jira: FAILED - Ticket SLCORE-305 is still Resolved. Ticket SLCORE-300 is still Open.
* \u2705 QualityGate: PASSED'''
    )
