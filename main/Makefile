SHELL := /bin/bash

test:
	pipenv install --dev
	PYTHONPATH=${PWD} pipenv run pytest \
		--cov-report html:build/coverage-html \
		--cov-report xml:build/coverage.xml \
		--cov-report term \
		--cov=release/ \
		tests/
