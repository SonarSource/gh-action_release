import os
import unittest
from unittest.mock import patch, mock_open

from release.releasability_check import do_releasability_checks
from release.utils.burgr import Burgr
from release.utils.releasability import Releasability


class ReleasabilityCheckTest(unittest.TestCase):

    @patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}, clear=True)
    @patch(
        "release.utils.github.json.load",
        return_value={
            "inputs": {"version": "1.0.0.0"},
            "repository": {"default_branch": "master", "full_name": "org/project"},
        },
    )
    @patch.object(Burgr, "start_releasability_checks")
    @patch.object(Releasability, 'start_releasability_checks')
    @patch.object(Releasability, "get_releasability_status")
    def test_releasability_checks_script(
        self,
        json_load_mock,
        burgr_start_releasability_checks,
        releasability_start_releasability_checks,
        releasability_get_releasability_status
    ):
        with patch("release.utils.github.open", mock_open()) as open_mock:
            do_releasability_checks()

            open_mock.assert_called_once()
            json_load_mock.assert_called_once()
            burgr_start_releasability_checks.assert_called_once()
            releasability_start_releasability_checks.assert_called_once()
            releasability_get_releasability_status.assert_called_once()
