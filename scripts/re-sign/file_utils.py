"""Utilities for file and directory operations related to version changes."""

import os
import shutil
from pathlib import Path
from typing import List


def rename_versioned_files(local_repo_dir: str, old_version: str, new_version: str):
    """Rename files that contain the version in their filename.

    This includes files like:
    - artifact-15.0.2.8567.jar -> artifact-15.0.3.1234.jar
    - artifact-15.0.2.8567.pom -> artifact-15.0.3.1234.pom
    - artifact-15.0.2.8567-cyclonedx.json -> artifact-15.0.3.1234-cyclonedx.json

    Args:
        local_repo_dir: Local repository directory
        old_version: Current version in filenames
        new_version: New version for filenames
    """
    # Find all files that contain the old version in their name
    all_files = list(Path(local_repo_dir).rglob('*'))
    files_to_rename = [f for f in all_files if f.is_file() and old_version in f.name]

    if not files_to_rename:
        print("No files found with version in filename to rename")
        return

    print(f"Found {len(files_to_rename)} files to rename (version in filename)")

    for file_path in files_to_rename:
        try:
            # Replace old version with new version in filename
            new_name = file_path.name.replace(old_version, new_version)
            new_path = file_path.parent / new_name

            if new_path != file_path:
                file_path.rename(new_path)
                print(f"Renamed: {file_path.name} -> {new_name}")
        except Exception as e:
            print(f"Warning: Failed to rename {file_path}: {e}")


def restructure_version_directories(local_repo_dir: str, old_version: str, new_version: str):
    """Restructure Maven repository directories to reflect the new version.

    Maven repository structure is: groupId/artifactId/version/
    When version changes, we need to move files from old version directory to new version directory.

    Args:
        local_repo_dir: Local repository directory
        old_version: Current version in directory paths
        new_version: New version for directory paths
    """
    # Find all directories that end with the old version
    all_dirs = [d for d in Path(local_repo_dir).rglob('*') if d.is_dir()]
    version_dirs = [d for d in all_dirs if d.name == old_version]

    if not version_dirs:
        print("No version directories found to restructure")
        return

    print(f"Found {len(version_dirs)} version directories to restructure")
    print(f"Moving from version {old_version} to {new_version}")

    for old_dir in version_dirs:
        try:
            # Create new directory path with new version
            new_dir = old_dir.parent / new_version

            if new_dir.exists():
                # If target exists, we should remove old directory since files were already moved/renamed
                # This can happen if file renaming created the new directory structure
                print(f"Target directory already exists: {new_dir}, cleaning up old directory...")
                # Check if old directory has any files
                remaining_files = list(old_dir.iterdir())
                if remaining_files:
                    # Files still exist in old directory - this shouldn't happen if restructuring happens before renaming
                    # But if it does, we should move any files that don't exist in new directory
                    for item in remaining_files:
                        dest = new_dir / item.name
                        if not dest.exists():
                            # File doesn't exist in new directory, move it
                            shutil.move(str(item), str(dest))
                            print(f"  Moved {item.name} to new directory")
                    # Try to remove old directory
                    try:
                        old_dir.rmdir()
                        print(f"Removed old directory: {old_dir}")
                    except OSError:
                        remaining = list(old_dir.iterdir())
                        if remaining:
                            print(f"Warning: Could not remove old directory {old_dir}, {len(remaining)} items remain - removing forcefully")
                            # Force remove remaining files/directories
                            for item in remaining:
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():
                                    shutil.rmtree(item)
                            old_dir.rmdir()
                else:
                    # Old directory is empty, just remove it
                    old_dir.rmdir()
                    print(f"Removed empty old directory: {old_dir}")
            else:
                # Move the entire directory
                shutil.move(str(old_dir), str(new_dir))
                print(f"Moved directory: {old_dir} -> {new_dir}")

        except Exception as e:
            print(f"Warning: Failed to move directory {old_dir}: {e}")

