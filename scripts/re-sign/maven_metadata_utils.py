"""Utilities for Maven metadata.xml file manipulation."""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List


def find_maven_metadata_files(local_repo_dir: str) -> List[Path]:
    """Find all maven-metadata.xml files in the repository directory.

    Args:
        local_repo_dir: Local repository directory

    Returns:
        List of Path objects for maven-metadata.xml files
    """
    metadata_files = list(Path(local_repo_dir).rglob('maven-metadata.xml'))
    return metadata_files


def update_maven_metadata_versions(local_repo_dir: str, old_version: str, new_version: str):
    """Update version in all maven-metadata.xml files.

    Maven metadata files contain version information in various places:
    - <versioning><versions><version> elements
    - <versioning><release> element
    - <versioning><latest> element
    - <versioning><lastUpdated> timestamp

    Args:
        local_repo_dir: Local repository directory
        old_version: Current version to replace
        new_version: New version to set
    """
    metadata_files = find_maven_metadata_files(local_repo_dir)

    if not metadata_files:
        print("No maven-metadata.xml files found")
        return

    print(f"Found {len(metadata_files)} maven-metadata.xml files to update")
    print(f"Updating version from {old_version} to {new_version}")

    for metadata_file in metadata_files:
        try:
            tree = ET.parse(metadata_file)
            root = tree.getroot()

            # Remove namespace for easier processing
            # Maven metadata typically uses no namespace or http://maven.apache.org/METADATA/1.0.0
            ns = {}
            if root.tag.startswith('{'):
                ns_uri = root.tag[1:].split('}')[0]
                ns = {'maven': ns_uri}
                # Register namespace for XPath queries
                ET.register_namespace('', ns_uri)

            updated = False

            # Update versioning.versions.version elements
            if ns:
                versions_elem = root.find('.//maven:versions', ns)
            else:
                versions_elem = root.find('.//versions')

            if versions_elem is not None:
                for version_elem in versions_elem.findall('version'):
                    if version_elem.text == old_version:
                        version_elem.text = new_version
                        updated = True
                        print(f"Updated version in versions list: {metadata_file}")

            # Update versioning.release
            if ns:
                release_elem = root.find('.//maven:release', ns)
            else:
                release_elem = root.find('.//release')

            if release_elem is not None and release_elem.text == old_version:
                release_elem.text = new_version
                updated = True
                print(f"Updated release version: {metadata_file}")

            # Update versioning.latest
            if ns:
                latest_elem = root.find('.//maven:latest', ns)
            else:
                latest_elem = root.find('.//latest')

            if latest_elem is not None and latest_elem.text == old_version:
                latest_elem.text = new_version
                updated = True
                print(f"Updated latest version: {metadata_file}")

            # Update lastUpdated timestamp to current time
            if ns:
                last_updated_elem = root.find('.//maven:lastUpdated', ns)
            else:
                last_updated_elem = root.find('.//lastUpdated')

            if last_updated_elem is not None:
                # Format: YYYYMMDDHHmmss (Maven metadata timestamp format)
                new_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                last_updated_elem.text = new_timestamp
                updated = True
                print(f"Updated lastUpdated timestamp: {metadata_file}")

            if updated:
                # Write back the updated XML
                tree.write(metadata_file, encoding='utf-8', xml_declaration=True)
                print(f"Updated maven-metadata.xml: {metadata_file}")
            else:
                print(f"No version found to update in: {metadata_file}")

        except Exception as e:
            print(f"Warning: Failed to update maven-metadata.xml file {metadata_file}: {e}")

