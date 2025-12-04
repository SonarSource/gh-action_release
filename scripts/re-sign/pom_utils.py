"""Utilities for POM file manipulation."""

import xml.etree.ElementTree as ET
from pathlib import Path


def update_pom_versions(local_repo_dir: str, old_version: str, new_version: str):
    """Update version in all POM files.

    Args:
        local_repo_dir: Local repository directory containing POM files
        old_version: Current version to replace
        new_version: New version to set
    """
    pom_files = list(Path(local_repo_dir).rglob('*.pom'))

    if not pom_files:
        print("No POM files found")
        return

    print(f"Found {len(pom_files)} POM files to update")
    print(f"Updating version from {old_version} to {new_version}")

    for pom_file in pom_files:
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()

            # Handle namespaces - POM files can use default namespace or prefixed namespace
            ns_uri = 'http://maven.apache.org/POM/4.0.0'
            if root.tag.startswith('{'):
                ns_uri = root.tag[1:].split('}')[0]

            # Register namespace for XPath queries
            ns = {'maven': ns_uri}
            ET.register_namespace('', ns_uri)

            updated = False

            # Update version element - find all version elements recursively
            # Try both with and without namespace prefix
            version_elems = root.findall('.//maven:version', ns)
            if not version_elems:
                # Try without namespace prefix (for default namespace)
                version_elems = root.findall('.//{http://maven.apache.org/POM/4.0.0}version')
                if not version_elems:
                    version_elems = root.findall('.//version')

            for version_elem in version_elems:
                if version_elem.text == old_version:
                    version_elem.text = new_version
                    updated = True

            # Also check root level version (if not in a parent)
            root_version = root.find('maven:version', ns)
            if root_version is None:
                root_version = root.find('{http://maven.apache.org/POM/4.0.0}version')
            if root_version is None:
                root_version = root.find('version')

            if root_version is not None and root_version.text == old_version:
                root_version.text = new_version
                updated = True

            # Also update parent version if present
            parent = root.find('.//maven:parent', ns)
            if parent is None:
                parent = root.find('.//{http://maven.apache.org/POM/4.0.0}parent')
            if parent is None:
                parent = root.find('.//parent')

            if parent is not None:
                parent_version = parent.find('maven:version', ns)
                if parent_version is None:
                    parent_version = parent.find('{http://maven.apache.org/POM/4.0.0}version')
                if parent_version is None:
                    parent_version = parent.find('version')

                if parent_version is not None and parent_version.text == old_version:
                    parent_version.text = new_version
                    updated = True

            if updated:
                tree.write(pom_file, encoding='utf-8', xml_declaration=True)
                print(f"Updated version in: {pom_file}")

        except Exception as e:
            print(f"Warning: Failed to update {pom_file}: {e}")

