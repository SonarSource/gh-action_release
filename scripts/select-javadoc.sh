#!/usr/bin/env bash

# Usage: select-javadoc.sh <public-dir> <private-dir> <dest-dir> <public-release>

set -euo pipefail

PUBLIC_DIR="${1:?public-dir parameter is required}"
PRIVATE_DIR="${2:?private-dir parameter is required}"
DEST_DIR="${3:?dest-dir parameter is required}"
PUBLIC_RELEASE="${4:-false}"

shopt -s nullglob

copied_jars=0
copy_jars_no_overwrite() {
  local jar name target
  copied_jars=0
  for jar in "$@"; do
    name=$(basename "$jar")
    target="$DEST_DIR/$name"
    if [[ -e "$target" ]]; then
      echo "::warning::Duplicate javadoc jar name $name, skipping to avoid overwriting an already-copied one"
      continue
    fi
    cp "$jar" "$target"
    copied_jars=$((copied_jars + 1))
  done
}

public_jars=( "$PUBLIC_DIR"/*-javadoc.jar )
private_jars=( "$PRIVATE_DIR"/*-javadoc.jar )

echo "Found ${#public_jars[@]} public and ${#private_jars[@]} private javadoc jar(s) (publicRelease=$PUBLIC_RELEASE)"

if (( ${#public_jars[@]} > 0 )); then
  copy_jars_no_overwrite "${public_jars[@]}"
fi

private_selected=false
if (( ${#private_jars[@]} > 0 )) && { (( ${#public_jars[@]} == 0 )) || [[ "$PUBLIC_RELEASE" == "true" ]]; }; then
  copy_jars_no_overwrite "${private_jars[@]}"
  if (( copied_jars > 0 )); then
    private_selected=true
  fi
elif (( ${#private_jars[@]} > 0 )); then
  echo "::notice::Skipping ${#private_jars[@]} com.sonarsource.* javadoc jar(s); set publicRelease: true to publish them too"
fi

mixed=false
if (( ${#public_jars[@]} > 0 )) && [[ "$private_selected" == "true" ]]; then
  mixed=true
fi
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "mixed=${mixed}" >> "$GITHUB_OUTPUT"
fi
