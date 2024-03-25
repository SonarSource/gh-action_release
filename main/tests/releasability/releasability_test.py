import ast
import copy
import unittest
from unittest import mock

from unittest.mock import patch, MagicMock

from release.steps.ReleaseRequest import ReleaseRequest
from release.releasability.releasability import Releasability, CouldNotRetrieveReleasabilityCheckResultsException


class ReleasabilityTest(unittest.TestCase):

    def test_build_sns_request_should_assign_correctly_properties(self):
        session = MagicMock()
        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            uuid = "42f23-3232-3232-32232"

            request = releasability._build_sns_request(
                correlation_id=uuid,
                organization=organization,
                project_name=project_name,
                branch_name=branch_name,
                version=version,
                revision=sha,
                build_number=build_number
            )

            assert request['uuid'] == uuid
            assert request['responseToARN'] is not None
            assert request['repoSlug'] == "sonar/sonar-dummy"
            assert request['version'] == version
            assert request['vcsRevision'] == sha
            assert request['artifactoryBuildNumber'] == build_number
            assert request['branchName'] == branch_name

    def test_start_releasability_checks_should_invoke_publish(self):
        session = MagicMock()
        mocked_sns_client = MagicMock()
        session.client.return_value = mocked_sns_client

        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            releasability.start_releasability_checks()

            assert mocked_sns_client.publish.call_count == 1
            sns_query_content = ast.literal_eval(mocked_sns_client.publish.call_args[1]['Message'])
            assert sns_query_content['responseToARN'] is not None
            assert sns_query_content['vcsRevision'] == sha

    def test_start_releasability_checks_should_return_a_correlation_id_after_invokation(self):
        session = MagicMock()
        mocked_sns_client = MagicMock()
        session.client.return_value = mocked_sns_client

        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            correlation_id = releasability.start_releasability_checks()

            assert correlation_id is not None

    def test_arn_to_sqs_url_should_return_expected_url_given_a_valid_sqs_arn(self):
        region = "us-east-1"
        account_number = "123456789012"
        queue_name = "great-project/great"
        arn = f"arn:aws:sqs:{region}:{account_number}:{queue_name}"

        sqs_url = Releasability._arn_to_sqs_url(arn)

        self.assertEqual(sqs_url, f"https://sqs.{region}.amazonaws.com/{account_number}/{queue_name}")

    def test_arn_to_sqs_url_should_return_expected_url_given_an_invalid_arn(self):
        region = "us-east-1"
        account_number = "123456789012"
        queue_name = "great-project/great"
        arn = f"arn:aws:invalid:{region}:{account_number}:{queue_name}"

        self.assertRaises(ValueError, lambda: Releasability._arn_to_sqs_url(arn))

    @mock.patch('boto3.Session.client')
    def test_fetch_check_results_should_return_4_messages_given_the_provided_response_contains_4(self, mock_client):
        mock_receive_message_response = {
            "Messages": [
                {
                    "MessageId": "8f1c4252-ef69-4426-87e6-bedc38dd1c59",
                    "ReceiptHandle": "AQEBled9Czbop56DLRmqHHStEuDqs2KbSIvieX1KQ9ViaiCO366I1kLpC5oVoq469pgOp+XUVwyDAqPetFG8R8amcCThlOEwuFudc4P2aF6DFcipt0WrLqkxlfLgYB1da9nZqsRJLRAh9oYLs0IGGmb6X9CFpoPjjGusfLNfpgs5oB6bVSwWPXZFzNtQ0arrYvH2Q5XQx3XEoUteJMrxtWBtOPGx8o5ab68Rag7aKe7TojFB23iyY4lA4bMyXGQ4A/MyBnULy4R/MnBZQKp0WPrhTZaRMyrI9XVePfqwZWTSo7uJ6rWj7iAfQtB6QHN/wgQtl9teUwnYeIsbZQkPEZ/5KNY0FSFWGmH8CLB8EGezl1SRhUKiM5Ol7Cf4hwwmbYj5xBfQu/644xnX8xMKtgDHKw==",
                    "MD5OfBody": "5345a84088f3e0405b4ba6f5c3e561ee",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "7a3a3d4f-b9ee-579e-b423-633b4bcbc067",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"ACK\\",\\"requestUUID\\":\\"2fe2a7f3-7910-407d-b5da-d72f68111a4e\\",\\"checkName\\":\\"Jira\\"}",\n  "Timestamp" : "2024-03-20T14:17:09.071Z",\n  "SignatureVersion" : "1",\n  "Signature" : "CgZfhTmy1jvPyu1z+vKR+lbj+EN4Bsxsn5QOnV8rACMRIG7RgUbrTOVzEU8M1wtX940gnBIjdYYfrRAvqsQuH/WXREz1HZESBvAGroRJuX//kAqq0gk8dtRUd39AodOwnQ5qEciTXmwQYoAR33WGHTNxXM7wduoPFjxwhOn7RRExaSKyhvMekoFOuyF+y5sxtGqvhLTG31k6xF4SOkQ8DyG+6Ko7F6+xOJiwzXJnzDErgA3DnkwZPUDpOfnWhtNNRwUeoU1gIqMTWAiwLHfverO+Tcuyw6MfJfQpFeFBzsXHv4BzFebCfgjITb8YV6+aUAlxYZ6hy/ZvA6Uvw4TaJA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "dbed4492-0e78-49c8-bdcf-85fce5832d0c",
                    "ReceiptHandle": "AQEBcarMK65resUunTs6R8vxdqY4eVt0u+42WDGngdzAhFsSuZwzU/zvbgLK66au158enVS1dKCHhdbpZ5Uoa6aCx85JnFf6EhMkAJLuFlE/TDvsjxKlDEYMrW6atkfrKiGp74toIA5bFMquvFCHBeUX67lYPqdZt4uQZff6LKBw+ffwSW7bD/iMo6GNNomHp1EuoQEFD/Sg5pQ72L2xDyl1ktIGzRRDCZPRcBDf7IoMK02km1dWvc4BCwCIUPfk7Q9QBWjc7H6xgnwvyH0/CdsY6FtEfzoplsiwBSvHx1MwR9bi5XegjzSMW599oIpw2LyIb0J9y6i4WC37nJ3OMi3sJ5DyZQE6m26yky3al2LqP9XajaeZoWn0zj5AtXqJp67zD9eU5Az6htN+aPoYk3hUbA==",
                    "MD5OfBody": "5d09311d8a24bfb52d51f3d84ce5bf45",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "22c0530b-97df-5b43-8e93-0d7f65bac623",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"ACK\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"CheckManifestValues\\"}",\n  "Timestamp" : "2024-03-20T14:18:13.990Z",\n  "SignatureVersion" : "1",\n  "Signature" : "OtI37PxiCZwuf+KKso2DUyYKBqZazI/g74mflET3OEtgzcpDEDwxKuK1CYJGg37FCeUg3HzuJIspHqSTPr0mZiMozWg+y2++V4hV70ZTWoQkb1tCVVWWdPVc9p3SGr6VccnILDR/+scYlVOnO5CJ6al3h0Pyb+7NcFl3Wp7xYuO+3P3Kk59sFwkw4aXRQ4NNpeA4oED0oxff7oTrazFt/omfZcVIEnSh+meW+0ToqC16+f4okmWvpeKPtSplWIqwm5lqF5Ig8MZxIvxOJXs0UINVqmA+A8n4JaV1p9EEx4G8uqgd2YCXHxbubOfrQOzjKSDlSyNy9TGM1wPTrVBZzA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "c5bf7e99-7ac6-4af5-8ebf-fe49453fdb22",
                    "ReceiptHandle": "AQEBiliSt3Pr2Siad3VwxnmOZJXNcAmSGKiP76RzaL9bnX3TRHlMvcrI5kcuIGe5seNCa96B1CygByamfDIe4akJ1zuHyk9KyiyuedJvvJuhi8Vm6rnkNMro6l8cnSN/PzApJxbljU8V7TBX9O9H6R2XPz51uA+qRZDclpbN9uZdFo+Vmwgo+nX0oic/38XBbJsCs2uuzQty54tnsa3bRXsYXT+yncCpp1+4K0R217gaEv8+leoXPakvUw8MWT8EdfpHXjM1ZOqC99Gm0Gl/bls7KvEi1Da/+qNSDXztbAO45TPAfWRrIacrEJOfNnyRzIhocCsOThi8WcXg8ksvrjZYULaC07r36ZMwtTtvgaWVx/xadV6a2kZ4fj7sNf7mfni7h3TEc5LZikfmDMP/kKTSSQ==",
                    "MD5OfBody": "d4eec5af4ed08874f228bf874b2f533b",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "304e7c5a-a223-5d41-a9a9-222e50455021",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"PASSED\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"CheckManifestValues\\"}",\n  "Timestamp" : "2024-03-20T14:18:14.211Z",\n  "SignatureVersion" : "1",\n  "Signature" : "L76hnVaqFgQAQkf84oxWSVtJOgEYPtaTuZ5XBz6Bt8Q3i3u7hp5UL2mb1X8zh2u/NYNapvZ8vgOuA/qY7dpIkxq1w8QK3iEfJedDjxSwr2BqtgI2ZnEiG3ZE3D3ImleloYv3qeBvKilQahN8dW5ggQgvVaVaMo91soAFTYnqRxpihVJlsXhlgPFbJvbZVHBWXe1+DIn8dZboFJ29bgtB5MfgkZvlDfgXzrEZXCOGXyUaRXFNVkfaYHFerf3IHTX7IBSQbonk/na10227WA+AUtBv+4iAw+yG+gCkXS6U34gxXjboiO+rMbUEiZZjlu0WyvWH2SnPBtn2eQeY0IG5oQ==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "430ab0e1-3c5f-4f74-bee3-ab9ed4af0de4",
                    "ReceiptHandle": "AQEBv+xtTfU1EHcQNXb/gliOElKr5IHWGyH942btzBhVfeR3TOEDKwRvwBb16oAyNnah6MYtf8/2vghP1Fl11BdADYzb1xE/0Y8C80+bqaXODZHvsChp+EdfRXlSZ2G6nYP92eZ8hbzMDkrUehpjwSvZK5bIXBF95ACr5p3s/HiPtNPSm04z5WnlbIMUJxfRyeUprTHfnNF5omU2fiJ1DditIoUOzX1uK4emZV163QEtRY6BeA3SyHSQPdUJauedF9atvZaSS3QYBnxnnMl3euTBUOXQeYzg0OT4IS3705Zg4y4RJXpnlXTMXMelGPkw1+QyaO6x3uia/AeI8anwv5euKnoEIAOJ6kBxBNTlQWayla3850kktVS4b/0MA1c4IztheGV8iA4U8d+OUYF77TTSXw==",
                    "MD5OfBody": "3e4956d640e93a6c0c23a0843e001b76",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "45991139-0d30-59d2-8e05-4f4dff587745",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"FAILED\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"QualityGate\\",\\"message\\":\\"Quality gate is older than 15 minutes\\"}",\n  "Timestamp" : "2024-03-20T14:18:16.689Z",\n  "SignatureVersion" : "1",\n  "Signature" : "aFqqVS2pDWvKQ277vHGJtqKhp/pElh4ZHebZqjD7eIKPz3T9XS3lJd+129WRDCMd5brac/cG1cIaOzbKv1B8JJl8jaIT95ZG7KbsLg5sHpRDQq1shkQ7fBfEu5gWSIFip2xYeis1zDJdA4R8P8EAAVpeC0s+w80qiIMTYUSSyJfMNGoTUZY0s9MW3eyo+EC02cvDPpkd6pqJx/FKEQhO8cpyMAUM5DYuyI2vxVUamDBEQ7N67CuVcngSVE4Ti62pHnN80XGhYbUma+7th8Yty5GaWlavWAla3ZjwHSZuKkCb7lZdo3tAo3u8Vb5pqiJbg7FEPCkql7fHXRb4iX4BvA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
            ],
            "ResponseMetadata": {
                "RequestId": "3886ad6f-ba52-5351-8ae2-f31b4885daf7",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "3886ad6f-ba52-5351-8ae2-f31b4885daf7",
                    "date": "Wed, 20 Mar 2024 14:20:07 GMT",
                    "content-type": "text/xml",
                    "content-length": "7835",
                    "connection": "keep-alive",
                },
                "RetryAttempts": 0,
            },
        }

        mock_sqs_client = mock_client.return_value
        mock_sqs_client.receive_message.return_value = mock_receive_message_response

        organization = "sonar"
        project_name = "sonar-dummy"
        version = "5.4.3"
        sha = "434343443efdcaaa123232"
        build_number = 42
        branch_name = "feat/some"
        release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)

        releasability = Releasability(release_request)

        messages = releasability._fetch_check_results()

        self.assertEqual(len(messages), 4)

    @mock.patch('boto3.Session.client')
    def test_fetch_filtered_check_results_should_return_2_messages_given_the_4_provided_contains_only_2_matching_criteria(self,
                                                                                                                          mock_client):
        mock_receive_message_response = {
            "Messages": [
                {
                    "MessageId": "relevant-good-correlation-id-and-not-an-ack-message-1",
                    "ReceiptHandle": "AQEBled9Czbop56DLRmqHHStEuDqs2KbSIvieX1KQ9ViaiCO366I1kLpC5oVoq469pgOp+XUVwyDAqPetFG8R8amcCThlOEwuFudc4P2aF6DFcipt0WrLqkxlfLgYB1da9nZqsRJLRAh9oYLs0IGGmb6X9CFpoPjjGusfLNfpgs5oB6bVSwWPXZFzNtQ0arrYvH2Q5XQx3XEoUteJMrxtWBtOPGx8o5ab68Rag7aKe7TojFB23iyY4lA4bMyXGQ4A/MyBnULy4R/MnBZQKp0WPrhTZaRMyrI9XVePfqwZWTSo7uJ6rWj7iAfQtB6QHN/wgQtl9teUwnYeIsbZQkPEZ/5KNY0FSFWGmH8CLB8EGezl1SRhUKiM5Ol7Cf4hwwmbYj5xBfQu/644xnX8xMKtgDHKw==",
                    "MD5OfBody": "5345a84088f3e0405b4ba6f5c3e561ee",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "7a3a3d4f-b9ee-579e-b423-633b4bcbc067",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"PASSED\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"Jira\\"}",\n  "Timestamp" : "2024-03-20T14:17:09.071Z",\n  "SignatureVersion" : "1",\n  "Signature" : "CgZfhTmy1jvPyu1z+vKR+lbj+EN4Bsxsn5QOnV8rACMRIG7RgUbrTOVzEU8M1wtX940gnBIjdYYfrRAvqsQuH/WXREz1HZESBvAGroRJuX//kAqq0gk8dtRUd39AodOwnQ5qEciTXmwQYoAR33WGHTNxXM7wduoPFjxwhOn7RRExaSKyhvMekoFOuyF+y5sxtGqvhLTG31k6xF4SOkQ8DyG+6Ko7F6+xOJiwzXJnzDErgA3DnkwZPUDpOfnWhtNNRwUeoU1gIqMTWAiwLHfverO+Tcuyw6MfJfQpFeFBzsXHv4BzFebCfgjITb8YV6+aUAlxYZ6hy/ZvA6Uvw4TaJA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "relevant-good-correlation-id-and-not-an-ack-message-2",
                    "ReceiptHandle": "AQEBcarMK65resUunTs6R8vxdqY4eVt0u+42WDGngdzAhFsSuZwzU/zvbgLK66au158enVS1dKCHhdbpZ5Uoa6aCx85JnFf6EhMkAJLuFlE/TDvsjxKlDEYMrW6atkfrKiGp74toIA5bFMquvFCHBeUX67lYPqdZt4uQZff6LKBw+ffwSW7bD/iMo6GNNomHp1EuoQEFD/Sg5pQ72L2xDyl1ktIGzRRDCZPRcBDf7IoMK02km1dWvc4BCwCIUPfk7Q9QBWjc7H6xgnwvyH0/CdsY6FtEfzoplsiwBSvHx1MwR9bi5XegjzSMW599oIpw2LyIb0J9y6i4WC37nJ3OMi3sJ5DyZQE6m26yky3al2LqP9XajaeZoWn0zj5AtXqJp67zD9eU5Az6htN+aPoYk3hUbA==",
                    "MD5OfBody": "5d09311d8a24bfb52d51f3d84ce5bf45",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "22c0530b-97df-5b43-8e93-0d7f65bac623",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"ERROR\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"CheckManifestValues\\"}",\n  "Timestamp" : "2024-03-20T14:18:13.990Z",\n  "SignatureVersion" : "1",\n  "Signature" : "OtI37PxiCZwuf+KKso2DUyYKBqZazI/g74mflET3OEtgzcpDEDwxKuK1CYJGg37FCeUg3HzuJIspHqSTPr0mZiMozWg+y2++V4hV70ZTWoQkb1tCVVWWdPVc9p3SGr6VccnILDR/+scYlVOnO5CJ6al3h0Pyb+7NcFl3Wp7xYuO+3P3Kk59sFwkw4aXRQ4NNpeA4oED0oxff7oTrazFt/omfZcVIEnSh+meW+0ToqC16+f4okmWvpeKPtSplWIqwm5lqF5Ig8MZxIvxOJXs0UINVqmA+A8n4JaV1p9EEx4G8uqgd2YCXHxbubOfrQOzjKSDlSyNy9TGM1wPTrVBZzA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "irrelevant-as-its-an-ack",
                    "ReceiptHandle": "AQEBcarMK65resUunTs6R8vxdqY4eVt0u+42WDGngdzAhFsSuZwzU/zvbgLK66au158enVS1dKCHhdbpZ5Uoa6aCx85JnFf6EhMkAJLuFlE/TDvsjxKlDEYMrW6atkfrKiGp74toIA5bFMquvFCHBeUX67lYPqdZt4uQZff6LKBw+ffwSW7bD/iMo6GNNomHp1EuoQEFD/Sg5pQ72L2xDyl1ktIGzRRDCZPRcBDf7IoMK02km1dWvc4BCwCIUPfk7Q9QBWjc7H6xgnwvyH0/CdsY6FtEfzoplsiwBSvHx1MwR9bi5XegjzSMW599oIpw2LyIb0J9y6i4WC37nJ3OMi3sJ5DyZQE6m26yky3al2LqP9XajaeZoWn0zj5AtXqJp67zD9eU5Az6htN+aPoYk3hUbA==",
                    "MD5OfBody": "5d09311d8a24bfb52d51f3d84ce5bf45",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "22c0530b-97df-5b43-8e93-0d7f65bac623",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"ACK\\",\\"requestUUID\\":\\"b8e28245-3568-4257-970d-dcf47bd49ce5\\",\\"checkName\\":\\"CheckManifestValues\\"}",\n  "Timestamp" : "2024-03-20T14:18:13.990Z",\n  "SignatureVersion" : "1",\n  "Signature" : "OtI37PxiCZwuf+KKso2DUyYKBqZazI/g74mflET3OEtgzcpDEDwxKuK1CYJGg37FCeUg3HzuJIspHqSTPr0mZiMozWg+y2++V4hV70ZTWoQkb1tCVVWWdPVc9p3SGr6VccnILDR/+scYlVOnO5CJ6al3h0Pyb+7NcFl3Wp7xYuO+3P3Kk59sFwkw4aXRQ4NNpeA4oED0oxff7oTrazFt/omfZcVIEnSh+meW+0ToqC16+f4okmWvpeKPtSplWIqwm5lqF5Ig8MZxIvxOJXs0UINVqmA+A8n4JaV1p9EEx4G8uqgd2YCXHxbubOfrQOzjKSDlSyNy9TGM1wPTrVBZzA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
                {
                    "MessageId": "irrelevant-as-its-for-another-correlation-id",
                    "ReceiptHandle": "AQEBcarMK65resUunTs6R8vxdqY4eVt0u+42WDGngdzAhFsSuZwzU/zvbgLK66au158enVS1dKCHhdbpZ5Uoa6aCx85JnFf6EhMkAJLuFlE/TDvsjxKlDEYMrW6atkfrKiGp74toIA5bFMquvFCHBeUX67lYPqdZt4uQZff6LKBw+ffwSW7bD/iMo6GNNomHp1EuoQEFD/Sg5pQ72L2xDyl1ktIGzRRDCZPRcBDf7IoMK02km1dWvc4BCwCIUPfk7Q9QBWjc7H6xgnwvyH0/CdsY6FtEfzoplsiwBSvHx1MwR9bi5XegjzSMW599oIpw2LyIb0J9y6i4WC37nJ3OMi3sJ5DyZQE6m26yky3al2LqP9XajaeZoWn0zj5AtXqJp67zD9eU5Az6htN+aPoYk3hUbA==",
                    "MD5OfBody": "5d09311d8a24bfb52d51f3d84ce5bf45",
                    "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "22c0530b-97df-5b43-8e93-0d7f65bac623",\n  "TopicArn" : "arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic",\n  "Message" : "{\\"type\\":\\"PASSED\\",\\"requestUUID\\":\\"another-correlation-id\\",\\"checkName\\":\\"CheckManifestValues\\"}",\n  "Timestamp" : "2024-03-20T14:18:13.990Z",\n  "SignatureVersion" : "1",\n  "Signature" : "OtI37PxiCZwuf+KKso2DUyYKBqZazI/g74mflET3OEtgzcpDEDwxKuK1CYJGg37FCeUg3HzuJIspHqSTPr0mZiMozWg+y2++V4hV70ZTWoQkb1tCVVWWdPVc9p3SGr6VccnILDR/+scYlVOnO5CJ6al3h0Pyb+7NcFl3Wp7xYuO+3P3Kk59sFwkw4aXRQ4NNpeA4oED0oxff7oTrazFt/omfZcVIEnSh+meW+0ToqC16+f4okmWvpeKPtSplWIqwm5lqF5Ig8MZxIvxOJXs0UINVqmA+A8n4JaV1p9EEx4G8uqgd2YCXHxbubOfrQOzjKSDlSyNy9TGM1wPTrVBZzA==",\n  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:597611216173:ReleasabilityResultTopic:5983c1c3-36dd-4f95-8381-2e5864862d96"\n}',
                },
            ],
            "ResponseMetadata": {
                "RequestId": "3886ad6f-ba52-5351-8ae2-f31b4885daf7",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "3886ad6f-ba52-5351-8ae2-f31b4885daf7",
                    "date": "Wed, 20 Mar 2024 14:20:07 GMT",
                    "content-type": "text/xml",
                    "content-length": "7835",
                    "connection": "keep-alive",
                },
                "RetryAttempts": 0,
            },
        }

        mock_sqs_client = mock_client.return_value
        mock_sqs_client.receive_message.return_value = mock_receive_message_response

        organization = "sonar"
        project_name = "sonar-dummy"
        version = "5.4.3"
        sha = "434343443efdcaaa123232"
        build_number = 42
        branch_name = "feat/some"
        release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)

        releasability = Releasability(release_request)

        correlation_id = "b8e28245-3568-4257-970d-dcf47bd49ce5"

        def match_correlation_id(msg):
            return msg['requestUUID'] == correlation_id

        def not_an_ack_message(msg):
            return msg['type'] != 'ACK'

        filters = [lambda x: match_correlation_id(x), lambda x: not_an_ack_message(x)]
        filtered_messages = releasability._fetch_filtered_check_results(filters)

        self.assertEqual(len(filtered_messages), 2)

    @mock.patch('boto3.Session.client')
    def test_get_check_results_should_return_a_list_of_the_same_size_as_the_one_received_from_filtered_check_results(self, mock_session):
        organization = "sonar"
        project_name = "sonar-dummy"
        version = "5.4.3"
        sha = "434343443efdcaaa123232"
        build_number = 42
        branch_name = "feat/some"
        release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)

        releasability = Releasability(release_request)

        correlation_id = "ffff-0000-ffff-0000"
        filtered_check_results = [
                {
                    "type": "PASSED",
                    "requestUUID": correlation_id,
                    "checkName": "Jira",
                },
                {
                    "type": "ERROR",
                    "requestUUID": correlation_id,
                    "checkName": "some_check",
                },
            ]

        def mock_fetch_filtered_check_results(filters):
            return filtered_check_results

        def mock_get_checks_count():
            return len(filtered_check_results)

        releasability._get_checks_count = mock_get_checks_count

        releasability._fetch_filtered_check_results = mock_fetch_filtered_check_results

        results = releasability._get_check_results(correlation_id)

        self.assertEqual(len(results), len(filtered_check_results))

    @mock.patch('boto3.Session.client')
    def test_get_check_results_should_raise_an_exception_given_not_enough_check_result_were_retrieved(self, mock_session):
        organization = "sonar"
        project_name = "sonar-dummy"
        version = "5.4.3"
        sha = "434343443efdcaaa123232"
        build_number = 42
        branch_name = "feat/some"
        release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)

        Releasability.FETCH_CHECK_RESULT_TIMEOUT_SECONDS = 2

        releasability = Releasability(release_request)

        correlation_id = "ffff-0000-ffff-0000"
        filtered_check_results = [
                {
                    "type": "PASSED",
                    "requestUUID": correlation_id,
                    "checkName": "Jira",
                }
            ]

        def mock_fetch_filtered_check_results(filters):
                """
                Returns:
                    filtered_check_results only the first time it is invoked, after return an empty list
                """
                result = copy.deepcopy(filtered_check_results)
                filtered_check_results.clear()
                return result
        releasability._fetch_filtered_check_results = mock_fetch_filtered_check_results

        def mock_get_checks_count():
            return 5
        releasability._get_checks_count = mock_get_checks_count

        with self.assertRaises(CouldNotRetrieveReleasabilityCheckResultsException):
            releasability._get_check_results(correlation_id)

    @mock.patch('boto3.Session.client')
    def test_get_check_names(self, mock_client):
        sns_response = {
            "Subscriptions": [
                {
                    "SubscriptionArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic:8826ce92-6ebf-4c8c-96dc-832be94218db",
                    "Owner": "597611216173",
                    "Protocol": "lambda",
                    "Endpoint": "arn:aws:lambda:eu-west-1:597611216173:function:CheckWhiteSource",
                    "TopicArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic",
                },
                {
                    "SubscriptionArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic:53a1e6c7-a967-40b6-8d4d-61f8b50f0314",
                    "Owner": "597611216173",
                    "Protocol": "lambda",
                    "Endpoint": "arn:aws:lambda:eu-west-1:597611216173:function:CheckQualityGate",
                    "TopicArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic",
                },
                {
                    "SubscriptionArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic:439f2173-bcdb-4da6-acbe-121600093d8f",
                    "Owner": "597611216173",
                    "Protocol": "lambda",
                    "Endpoint": "arn:aws:lambda:eu-west-1:597611216173:function:CheckDependencies",
                    "TopicArn": "arn:aws:sns:eu-west-1:597611216173:ReleasabilityTriggerTopic",
                },
            ],
            "ResponseMetadata": {
                "RequestId": "2a7cdef4-75de-5568-81bb-80831b58a9f5",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "2a7cdef4-75de-5568-81bb-80831b58a9f5",
                    "date": "Fri, 22 Mar 2024 11:32:22 GMT",
                    "content-type": "text/xml",
                    "content-length": "4194",
                    "connection": "keep-alive",
                },
                "RetryAttempts": 0,
            },
        }
        mock_sns_client = mock_client.return_value
        mock_sns_client.list_subscriptions_by_topic.return_value = sns_response
        release_request = MagicMock()
        releasability = Releasability(release_request)

        check_names = releasability._get_checks()
        self.assertEqual(check_names, ["CheckWhiteSource", "CheckQualityGate", "CheckDependencies"])
