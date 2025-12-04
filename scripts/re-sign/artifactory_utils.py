"""Utilities for Artifactory operations."""

import json
import os
import re
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests

# Constants
TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
TIMESTAMP_TZ = '+0000'
ASC_PATTERN = '*.asc'

# Add parent directory to path to import release modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "main"))

from release.utils.buildinfo import BuildInfo


def get_buildinfo(artifactory, project: str, build_number: str) -> BuildInfo:
    """Get the original buildinfo from Artifactory.

    Note: We fetch buildinfo directly even in dry-run mode because we need it
    to determine the repository for downloading artifacts and for debugging.

    Args:
        artifactory: Artifactory client instance
        project: Project name
        build_number: Build number

    Returns:
        BuildInfo instance
    """
    # Fetch buildinfo directly using requests to bypass @Dryable decorator
    # We need buildinfo even in dry-run mode to determine the repository
    url = f"{artifactory.url}/api/build/{project}/{build_number}"
    headers = artifactory.headers

    print(f"Fetching buildinfo from: {url}")
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print(f"Error status: {r.status_code}")
        print(f"Error content: {r.content}")
        raise RuntimeError(f"Failed to fetch buildinfo: HTTP {r.status_code}")

    buildinfo_json = r.json()
    return BuildInfo(buildinfo_json)


def download_artifacts(local_repo_dir: str, project: str, build_number: str, buildinfo: BuildInfo):
    """Download artifacts from Artifactory using jfrog CLI.

    Args:
        local_repo_dir: Local directory to download artifacts to
        project: Project name
        build_number: Build number
        buildinfo: BuildInfo instance for repository determination
    """
    # Determine repository from buildinfo
    # Try to get repository from buildinfo statuses
    repo = 'sonarsource-public-releases'  # default
    try:
        if buildinfo.json.get('buildInfo', {}).get('statuses'):
            original_repo = buildinfo.json['buildInfo']['statuses'][0].get('repository')
            repo = original_repo or repo
            # Convert builds repo to releases repo if needed
            if 'builds' in repo:
                repo = repo.replace('builds', 'releases')
    except (KeyError, IndexError):
        pass

    # Use jfrog CLI to download artifacts
    # Similar to download-build action - need to be in the target directory
    os.makedirs(local_repo_dir, exist_ok=True)

    # When using --build, JFrog CLI automatically determines the repository from buildinfo
    # So we don't need to specify the repository parameter
    build_name = f"{project}/{build_number}"

    cmd = [
        'jfrog', 'rt', 'download',
        '--fail-no-op',
        '--exclusions', '-',  # Default exclusions from action.yml
        '--build', build_name
    ]

    result = subprocess.run(cmd, cwd=local_repo_dir, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to download artifacts: {result.stderr}\n{result.stdout}")

    print(f"Downloaded artifacts to {local_repo_dir}")


def delete_asc_files(local_repo_dir: str):
    """Delete all .asc signature files.

    Args:
        local_repo_dir: Local repository directory
    """
    asc_files = list(Path(local_repo_dir).rglob(ASC_PATTERN))

    if not asc_files:
        print("No .asc files found to delete")
        return

    print(f"Found {len(asc_files)} .asc files to delete")

    for asc_file in asc_files:
        asc_file.unlink()
        print(f"Deleted: {asc_file}")


def _calculate_file_checksums(file_path: Path) -> dict:
    """Calculate MD5, SHA1, and SHA256 checksums for a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with 'md5', 'sha1', 'sha256' keys
    """
    import hashlib
    with open(file_path, 'rb') as f:
        content = f.read()

    return {
        'md5': hashlib.md5(content).hexdigest(),
        'sha1': hashlib.sha1(content).hexdigest(),
        'sha256': hashlib.sha256(content).hexdigest()
    }


def _create_new_buildinfo(
    local_repo_dir: str,
    project: str,
    build_number: str,
    version: str,
    old_version: str,
    original_buildinfo: BuildInfo
) -> BuildInfo:
    """Create a new buildinfo based on the original, updating versions and artifact paths.

    Args:
        local_repo_dir: Local repository directory containing artifacts
        project: Project name
        build_number: New build number
        version: New version
        old_version: Old version to replace
        original_buildinfo: Original buildinfo to base the new one on

    Returns:
        New BuildInfo instance with updated versions and artifact paths
    """
    import hashlib
    import copy

    # Deep copy the original buildinfo JSON
    new_buildinfo_json = copy.deepcopy(original_buildinfo.json)

    # Update build name and number, and ensure required fields are present
    if 'buildInfo' in new_buildinfo_json:
        new_buildinfo_json['buildInfo']['name'] = project
        new_buildinfo_json['buildInfo']['number'] = build_number

        # Ensure started timestamp is present (required by Artifactory API)
        import datetime
        from datetime import timezone
        now = datetime.datetime.now(timezone.utc)
        timestamp_str = now.strftime(TIMESTAMP_FORMAT)[:-3] + TIMESTAMP_TZ
        timestamp_ms = int(now.timestamp() * 1000)

        new_buildinfo_json['buildInfo']['started'] = timestamp_str
        new_buildinfo_json['buildInfo']['startedDate'] = timestamp_ms

        # Update modules
        if 'modules' in new_buildinfo_json['buildInfo']:
            modules = new_buildinfo_json['buildInfo']['modules']

            print("\n=== Creating new buildinfo ===")
            print(f"Original modules: {len(modules)}")

            # First, scan local directory to find all artifacts and their checksums
            print("Scanning local artifacts...")
            local_artifacts = {}
            # Include SBOM files (*-cyclonedx.json, *-cyclonedx.xml) in addition to standard artifacts
            for ext in ['*.jar', '*.pom', '*.war', '*.ear', '*.asc', '*-cyclonedx.json', '*-cyclonedx.xml']:
                for artifact_file in Path(local_repo_dir).rglob(ext):
                    # Skip checksum files
                    if artifact_file.name.endswith(('.md5', '.sha1', '.sha256')):
                        continue

                    # Get relative path from local_repo_dir (this is the Artifactory path)
                    rel_path = str(artifact_file.relative_to(local_repo_dir))
                    checksums = _calculate_file_checksums(artifact_file)

                    local_artifacts[rel_path] = {
                        'path': rel_path,
                        'name': artifact_file.name,
                        'checksums': checksums,
                        'size': artifact_file.stat().st_size
                    }

            print(f"Found {len(local_artifacts)} local artifacts")

            # Update each module
            for module_idx, module in enumerate(modules):
                orig_module_id = module.get('id', '')
                print(f"\nProcessing module {module_idx + 1}: {orig_module_id}")

                # Update module ID with new version
                if ':' in orig_module_id:
                    parts = orig_module_id.split(':')
                    if len(parts) >= 3:
                        parts[-1] = version
                        module['id'] = ':'.join(parts)
                        print(f"  Updated module ID: {orig_module_id} -> {module['id']}")

                # Update artifacts in this module
                if 'artifacts' in module:
                    orig_artifacts = module['artifacts']
                    new_artifacts = []

                    print(f"  Original artifacts: {len(orig_artifacts)}")

                    for artifact in orig_artifacts:
                        orig_path = artifact.get('name', '')
                        orig_type = artifact.get('type', '')

                        # Replace old version with new version in the path
                        new_path = orig_path.replace(old_version, version)

                        # Try to find the artifact in local artifacts
                        # The artifact path might be stored as:
                        # 1. Full path: com/sonarsource/dummy/dummy/15.0.3.5000/dummy-15.0.3.5000.pom
                        # 2. Just filename: dummy-15.0.3.5000.pom
                        # 3. Relative path: ./com/sonarsource/...
                        local_artifact = None
                        if new_path in local_artifacts:
                            local_artifact = local_artifacts[new_path]
                        else:
                            # Try alternative path formats
                            alt_paths = [
                                new_path.lstrip('./'),
                                f'./{new_path}',
                                new_path.replace('\\', '/'),  # Normalize path separators
                            ]

                            # If path contains slashes, try matching by filename only
                            if '/' in new_path:
                                filename = new_path.split('/')[-1]
                                alt_paths.append(filename)

                            for alt_path in alt_paths:
                                if alt_path in local_artifacts:
                                    local_artifact = local_artifacts[alt_path]
                                    # Update new_path to use the matched path format
                                    new_path = alt_path
                                    break

                            # If still not found, try matching by filename across all local artifacts
                            if not local_artifact:
                                filename = new_path.split('/')[-1] if '/' in new_path else new_path
                                for local_path, local_data in local_artifacts.items():
                                    if local_data['name'] == filename:
                                        local_artifact = local_data
                                        new_path = local_path  # Use the full path from local artifacts
                                        break

                        if local_artifact:
                            # Extract just the filename from the path (Artifactory expects just filename, not full path)
                            # e.g., "com/sonarsource/dummy/dummy/15.0.3.5000/dummy-15.0.3.5000.pom" -> "dummy-15.0.3.5000.pom"
                            artifact_filename = os.path.basename(new_path)

                            new_artifact = {
                                'name': artifact_filename,  # Just the filename, not the full path
                                'type': orig_type,
                                'sha1': local_artifact['checksums']['sha1'],
                                'md5': local_artifact['checksums']['md5'],
                                'sha256': local_artifact['checksums']['sha256']
                            }
                            # Preserve other fields from original artifact (like size, etc.)
                            for key in ['size']:
                                if key in artifact:
                                    new_artifact[key] = artifact[key]
                            # Note: Artifactory links artifacts based on:
                            # 1. The repository in statuses
                            # 2. The artifact filename matching files in that repository
                            # 3. The checksums matching
                            new_artifacts.append(new_artifact)
                            print(f"    ✅ {orig_path} -> {artifact_filename} (path: {new_path})")
                        else:
                            print(f"    ⚠️  Warning: Artifact not found locally: {new_path}")
                            print(f"      Available local artifacts (first 5): {list(local_artifacts.keys())[:5]}")
                            # Still add it but with original checksums (will be updated by JFrog)
                            new_artifact = artifact.copy()
                            new_artifact['name'] = new_path
                            new_artifacts.append(new_artifact)

                    module['artifacts'] = new_artifacts
                    print(f"  New artifacts: {len(new_artifacts)}")

                    if len(new_artifacts) != len(orig_artifacts):
                        raise RuntimeError(
                            f"Module {module_idx + 1} ({orig_module_id}): "
                            f"Expected {len(orig_artifacts)} artifacts, but found {len(new_artifacts)}"
                        )

            print(f"\n✅ Created new buildinfo with {len(modules)} modules")

    return BuildInfo(new_buildinfo_json)


def _modify_exported_buildinfo(
    exported_buildinfo: BuildInfo,
    local_repo_dir: str,
    project: str,
    build_number: str,
    version: str,
    original_buildinfo: BuildInfo
) -> BuildInfo:
    """Modify exported buildinfo to match the original structure.

    This function takes a buildinfo that was automatically collected by JFrog CLI
    (which has artifacts already linked) and modifies it to match the original structure,
    preserving the artifact linking.

    Args:
        exported_buildinfo: BuildInfo instance exported from JFrog CLI
        local_repo_dir: Local repository directory
        project: Project name
        build_number: Build number
        version: New version
        original_buildinfo: Original buildinfo to match structure from

    Returns:
        Modified BuildInfo instance
    """
    import copy
    import os
    import hashlib

    # Deep copy the exported buildinfo to modify it
    new_buildinfo_json = copy.deepcopy(exported_buildinfo.json)

    # Update build name and number
    if 'buildInfo' in new_buildinfo_json:
        buildinfo_obj = new_buildinfo_json['buildInfo']
        buildinfo_obj['name'] = project
        buildinfo_obj['number'] = build_number

        # Update module IDs to use new version and match original structure
        modules = buildinfo_obj.get('modules', [])
        original_modules = original_buildinfo.json.get('buildInfo', {}).get('modules', [])

        for module_idx, module in enumerate(modules):
            if module_idx < len(original_modules):
                orig_module = original_modules[module_idx]
                orig_module_id = orig_module.get('id', '')

                # Update module ID with new version
                if ':' in orig_module_id:
                    parts = orig_module_id.split(':')
                    if len(parts) >= 3:
                        parts[2] = version  # Update version
                        module['id'] = ':'.join(parts)
                        print(f"  Updated module ID: {orig_module_id} -> {module['id']}")

        # Update artifact checksums to match local files (in case they changed)
        # The artifacts are already linked, so we just need to update checksums
        for module in modules:
            artifacts = module.get('artifacts', [])
            for artifact in artifacts:
                artifact_name = artifact.get('name', '')
                # Find the local file matching this artifact
                # Artifacts are stored with just filename, but files are in Maven structure
                local_file = None
                for root, dirs, files in os.walk(local_repo_dir):
                    if artifact_name in files:
                        local_file = os.path.join(root, artifact_name)
                        break

                if local_file and os.path.exists(local_file):
                    # Recalculate checksums from local file
                    with open(local_file, 'rb') as f:
                        content = f.read()
                        artifact['sha1'] = hashlib.sha1(content).hexdigest()
                        artifact['md5'] = hashlib.md5(content).hexdigest()
                        artifact['sha256'] = hashlib.sha256(content).hexdigest()

    return BuildInfo(new_buildinfo_json)


def create_and_upload_buildinfo(
    local_repo_dir: str,
    project: str,
    build_number: str,
    version: str,
    original_buildinfo: BuildInfo,
    artifactory=None,
    dry_run: bool = False
) -> Optional[BuildInfo]:
    """Upload artifacts and let JFrog CLI collect buildinfo, then validate it matches original.

    Args:
        local_repo_dir: Local repository directory
        project: Project name
        build_number: Build number
        version: New version (for validation purposes)
        original_buildinfo: Original buildinfo to compare against
        dry_run: If True, skip actual upload

    Returns:
        BuildInfo instance if successful, None if dry-run
    """
    # Determine target repository based on group ID
    # com.sonarsource -> sonarsource-private-releases
    # org.sonarsource -> sonarsource-public-releases
    # Upload directly to releases repositories with status "released"
    repo = 'sonarsource-public-releases'  # default for org.sonarsource
    group_id = None
    try:
        modules = original_buildinfo.json.get('buildInfo', {}).get('modules', [])
        if modules:
            # Extract group ID from first module (format: groupId:artifactId:version)
            first_module_id = modules[0].get('id', '')
            if ':' in first_module_id:
                group_id = first_module_id.split(':')[0]
                if group_id.startswith('com.sonarsource'):
                    repo = 'sonarsource-private-releases'
                elif group_id.startswith('org.sonarsource'):
                    repo = 'sonarsource-public-releases'
                else:
                    # Fallback: try to determine from original repository
                    if original_buildinfo.json.get('buildInfo', {}).get('statuses'):
                        original_repo = original_buildinfo.json['buildInfo']['statuses'][0].get('repository', repo)
                        # Convert builds to releases
                        if 'builds' in original_repo:
                            repo = original_repo.replace('builds', 'releases')
                        elif 'releases' in original_repo:
                            repo = original_repo
    except (KeyError, IndexError, AttributeError):
        pass

    print(f"Determined target repository: {repo} (group ID: {group_id or 'unknown'})")

    if dry_run:
        print("[DRY-RUN] Would upload artifacts and create buildinfo")
        print(f"[DRY-RUN] Build: {project}/{build_number}")
        print(f"[DRY-RUN] Version: {version}")
        print(f"[DRY-RUN] Target repository: {repo}")
        return None

    # Upload artifacts WITH build info collection to automatically link artifacts to buildinfo
    # Then we'll export, modify, and republish the buildinfo to match the original structure
    print("\nUploading artifacts (with buildinfo collection for automatic linking)...")

    # Change to local_repo_dir to ensure paths are relative
    # Use ANT pattern with parentheses to create capture group for placeholder
    # Pattern: (**/*) creates a capture group that matches all files recursively
    # The {1} placeholder will be replaced with the captured path relative to the working directory
    # Using --ant flag allows ANT-style patterns which work better with placeholders
    # Exclude checksum files - JFrog will generate them automatically
    # Note: With --ant flag, exclusions use ANT patterns: **/*.md5, **/*.sha1, **/*.sha256
    # IMPORTANT: We run from local_repo_dir (cwd), so **/* matches files relative to that directory
    # Use --build-name and --build-number to let JFrog CLI collect buildinfo and link artifacts automatically
    cmd = [
        'jfrog', 'rt', 'upload',
        '(**/*)',  # Match all files recursively with capture group (ANT pattern) - relative to cwd
        f'{repo}/{{1}}',  # Upload to repo with relative path preserved (placeholder will be replaced)
        '--ant',  # Use ANT pattern matching
        '--flat=false',  # Preserve directory structure
        '--recursive',  # Recursive upload
        '--exclusions', '**/*.md5;**/*.sha1;**/*.sha256',  # Exclude checksum files - JFrog will generate them
        '--build-name', project,  # Build name for buildinfo collection
        '--build-number', build_number,  # Build number for buildinfo collection
        '--fail-no-op'  # Fail if no files are uploaded
    ]

    print(f"Uploading artifacts to {repo}...")
    result = subprocess.run(cmd, cwd=local_repo_dir, capture_output=True, text=True)

    # Parse upload output to determine success
    combined_output = (result.stdout or '') + (result.stderr or '')
    import re
    import json as json_module

    # Try to parse JSON summary first (most reliable)
    json_match = re.search(r'\{[^}]*"status"[^}]*\}', combined_output, re.DOTALL)
    if json_match:
        try:
            summary_json = json_module.loads(json_match.group(0))
            totals = summary_json.get('totals', {})
            success_count = totals.get('success', 0)
            failure_count = totals.get('failure', 0)
            if success_count > 0:
                print(f"✅ Uploaded {success_count} artifacts")
            if failure_count > 0:
                print(f"⚠️  Warning: {failure_count} artifacts failed to upload")
            if success_count == 0 and failure_count == 0:
                raise RuntimeError("No artifacts were uploaded. Check the command output above.")
        except json_module.JSONDecodeError:
            pass

    # Check for text-based indicators
    no_op_match = re.search(r'No errors, but also no files affected', combined_output, flags=re.IGNORECASE)
    if no_op_match:
        raise RuntimeError("No files were uploaded. The pattern may not match any files.")

    failure_match = re.search(r'Failed uploading\s*(\d+)\s*artifacts?', combined_output, flags=re.IGNORECASE)
    if failure_match:
        failure_count = int(failure_match.group(1))
        if failure_count > 0:
            print(f"⚠️  Warning: {failure_count} artifacts failed to upload")

    if result.returncode != 0:
        print(f"\n❌ Command failed with return code {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        raise RuntimeError(f"Failed to upload artifacts: {result.stderr}\n{result.stdout}")

    print("Artifacts uploaded successfully with buildinfo collection")

    # Export the buildinfo that was automatically collected by JFrog CLI
    print("\nExporting buildinfo collected by JFrog CLI...")
    import tempfile
    exported_buildinfo_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    exported_buildinfo_path = exported_buildinfo_file.name
    exported_buildinfo_file.close()

    try:
        # Export buildinfo using jfrog rt build-export
        export_cmd = [
            'jfrog', 'rt', 'build-export',
            project,
            build_number,
            exported_buildinfo_path
        ]
        print(f"Exporting buildinfo: {' '.join(export_cmd)}")
        export_result = subprocess.run(export_cmd, capture_output=True, text=True)

        if export_result.returncode != 0:
            # Buildinfo export failed, will fall back to manual creation
            exported_buildinfo = None
        else:
            # Load the exported buildinfo
            import json as json_module
            with open(exported_buildinfo_path, 'r') as f:
                exported_buildinfo_json = json_module.load(f)
            exported_buildinfo = BuildInfo(exported_buildinfo_json)
            print("✅ Buildinfo exported successfully")
    except Exception:
        # Buildinfo export failed, will fall back to manual creation
        exported_buildinfo = None
    finally:
        # Clean up temp file
        if os.path.exists(exported_buildinfo_path):
            os.remove(exported_buildinfo_path)

    # Now create/modify buildinfo matching the original structure
    print("\nCreating/modifying buildinfo to match original structure...")
    original_modules = original_buildinfo.json.get('buildInfo', {}).get('modules', [])
    old_version = None

    # Extract old version from first module ID (format: groupId:artifactId:version)
    if original_modules:
        first_module_id = original_modules[0].get('id', '')
        if ':' in first_module_id:
            parts = first_module_id.split(':')
            if len(parts) >= 3:
                old_version = parts[2]

    if not old_version:
        # Fallback: try to extract from artifact paths in the original buildinfo
        if original_modules and original_modules[0].get('artifacts'):
            first_artifact_name = original_modules[0]['artifacts'][0].get('name', '')
            # Try to extract version from path like: com/sonarsource/dummy/dummy/15.0.2.8567/...
            import re
            version_match = re.search(r'/(\d+\.\d+\.\d+\.\d+)/', first_artifact_name)
            if version_match:
                old_version = version_match.group(1)

    if not old_version:
        raise RuntimeError(
            f"Could not extract old version from buildinfo. "
            f"Module IDs: {[m.get('id', '') for m in original_modules]}"
        )

    print(f"Extracted old version: {old_version}")

    # If we successfully exported buildinfo from JFrog CLI, use it as a base and modify it
    # Otherwise, create buildinfo manually
    if exported_buildinfo:
        # Use the exported buildinfo as a base, but modify it to match the original structure
        # This preserves the automatic linking that JFrog CLI created
        print("Using exported buildinfo as base and modifying to match original structure...")
        new_buildinfo = _modify_exported_buildinfo(
            exported_buildinfo,
            local_repo_dir,
            project,
            build_number,
            version,
            original_buildinfo
        )
    else:
        # Fall back to manual creation
        print("Creating buildinfo manually...")
        new_buildinfo = _create_new_buildinfo(
            local_repo_dir,
            project,
            build_number,
            version,
            old_version,
            original_buildinfo
        )

    # Update the repository in buildinfo statuses to match where we uploaded
    if 'buildInfo' in new_buildinfo.json:
        # Update or create statuses to point to the correct repository
        # Status must include: status, repository, timestamp, and timestampDate
        import datetime
        from datetime import timezone
        now = datetime.datetime.now(timezone.utc)
        timestamp_str = now.strftime(TIMESTAMP_FORMAT)[:-3] + TIMESTAMP_TZ
        timestamp_ms = int(now.timestamp() * 1000)

        # Remove old statuses and add new one for the target repository
        # Set status to "released" since we're uploading directly to releases repository
        new_buildinfo.json['buildInfo']['statuses'] = [{
            'repository': repo,
            'status': 'released',
            'timestamp': timestamp_str,
            'timestampDate': timestamp_ms
        }]
        print(f"Updated buildinfo statuses to repository: {repo} with status 'released'")

    print("Buildinfo created successfully")

    # Publish the manually created buildinfo via REST API using Python requests
    print("\nPublishing buildinfo via REST API...")
    if not artifactory:
        # Try to get from environment if artifactory client not provided
        artifactory_url = os.environ.get('ARTIFACTORY_URL', 'https://repox.jfrog.io/repox')
        artifactory_token = os.environ.get('ARTIFACTORY_ACCESS_TOKEN')
        if not artifactory_token:
            raise RuntimeError("Artifactory client or ARTIFACTORY_ACCESS_TOKEN is required to publish buildinfo")
        headers = {
            'Authorization': f'Bearer {artifactory_token}',
            'Content-Type': 'application/json'
        }
    else:
        artifactory_url = artifactory.url
        headers = artifactory.headers

    # Publish buildinfo via REST API
    url = f"{artifactory_url}/api/build"

    # Ensure all required fields are present
    import copy
    buildinfo_json = copy.deepcopy(new_buildinfo.json)
    if 'buildInfo' in buildinfo_json:
        # Ensure required fields are present
        buildinfo_obj = buildinfo_json['buildInfo']
        if 'name' not in buildinfo_obj:
            buildinfo_obj['name'] = project
        if 'number' not in buildinfo_obj:
            buildinfo_obj['number'] = build_number
        if 'started' not in buildinfo_obj:
            import datetime
            from datetime import timezone
            now = datetime.datetime.now(timezone.utc)
            timestamp_str = now.strftime(TIMESTAMP_FORMAT)[:-3] + TIMESTAMP_TZ
            buildinfo_obj['started'] = timestamp_str
        if 'startedDate' not in buildinfo_obj:
            import time
            buildinfo_obj['startedDate'] = int(time.time() * 1000)  # milliseconds since epoch

    # The Artifactory API expects the buildInfo object directly, not wrapped
    if 'buildInfo' not in buildinfo_json:
        raise RuntimeError("buildInfo object not found in buildinfo JSON")

    # Send just the buildInfo object, not the wrapper
    payload = buildinfo_json['buildInfo']

    print(f"Publishing buildinfo: {buildinfo_obj.get('name')}/{buildinfo_obj.get('number')}")
    response = requests.put(url, headers=headers, json=payload)

    if response.status_code not in [200, 201, 204]:
        raise RuntimeError(f"Failed to publish buildinfo: HTTP {response.status_code} - {response.text}")

    print("Buildinfo published successfully")

    # Validate that new buildinfo matches original structure
    print("\nValidating buildinfo structure...")
    # original_modules was already extracted above, reuse it
    new_modules = new_buildinfo.json.get('buildInfo', {}).get('modules', [])

    if len(new_modules) != len(original_modules):
        print("\n❌ ERROR: Module count mismatch!")
        print(f"Original modules: {len(original_modules)}")
        print(f"New modules: {len(new_modules)}")
        print("\nOriginal module IDs:")
        for i, module in enumerate(original_modules):
            module_id = module.get('id', 'unknown')
            artifacts = module.get('artifacts', [])
            print(f"  [{i}] {module_id} ({len(artifacts)} artifacts)")
        print("\nNew module IDs:")
        for i, module in enumerate(new_modules):
            module_id = module.get('id', 'unknown')
            artifacts = module.get('artifacts', [])
            print(f"  [{i}] {module_id} ({len(artifacts)} artifacts)")
        raise RuntimeError(
            f"Buildinfo validation failed: Expected {len(original_modules)} modules, "
            f"but new buildinfo has {len(new_modules)} modules. "
            "Not all artifacts were uploaded correctly."
        )

    # Verify each module has the expected artifacts
    for i, (orig_module, new_module) in enumerate(zip(original_modules, new_modules)):
        orig_artifacts = orig_module.get('artifacts', [])
        new_artifacts = new_module.get('artifacts', [])

        if len(new_artifacts) != len(orig_artifacts):
            orig_id = orig_module.get('id', 'unknown')
            raise RuntimeError(
                f"Buildinfo validation failed: Module {i+1} ({orig_id}) has "
                f"{len(orig_artifacts)} artifacts in original but {len(new_artifacts)} "
                f"in new buildinfo. Not all artifacts were uploaded."
            )

    print("✅ Buildinfo validation passed! All modules and artifacts match.")

    return new_buildinfo


def promote_build_to_releases(
    artifactory,
    project: str,
    build_number: str,
    buildinfo: BuildInfo,
    dry_run: bool = False
):
    """Promote build to the corresponding release repository with status 'released'.

    Args:
        artifactory: Artifactory client instance
        project: Project name
        build_number: Build number
        buildinfo: BuildInfo instance to determine repositories
        dry_run: If True, skip actual promotion
    """
    if dry_run:
        print("[DRY-RUN] Would promote build to release repository")
        return

    # Determine source and target repositories based on group ID
    source_repo = 'sonarsource-public-builds'  # default
    target_repo = 'sonarsource-public-releases'  # default

    try:
        modules = buildinfo.json.get('buildInfo', {}).get('modules', [])
        if modules:
            # Extract group ID from first module (format: groupId:artifactId:version)
            first_module_id = modules[0].get('id', '')
            if ':' in first_module_id:
                group_id = first_module_id.split(':')[0]
                if group_id.startswith('com.sonarsource'):
                    source_repo = 'sonarsource-private-builds'
                    target_repo = 'sonarsource-private-releases'
                elif group_id.startswith('org.sonarsource'):
                    source_repo = 'sonarsource-public-builds'
                    target_repo = 'sonarsource-public-releases'
    except (KeyError, IndexError, AttributeError):
        pass

    print(f"\nPromoting build {project}/{build_number} to {target_repo}...")
    print(f"  Source repository: {source_repo}")
    print(f"  Target repository: {target_repo}")
    print(f"  Status: released")

    # Prepare promotion request
    if not artifactory:
        # Try to get from environment if artifactory client not provided
        artifactory_url = os.environ.get('ARTIFACTORY_URL', 'https://repox.jfrog.io/repox')
        artifactory_token = os.environ.get('ARTIFACTORY_ACCESS_TOKEN')
        if not artifactory_token:
            raise RuntimeError("Artifactory client or ARTIFACTORY_ACCESS_TOKEN is required to promote build")
        headers = {
            'Authorization': f'Bearer {artifactory_token}',
            'Content-Type': 'application/json'
        }
    else:
        artifactory_url = artifactory.url
        headers = artifactory.headers

    # Promote build via REST API
    url = f"{artifactory_url}/api/build/promote/{project}/{build_number}"

    payload = {
        "status": "released",
        "sourceRepo": source_repo,
        "targetRepo": target_repo
    }

    print(f"Promoting build: {url}")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [200, 201, 204]:
        raise RuntimeError(f"Failed to promote build: HTTP {response.status_code} - {response.text}")

    print("✅ Build promoted successfully")


def upload_to_binaries(
    artifactory,
    binaries,
    project: str,
    build_number: str,
    version: str,
    buildinfo: BuildInfo,
    dry_run: bool = False
):
    """Upload artifacts to binaries.sonarsource.com.

    Args:
        artifactory: Artifactory client instance
        binaries: Binaries client instance
        project: Project name
        build_number: Build number
        version: Version
        buildinfo: BuildInfo instance
        dry_run: If True, skip actual upload
    """
    if dry_run:
        print("[DRY-RUN] Would upload to binaries.sonarsource.com")
        return

    from release.utils.release import publish_all_artifacts_to_binaries
    from release.steps.ReleaseRequest import ReleaseRequest

    release_request = ReleaseRequest(
        org='',
        project=project,
        version=version,
        buildnumber=build_number,
        branch='',
        sha=''
    )

    # Update buildinfo version in the JSON and ensure ARTIFACTORY_DEPLOY_REPO is set
    buildinfo_json = buildinfo.json.copy()
    if 'buildInfo' in buildinfo_json:
        # Ensure properties exist
        if 'properties' not in buildinfo_json['buildInfo']:
            buildinfo_json['buildInfo']['properties'] = {}

        # Set ARTIFACTORY_DEPLOY_REPO property based on group ID
        # This is needed for binaries upload to know which repository to use
        modules = buildinfo_json['buildInfo'].get('modules', [])
        if modules:
            first_module_id = modules[0].get('id', '')
            if ':' in first_module_id:
                group_id = first_module_id.split(':')[0]
                if group_id.startswith('com.sonarsource'):
                    deploy_repo = 'sonarsource-private-releases'
                elif group_id.startswith('org.sonarsource'):
                    deploy_repo = 'sonarsource-public-releases'
                else:
                    deploy_repo = 'sonarsource-public-releases'  # default

                buildinfo_json['buildInfo']['properties']['buildInfo.env.ARTIFACTORY_DEPLOY_REPO'] = deploy_repo

        # Update module versions
        if 'modules' in buildinfo_json['buildInfo']:
            for module in buildinfo_json['buildInfo']['modules']:
                if 'id' in module:
                    # Update version in module ID (format: groupId:artifactId:version)
                    parts = module['id'].split(':')
                    if len(parts) >= 3:
                        parts[-1] = version
                        module['id'] = ':'.join(parts)

    updated_buildinfo = BuildInfo(buildinfo_json)

    publish_all_artifacts_to_binaries(artifactory, binaries, release_request, updated_buildinfo)


def should_upload_to_maven_central(buildinfo: BuildInfo) -> bool:
    """Check if artifacts should be uploaded to Maven Central.

    Args:
        buildinfo: BuildInfo instance

    Returns:
        True if artifacts should be uploaded to Maven Central
    """
    artifacts_to_publish = buildinfo.get_artifacts_to_publish()
    if not artifacts_to_publish:
        return False

    # Check if any artifact has group ID starting with org.sonarsource
    artifacts = artifacts_to_publish.split(",")
    for artifact in artifacts:
        parts = artifact.split(":")
        if len(parts) > 0 and parts[0].startswith("org.sonarsource"):
            return True
    return False


def _generate_maven_central_checksums(local_repo_dir: str):
    """Generate MD5 and SHA1 checksum files required by Maven Central.

    Maven Central requires MD5 and SHA1 checksum files for all artifacts.
    This function generates these checksum files for all relevant files.

    Args:
        local_repo_dir: Local repository directory containing files
    """
    import hashlib

    # Find all files that need checksums (artifacts, POMs, SBOMs, signatures, module files)
    # Exclude existing checksum files
    patterns = [
        '*.jar', '*.pom', '*.war', '*.ear',
        '*.asc',  # Signatures
        '*.module',  # Module files
        '*-cyclonedx.json', '*-cyclonedx.xml',  # SBOM files
        'maven-metadata.xml'
    ]

    files_to_checksum = []
    for pattern in patterns:
        files_to_checksum.extend(Path(local_repo_dir).rglob(pattern))

    # Filter out checksum files themselves
    files_to_checksum = [f for f in files_to_checksum
                        if not f.name.endswith(('.md5', '.sha1', '.sha256'))]

    if not files_to_checksum:
        print("No files found to generate checksums for")
        return

    print(f"Generating MD5 and SHA1 checksums for {len(files_to_checksum)} files...")

    checksum_count = 0
    for file_path in files_to_checksum:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # Generate MD5 checksum file if it doesn't exist
            md5_file = Path(f'{file_path}.md5')
            if not md5_file.exists():
                md5 = hashlib.md5(content).hexdigest()
                md5_file.write_text(md5)
                checksum_count += 1

            # Generate SHA1 checksum file if it doesn't exist
            sha1_file = Path(f'{file_path}.sha1')
            if not sha1_file.exists():
                sha1 = hashlib.sha1(content).hexdigest()
                sha1_file.write_text(sha1)
                checksum_count += 1

        except Exception as e:
            print(f"Warning: Failed to generate checksums for {file_path}: {e}")

    if checksum_count > 0:
        print(f"✅ Generated {checksum_count} checksum files")


def upload_to_maven_central(
    local_repo_dir: str,
    vault_client: Optional[object],
    dry_run: bool = False
):
    """Upload artifacts to Maven Central Portal.

    Args:
        local_repo_dir: Local repository directory
        vault_client: Vault client instance (optional)
        dry_run: If True, skip actual upload
    """
    # Try to get CENTRAL_TOKEN from Vault first, then environment
    central_token = None
    if vault_client:
        try:
            central_token = vault_client.read_secret('development/kv/data/ossrh', 'token')
            print("Retrieved Maven Central token from Vault")
        except Exception as e:
            print(f"Warning: Failed to get Maven Central token from Vault: {e}")

    if not central_token:
        central_token = os.environ.get('CENTRAL_TOKEN')

    if not central_token:
        raise ValueError(
            "CENTRAL_TOKEN is required for Maven Central upload. Provide via:\n"
            "  - Vault (--vault-token, will retrieve from development/kv/data/ossrh)\n"
            "  - Environment variable CENTRAL_TOKEN"
        )

    central_url = os.environ.get('CENTRAL_URL', 'https://central.sonatype.com')
    auto_publish = os.environ.get('CENTRAL_AUTO_PUBLISH', 'true')

    if dry_run:
        print("[DRY-RUN] Would upload to Maven Central")
        print(f"[DRY-RUN] Central URL: {central_url}")
        print(f"[DRY-RUN] Auto-publish: {auto_publish}")
        return

    # Check if we have artifacts to publish
    artifact_count = len(list(Path(local_repo_dir).rglob('*.jar'))) + \
                    len(list(Path(local_repo_dir).rglob('*.pom'))) + \
                    len(list(Path(local_repo_dir).rglob('*.war'))) + \
                    len(list(Path(local_repo_dir).rglob('*.ear')))

    if artifact_count == 0:
        print("No artifacts found to upload to Maven Central")
        return

    print(f"Found {artifact_count} artifacts to upload to Maven Central")

    # Generate MD5 and SHA1 checksum files required by Maven Central
    print("Generating MD5 and SHA1 checksums for Maven Central...")
    _generate_maven_central_checksums(local_repo_dir)

    # Create bundle zip file
    bundle_dir = tempfile.mkdtemp()
    bundle_file = os.path.join(bundle_dir, 'central-bundle.zip')

    try:
        print("Creating deployment bundle...")
        # Create zip preserving Maven repository structure
        # Include all files including checksum files (.md5, .sha1) and signatures (.asc)
        with zipfile.ZipFile(bundle_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(local_repo_dir):
                # Skip hidden files and directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    if file in ['.DS_Store', 'Thumbs.db']:
                        continue
                    # Skip SHA256 checksums (Maven Central doesn't require them)
                    if file.endswith('.sha256'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, local_repo_dir)
                    zipf.write(file_path, arcname)

        bundle_size = os.path.getsize(bundle_file)
        print(f"Bundle created: {bundle_size} bytes")

        # Determine publishing type
        publishing_type = "AUTOMATIC" if auto_publish.lower() == "true" else "USER_MANAGED"
        print(f"Publishing type: {publishing_type}")

        # Upload to Central Portal using curl (more reliable for multipart)
        print("Uploading to Central Portal...")
        url = f"{central_url}/api/v1/publisher/upload?publishingType={publishing_type}"

        cmd = [
            'curl', '-s', '-w', 'HTTPSTATUS:%{http_code}',
            '-X', 'POST',
            '-H', f'Authorization: Bearer {central_token}',
            '-F', f'bundle=@{bundle_file}',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse response
        http_status_match = re.search(r'HTTPSTATUS:(\d+)', result.stdout)
        if http_status_match:
            http_status = int(http_status_match.group(1))
            response_body = result.stdout.replace('HTTPSTATUS:' + str(http_status), '').strip()
        else:
            # Fallback: check stderr or use return code
            http_status = result.returncode if result.returncode != 0 else 200
            response_body = result.stdout + result.stderr

        if http_status != 201:
            raise RuntimeError(f"Maven Central upload failed with status {http_status}: {response_body}")

        deployment_id = response_body.strip()
        print(f"✅ Upload successful! Deployment ID: {deployment_id}")

        # Poll for deployment status
        poll_maven_central_status(central_url, central_token, deployment_id)
    finally:
        # Cleanup
        if os.path.exists(bundle_file):
            os.remove(bundle_file)
        os.rmdir(bundle_dir)


def poll_maven_central_status(central_url: str, central_token: str, deployment_id: str):
    """Poll Maven Central deployment status until completion.

    Args:
        central_url: Maven Central URL
        central_token: Maven Central token
        deployment_id: Deployment ID
    """
    max_attempts = 720  # 2 hours (720 * 10s)
    poll_interval = 10  # 10 seconds
    attempt = 1

    print("Polling deployment status...")

    while attempt <= max_attempts:
        print(f"Checking deployment status (attempt {attempt}/{max_attempts})...")

        url = f"{central_url}/api/v1/publisher/status?id={deployment_id}"
        cmd = [
            'curl', '-s', '-w', 'HTTPSTATUS:%{http_code}',
            '-X', 'POST',
            '-H', f'Authorization: Bearer {central_token}',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse response
        http_status_match = re.search(r'HTTPSTATUS:(\d+)', result.stdout)
        if http_status_match:
            http_status = int(http_status_match.group(1))
            response_body = result.stdout.replace('HTTPSTATUS:' + str(http_status), '').strip()
        else:
            http_status = 200
            response_body = result.stdout

        if http_status >= 200 and http_status < 300:
            # Extract deployment state
            try:
                status_data = json.loads(response_body)
                deployment_state = status_data.get('deploymentState', 'UNKNOWN')
            except json.JSONDecodeError:
                # Try regex fallback
                match = re.search(r'"deploymentState":"([^"]+)"', response_body)
                deployment_state = match.group(1) if match else 'UNKNOWN'

            print(f"Current deployment state: {deployment_state}")

            if deployment_state in ["VALIDATED", "PUBLISHING", "PUBLISHED"]:
                print(f"✅ Deployment successful with state: {deployment_state}")
                return
            elif deployment_state == "FAILED":
                raise RuntimeError(f"❌ Deployment failed validation. Response: {response_body}")
            elif deployment_state in ["PENDING", "VALIDATING"]:
                print(f"⏳ Deployment is still being processed (state: {deployment_state})...")
            else:
                print(f"Unknown deployment state: {deployment_state}")
        else:
            print(f"Warning: Status check failed with HTTP {http_status}")

        if attempt < max_attempts:
            print(f"Waiting {poll_interval} seconds before next check...")
            time.sleep(poll_interval)

        attempt += 1

    raise RuntimeError(
        f"❌ Timeout: Deployment did not reach a final state within "
        f"{max_attempts * poll_interval / 3600} hours. "
        f"Check deployment status manually using: "
        f"{central_url}/api/v1/publisher/status?id={deployment_id}"
    )

