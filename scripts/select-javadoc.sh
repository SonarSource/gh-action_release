#!/usr/bin/env bash

# Usage: select-javadoc.sh <public-dir> <private-dir> <dest-dir> <public-release>

set -euo pipefail

PUBLIC_DIR="${1:?public-dir parameter is required}"
PRIVATE_DIR="${2:?private-dir parameter is required}"
DEST_DIR="${3:?dest-dir parameter is required}"
PUBLIC_RELEASE="${4:-false}"

shopt -s nullglob

public_jars=( "$PUBLIC_DIR"/*-javadoc.jar )
private_jars=( "$PRIVATE_DIR"/*-javadoc.jar )

echo "Found ${#public_jars[@]} public and ${#private_jars[@]} private javadoc jar(s) (publicRelease=$PUBLIC_RELEASE)"

if (( ${#public_jars[@]} > 0 )); then
  cp "${public_jars[@]}" "$DEST_DIR/"
fi

private_selected=false
if (( ${#private_jars[@]} > 0 )) && { (( ${#public_jars[@]} == 0 )) || [[ "$PUBLIC_RELEASE" == "true" ]]; }; then
  cp "${private_jars[@]}" "$DEST_DIR/"
  private_selected=true
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
