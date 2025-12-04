"""Utilities for SBOM (Software Bill of Materials) file manipulation."""

import json
from pathlib import Path
from typing import List


def find_sbom_files(local_repo_dir: str) -> List[Path]:
    """Find all SBOM files in the repository directory.

    SBOM files are typically JSON files with names like:
    - *.sbom.json
    - *-sbom.json
    - *.bom.json
    - *.cyclonedx.json
    - *.spdx.json

    Args:
        local_repo_dir: Local repository directory

    Returns:
        List of Path objects for SBOM files
    """
    # Find SBOM files by pattern - need to handle both *-cyclonedx.json and *.cyclonedx.json patterns
    sbom_files = []

    # Find JSON SBOM files
    for pattern in ['*.sbom.json', '*-sbom.json', '*.bom.json', '*.cyclonedx.json', '*-cyclonedx.json', '*.spdx.json']:
        sbom_files.extend(Path(local_repo_dir).rglob(pattern))

    # Find XML SBOM files
    for pattern in ['*.cyclonedx.xml', '*-cyclonedx.xml']:
        sbom_files.extend(Path(local_repo_dir).rglob(pattern))

    # Remove duplicates
    return list(set(sbom_files))


def update_sbom_versions(local_repo_dir: str, old_version: str, new_version: str):
    """Update version in all SBOM files.

    SBOM files can be in various formats (CycloneDX, SPDX, etc.) but typically
    contain version information in JSON format. This function attempts to update
    version strings in common locations within SBOM files.

    Args:
        local_repo_dir: Local repository directory
        old_version: Current version to replace
        new_version: New version to set
    """
    sbom_files = find_sbom_files(local_repo_dir)

    if not sbom_files:
        print("No SBOM files found")
        return

    print(f"Found {len(sbom_files)} SBOM files to update")
    print(f"Updating version from {old_version} to {new_version}")

    for sbom_file in sbom_files:
        try:
            # Read the SBOM file
            with open(sbom_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to parse as JSON first
            try:
                sbom_data = json.loads(content)
                updated = False

                # Update version in common SBOM JSON structures
                # CycloneDX format: metadata.component.version or components[].version
                if isinstance(sbom_data, dict):
                    # Update metadata.component.version (CycloneDX)
                    if 'metadata' in sbom_data and isinstance(sbom_data['metadata'], dict):
                        if 'component' in sbom_data['metadata']:
                            component = sbom_data['metadata']['component']
                            if isinstance(component, dict) and component.get('version') == old_version:
                                component['version'] = new_version
                                updated = True

                    # Update components array (CycloneDX)
                    if 'components' in sbom_data and isinstance(sbom_data['components'], list):
                        for component in sbom_data['components']:
                            if isinstance(component, dict) and component.get('version') == old_version:
                                component['version'] = new_version
                                updated = True

                    # Update packages array (SPDX-like)
                    if 'packages' in sbom_data and isinstance(sbom_data['packages'], list):
                        for package in sbom_data['packages']:
                            if isinstance(package, dict) and package.get('version') == old_version:
                                package['version'] = new_version
                                updated = True

                    # Update documentDescribes (SPDX)
                    if 'documentDescribes' in sbom_data:
                        if isinstance(sbom_data['documentDescribes'], list):
                            for i, ref in enumerate(sbom_data['documentDescribes']):
                                if isinstance(ref, str) and old_version in ref:
                                    sbom_data['documentDescribes'][i] = ref.replace(old_version, new_version)
                                    updated = True

                    # Comprehensive recursive update for all version references
                    def update_all_version_references(obj, old_ver, new_ver):
                        nonlocal updated
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if isinstance(value, str):
                                    # Update bom-ref, purl, ref fields that contain version (case-insensitive)
                                    key_lower = key.lower()
                                    if key_lower in ['bom-ref', 'purl', 'ref'] or key_lower.endswith('ref'):
                                        if old_ver in value:
                                            obj[key] = value.replace(old_ver, new_ver)
                                            updated = True
                                    # Update version fields (exact match)
                                    elif key_lower == 'version':
                                        if value == old_ver:
                                            obj[key] = new_ver
                                            updated = True
                                elif isinstance(value, (dict, list)):
                                    update_all_version_references(value, old_ver, new_ver)
                        elif isinstance(obj, list):
                            for item in obj:
                                update_all_version_references(item, old_ver, new_ver)

                    # Update all version references recursively
                    update_all_version_references(sbom_data, old_version, new_version)

                    # Also do a final text replacement pass to catch any remaining occurrences
                    # This ensures we catch all version references, even in complex nested structures
                    content_str = json.dumps(sbom_data)
                    if old_version in content_str:
                        content_str = content_str.replace(old_version, new_version)
                        sbom_data = json.loads(content_str)
                        updated = True

                    if updated:
                        # Write back the updated JSON
                        with open(sbom_file, 'w', encoding='utf-8') as f:
                            json.dump(sbom_data, f, indent=2, ensure_ascii=False)
                        print(f"Updated SBOM file: {sbom_file}")
                    else:
                        print(f"No version found to update in: {sbom_file}")
                else:
                    # Not a dict, try text replacement
                    if old_version in content:
                        content = content.replace(old_version, new_version)
                        with open(sbom_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Updated SBOM file (text replacement): {sbom_file}")

            except json.JSONDecodeError:
                # Not valid JSON (likely XML), try text replacement for all occurrences
                if old_version in content:
                    content = content.replace(old_version, new_version)
                    with open(sbom_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Updated SBOM file (text replacement): {sbom_file}")
                else:
                    print(f"Warning: SBOM file is not JSON and no version found: {sbom_file}")

        except Exception as e:
            print(f"Warning: Failed to update SBOM file {sbom_file}: {e}")

