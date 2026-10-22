#!/usr/bin/env python3
"""Apply the Maven Central bundle customizations of the release workflow to a bundle downloaded by
manual-maven-central-sync.sh.

Usage: filter-central-bundle.py <local-repo-dir>

Reads CENTRAL_EXCLUSIONS, CENTRAL_EXCLUDE and CENTRAL_PLACEHOLDER_JAVADOC (default "-", i.e. none), which take the
values of the inputs mavenCentralSyncExclusions, mavenCentralSyncExclude and mavenCentralSyncPlaceholderJavadoc.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main"))

from release.utils.maven_central import filter_bundle  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        filter_bundle(sys.argv[1], os.environ.get("CENTRAL_EXCLUSIONS", "-"), os.environ.get("CENTRAL_EXCLUDE", "-"),
                      os.environ.get("CENTRAL_PLACEHOLDER_JAVADOC", "-"))
    except ValueError as e:
        sys.exit(f"ERROR: invalid bundle customization: {e}")


if __name__ == "__main__":
    main()
