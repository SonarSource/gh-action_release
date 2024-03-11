import uuid
import boto3
from dryable import Dryable
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.version_helper import VersionHelper
from release.vars import releasability_aws_region, releasability_env_type


class Releasability:
    release_request: ReleaseRequest

    def __init__(self, release_request):
        self.release_request = release_request

        arn_topics = {
            "Dev": {
                "INPUT_TOPIC": "arn:aws:sns:eu-west-1:597611216173:Releasability-Dev-MessagingReleasabilityTrigger41B5D077-ytFNCS6b5yFa",
                "OUTPUT_TOPIC": "arn:aws:sns:eu-west-1:597611216173:Releasability-Dev-MessagingReleasabilityResult1BF0D6BB-uVEUpOrhfpcm"
            },
            "Staging": {
                "INPUT_TOPIC":
                    "arn:aws:sns:eu-west-1:308147251410:Releasability-Staging-MessagingReleasabilityTrigger41B5D077-iSdypIfYu4x5",
                "OUTPUT_TOPIC": "arn:aws:sns:eu-west-1:308147251410:Releasability-Staging-MessagingReleasabilityResult1BF0D6BB-99BdgYmfNHCp"
            },
            "Prod": {
                "INPUT_TOPIC": "arn:aws:sns:eu-west-1:064493320159:Releasability-Prod-MessagingReleasabilityTrigger41B5D077-EjmsAMpmaj72",
                "OUTPUT_TOPIC": "arn:aws:sns:eu-west-1:064493320159:Releasability-Prod-MessagingReleasabilityResult1BF0D6BB-Sv8YMUXuc4bh"
            },
        }

        self.INPUT_TOPIC_ARN = arn_topics[releasability_env_type]["INPUT_TOPIC"]
        self.OUTPUT_TOPIC_ARN = arn_topics[releasability_env_type]["OUTPUT_TOPIC"]
        self.session = boto3.Session(region_name=releasability_aws_region)

    @Dryable(logging_msg='{function}()')
    def start_releasability_checks(self):
        standardized_version = VersionHelper.as_standardized_version(self.release_request)

        print(f"Starting releasability check: {self.release_request.project}#{standardized_version}")

        correlation_id = str(uuid.uuid4())
        sns_request = self._build_sns_request(
            correlation_id=correlation_id,
            organization=self.release_request.org,
            project_name=self.release_request.project,
            branch_name=self.release_request.branch,
            version=standardized_version,
            revision=self.release_request.sha,
            build_number=int(self.release_request.buildnumber)
        )

        response = self.session.client('sns').publish(
            TopicArn=self.INPUT_TOPIC_ARN,
            Message=str(sns_request),
        )
        print(f"Issued SNS message {response['MessageId']}; the request identifier is {correlation_id}")
        return correlation_id

    def _build_sns_request(self,
                           correlation_id: str,
                           organization: str,
                           project_name: str,
                           branch_name: str,
                           revision: str,
                           version: str,
                           build_number: int):
        sns_request = {
            'uuid': correlation_id,
            'responseToARN': self.OUTPUT_TOPIC_ARN,
            'repoSlug': f'{organization}/{project_name}',
            'version': version,
            'vcsRevision': revision,
            'artifactoryBuildNumber': build_number,
            'branchName': branch_name
        }
        return sns_request
