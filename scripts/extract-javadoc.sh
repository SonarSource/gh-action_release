#!/usr/bin/env bash

# Extract and publish javadoc jar
# Usage: extract-javadoc.sh <target-directory> <version>
# Example: ./extract-javadoc.sh /tmp/repo.ABCDEFGH 13.0.0.3026

set -euo pipefail

TARGET_DIR="${1:-.}"
VERSION="${2:?Version parameter is required}"

cd "$TARGET_DIR"

# Enable nullglob so the glob expands to nothing (instead of itself) when no files match
shopt -s nullglob

jars=( *-javadoc.jar )
JAVADOC_COUNT=${#jars[@]}

if (( JAVADOC_COUNT == 0 )); then
  echo "No javadoc files found!" >&2
  exit 1
elif (( JAVADOC_COUNT == 1 )); then
  echo "Found single javadoc file, using simple extraction"
  mv "${jars[0]}" javadoc.zip
else
  echo "Found multiple javadoc files, selecting main one"
  printf '%s\n' "${jars[@]}"
  for jar in "${jars[@]}"; do
    if [[ ! $jar =~ (test|fixture) ]]; then
      MAIN_JAVADOC="$jar"
      break
    fi
  done

  if [[ -z "${MAIN_JAVADOC:-}" ]]; then
    echo "No main javadoc found, please contact Engineering Experience team" >&2
    exit 1
  fi

  echo "Selected main javadoc: $MAIN_JAVADOC"
  mv "$MAIN_JAVADOC" javadoc.zip
fi

mkdir -p "javadoc/$VERSION"
unzip -q javadoc.zip -d "javadoc/$VERSION"
