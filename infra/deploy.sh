#!/usr/bin/env bash
set -eu -o pipefail

aws cloudformation deploy \
  --profile=${AWS_PROFILE} \
  --region=eu-west-1 \
  --template-file service.yaml \
  --stack-name ReleaseAction-Releasability-Service-${ENV_TYPE} \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-override \
    EnvType=${ENV_TYPE} \
    ReleasabilityResultTopicArn=/Burgr/Releasability/${ENV_TYPE}/ReleasabilityResultArn
