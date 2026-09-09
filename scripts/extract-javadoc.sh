#!/usr/bin/env bash

# Extract and publish javadoc jar
# Usage: extract-javadoc.sh <target-directory> <version> <mixed-privacy>
# Example: ./extract-javadoc.sh /tmp/repo.ABCDEFGH 13.0.0.3026 true

set -euo pipefail

TARGET_DIR="${1:-.}"
VERSION="${2:?Version parameter is required}"
MIXED="${3:-false}"

cd "$TARGET_DIR"

# Enable nullglob so the glob expands to nothing (instead of itself) when no files match
shopt -s nullglob

jars=( *-javadoc.jar )
JAVADOC_COUNT=${#jars[@]}

mkdir -p "javadoc/$VERSION"

if (( JAVADOC_COUNT == 0 )); then
  echo "No javadoc files found!" >&2
  exit 1
elif (( JAVADOC_COUNT == 1 )); then
  echo "Found single javadoc file, using simple extraction"
  unzip -q "${jars[0]}" -d "javadoc/$VERSION"
else
  echo "Found multiple javadoc files:"
  printf '%s\n' "${jars[@]}"

  main_jars=()
  for jar in "${jars[@]}"; do
    if [[ ! $jar =~ (test|fixture) ]]; then
      main_jars+=("$jar")
    fi
  done

  if (( ${#main_jars[@]} == 0 )); then
    echo "No main javadoc found, please contact Engineering Experience team" >&2
    exit 1
  elif (( ${#main_jars[@]} == 1 )); then
    echo "Found single main javadoc file (plus test/fixture noise), using simple extraction"
    unzip -q "${main_jars[0]}" -d "javadoc/$VERSION"
  elif [[ "$MIXED" != "true" ]]; then
    echo "Found multiple main javadoc files but not a mixed-privacy release, using simple extraction on the first one: ${main_jars[0]}"
    unzip -q "${main_jars[0]}" -d "javadoc/$VERSION"
  else
    echo "Extracting ${#main_jars[@]} javadoc file(s) into their own subdirectories: ${main_jars[*]}"
    {
      echo "<html><body><h1>Javadoc $VERSION</h1><ul>"
      for jar in "${main_jars[@]}"; do
        module="${jar%-"$VERSION"-javadoc.jar}"
        unzip -q -o "$jar" -d "javadoc/$VERSION/$module"
        echo "<li><a href=\"$module/index.html\">$module</a></li>"
      done
      echo "</ul></body></html>"
    } > "javadoc/$VERSION/index.html"
  fi
fi
