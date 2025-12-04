"""Utilities for checksum generation."""

import hashlib
from pathlib import Path


def regenerate_checksums(local_repo_dir: str):
    """Regenerate checksums (md5, sha1, sha256) for all files.

    Args:
        local_repo_dir: Local repository directory containing files
    """
    # Find all files that need checksums (excluding existing checksum files)
    all_files = []
    for ext in ['*.jar', '*.pom', '*.war', '*.ear', '*.asc', '*.zip',
                 '*.sbom.json', '*-sbom.json', '*.bom.json',
                 '*.cyclonedx.json', '*.spdx.json', 'maven-metadata.xml']:
        all_files.extend(Path(local_repo_dir).rglob(ext))

    # Filter out checksum files
    files_to_checksum = [f for f in all_files
                       if not f.name.endswith(('.md5', '.sha1', '.sha256'))]

    if not files_to_checksum:
        print("No files found to generate checksums for")
        return

    print(f"Regenerating checksums for {len(files_to_checksum)} files")

    # Calculate checksums manually
    for file_path in files_to_checksum:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # Calculate MD5
            md5 = hashlib.md5(content).hexdigest()
            with open(f'{file_path}.md5', 'w') as f:
                f.write(md5)

            # Calculate SHA1
            sha1 = hashlib.sha1(content).hexdigest()
            with open(f'{file_path}.sha1', 'w') as f:
                f.write(sha1)

            # Calculate SHA256
            sha256 = hashlib.sha256(content).hexdigest()
            with open(f'{file_path}.sha256', 'w') as f:
                f.write(sha256)

        except Exception as e:
            print(f"Warning: Failed to generate checksums for {file_path}: {e}")

