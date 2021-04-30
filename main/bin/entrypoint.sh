#!/bin/bash

set -oue pipefail

REVOKED_KEY=CFCA4A29D26468DE
BUILD="${GITHUB_REPOSITORY#*/}/${GITHUB_REF##*.}"

echo "BUILD=$BUILD"

jfrog rt config repox --url https://repox.jfrog.io/artifactory/ --apikey "$ARTIFACTORY_API_KEY" --basic-auth-only
cd "$(mktemp -d sigcheck.XXXXXXXXXX)" && {
  jfrog rt download --build "${BUILD}" sonarsource-builds/**/*.asc
  find . -type f -name "*.asc" -exec gpg --list-packets {} \; | grep ${REVOKED_KEY} && exit 1 || true
}

exec python /app/main.py
