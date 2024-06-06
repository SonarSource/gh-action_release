#!/usr/bin/python

import json
import os
import unittest
from unittest.mock import patch
from main import prepare_logs, push_logs


class TestDatadogIngest(unittest.TestCase):

    def test_prepare_logs(self):
        os.environ['run_id'] = 'run_id1'
        os.environ['repo'] = 'repo1'
        os.environ['releasabilityWhiteSource'] = 'PASSED'
        os.environ['releasabilityCheckDependencies'] = 'PASSED'
        os.environ['releasabilityQualityGate'] = 'PASSED'
        os.environ['releasabilityGitHub'] = 'PASSED'
        os.environ['releasabilityQA'] = 'PASSED'
        os.environ['releasabilityCheckManifestValues'] = 'PASSED'
        os.environ['releasabilityJira'] = 'PASSED'
        os.environ['releasabilityCheckPeacheeLanguagesStatistics'] = 'PASSED'
        os.environ['releasabilityParentPOM'] = 'PASSED'
        os.environ['release_passed'] = 'success'
        os.environ['maven_central_published'] = 'success'
        os.environ['javadoc_published'] = 'success'
        os.environ['testpypi_published'] = 'success'
        os.environ['pypi_published'] = 'success'
        os.environ['status'] = 'true'

        actual = prepare_logs()
        expected = [{
            'run_id': 'run_id1',
            'source': 'github',
            'message': 'https://github.com/repo1/actions/runs/run_id1',
            'service': 'gh-action_release',
            'repo': 'repo1',
            'releasability_checks': {
                'whitesource': 'PASSED',
                'dependencies': 'PASSED',
                'qualitygate': 'PASSED',
                'github': 'PASSED',
                'qa': 'PASSED',
                'manifest_values': 'PASSED',
                'jira': 'PASSED',
                'peachee_stats': 'PASSED',
                'parent_pom': 'PASSED',
                },
            'release_passed': 'success',
            'maven_central_published': 'success',
            'javadoc_published': 'success',
            'testpypi_published': 'success',
            'pypi_published': 'success',
            'status': 'true',
            }]

        self.assertEqual(expected, actual, 'Invalid log structure')

    @patch('requests.post')
    def test_post(self, mock_post):
        logs = prepare_logs()
        token = 'test-token'
        push_logs(logs, token)
        mock_post.assert_called_with("https://http-intake.logs.datadoghq.eu/api/v2/logs",
            json=logs,
            headers={
                "Content-Type": "application/json",
                "DD-API-KEY": 'test-token'
            },
        )


if __name__ == '__main__':
    unittest.main()
