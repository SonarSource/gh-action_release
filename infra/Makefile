SHELL := /bin/bash

deploy-dev:
	AWS_PROFILE=burgr-dev-admin ENV_TYPE=Dev ./deploy.sh

deploy-staging:
	AWS_PROFILE=burgr-staging-admin ENV_TYPE=Staging ./deploy.sh

deploy-prod:
	AWS_PROFILE=burgr-prod-admin ENV_TYPE=Prod ./deploy.sh

.PHONY: deploy-dev deploy-staging deploy-prod
