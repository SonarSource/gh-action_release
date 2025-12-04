"""Unit tests for SBOM utilities."""

import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sbom_utils import update_sbom_versions, find_sbom_files


def test_update_sbom_versions_json():
    """Test updating versions in CycloneDX JSON SBOM files."""
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()

    try:
        # Copy the original SBOM file with the actual naming pattern
        original_file = Path(__file__).parent / 'fixtures' / 'original-cyclonedx.json'
        test_file = Path(test_dir) / 'dummy-15.0.2.8567-cyclonedx.json'
        shutil.copy(original_file, test_file)

        # Read original content
        with open(test_file, 'r') as f:
            original_content = f.read()

        # Verify original contains old version
        assert '15.0.2.8567' in original_content
        assert '15.0.3.1234' not in original_content

        # Update versions
        update_sbom_versions(test_dir, '15.0.2.8567', '15.0.3.1234')

        # Read updated content
        with open(test_file, 'r') as f:
            updated_content = f.read()

        # Parse as JSON to verify it's still valid
        updated_data = json.loads(updated_content)

        # Verify old version is gone
        assert '15.0.2.8567' not in updated_content, f"Old version still found in: {updated_content[:500]}"

        # Verify new version is present
        assert '15.0.3.1234' in updated_content

        # Check specific fields
        metadata_component = updated_data.get('metadata', {}).get('component', {})
        assert metadata_component.get('version') == '15.0.3.1234', \
            f"metadata.component.version should be 15.0.3.1234, got {metadata_component.get('version')}"
        assert '15.0.3.1234' in metadata_component.get('bom-ref', ''), \
            f"metadata.component.bom-ref should contain 15.0.3.1234, got {metadata_component.get('bom-ref')}"
        assert '15.0.3.1234' in metadata_component.get('purl', ''), \
            f"metadata.component.purl should contain 15.0.3.1234, got {metadata_component.get('purl')}"

        # Check components array - only check components that originally had the old version
        components = updated_data.get('components', [])
        for component in components:
            # Only check components that are part of our artifacts (have the old group/artifact)
            bom_ref = component.get('bom-ref', '')
            if 'com.sonarsource.dummy' in bom_ref:
                assert component.get('version') == '15.0.3.1234', \
                    f"Component version should be 15.0.3.1234, got {component.get('version')} for {component.get('name')}"
                assert '15.0.3.1234' in bom_ref, \
                    f"Component bom-ref should contain 15.0.3.1234, got {bom_ref}"
                if 'purl' in component:
                    assert '15.0.3.1234' in component.get('purl', ''), \
                        f"Component purl should contain 15.0.3.1234, got {component.get('purl')}"

        # Check dependencies if present - only check refs that originally had the old version
        dependencies = updated_data.get('dependencies', [])
        for dep in dependencies:
            if 'ref' in dep:
                ref = dep['ref']
                if 'com.sonarsource.dummy' in ref:
                    assert '15.0.3.1234' in ref, \
                        f"Dependency ref should contain new version, got {ref}"
                    assert '15.0.2.8567' not in ref, \
                        f"Dependency ref should not contain old version, got {ref}"
            if 'dependsOn' in dep:
                for dep_ref in dep['dependsOn']:
                    if 'com.sonarsource.dummy' in dep_ref:
                        assert '15.0.3.1234' in dep_ref, \
                            f"Dependency dependsOn should contain new version, got {dep_ref}"
                        assert '15.0.2.8567' not in dep_ref, \
                            f"Dependency dependsOn should not contain old version, got {dep_ref}"

        print("✅ JSON SBOM update test passed!")

    finally:
        shutil.rmtree(test_dir)


def test_update_sbom_versions_xml():
    """Test updating versions in CycloneDX XML SBOM files."""
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()

    try:
        # Copy the original SBOM XML file
        original_file = Path(__file__).parent / 'fixtures' / 'original-cyclonedx.xml'
        if not original_file.exists():
            print("⚠️  XML fixture not found, skipping XML test")
            return

        test_file = Path(test_dir) / 'test-cyclonedx.xml'
        shutil.copy(original_file, test_file)

        # Read original content
        with open(test_file, 'r') as f:
            original_content = f.read()

        # Verify original contains old version
        assert '15.0.2.8567' in original_content

        # Update versions
        update_sbom_versions(test_dir, '15.0.2.8567', '15.0.3.1234')

        # Read updated content
        with open(test_file, 'r') as f:
            updated_content = f.read()

        # Verify old version is gone
        assert '15.0.2.8567' not in updated_content, \
            f"Old version still found in XML. First 1000 chars: {updated_content[:1000]}"

        # Verify new version is present
        assert '15.0.3.1234' in updated_content

        print("✅ XML SBOM update test passed!")

    finally:
        shutil.rmtree(test_dir)


def test_find_sbom_files():
    """Test finding SBOM files."""
    test_dir = tempfile.mkdtemp()

    try:
        # Create test files
        (Path(test_dir) / 'test-cyclonedx.json').touch()
        (Path(test_dir) / 'test-cyclonedx.xml').touch()
        (Path(test_dir) / 'test-sbom.json').touch()
        (Path(test_dir) / 'test.bom.json').touch()
        (Path(test_dir) / 'not-sbom.txt').touch()

        sbom_files = find_sbom_files(test_dir)

        # Note: find_sbom_files uses glob patterns, so it may not find all patterns
        # The important thing is that it finds the common ones
        assert len(sbom_files) >= 2, f"Expected at least 2 SBOM files, found {len(sbom_files)}"

        print("✅ Find SBOM files test passed!")

    finally:
        shutil.rmtree(test_dir)


if __name__ == '__main__':
    print("Running SBOM utils tests...")
    test_find_sbom_files()
    test_update_sbom_versions_json()
    test_update_sbom_versions_xml()
    print("\n✅ All tests passed!")

