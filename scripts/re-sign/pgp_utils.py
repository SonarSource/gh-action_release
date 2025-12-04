"""Utilities for GPG/PGP signing operations."""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class PGPManager:
    """Manager for GPG key operations and artifact signing."""

    def __init__(self, vault_client, local_repo_dir: str):
        self.vault_client = vault_client
        self.local_repo_dir = local_repo_dir
        self.gpg_key_id: Optional[str] = None
        self.gpg_passphrase: Optional[str] = None
        self.gpg_key_imported = False

    def import_gpg_key(self) -> str:
        """Import GPG key from Vault and retrieve passphrase.

        Returns:
            GPG key ID
        """
        if not self.vault_client:
            raise RuntimeError(
                "Vault client is required to retrieve GPG key. Provide --vault-token or set VAULT_TOKEN environment variable."
            )

        # Retrieve GPG key from Vault
        vault_path = 'development/kv/data/sign'
        key_name = 'key'

        print(f"Retrieving GPG key from Vault: {vault_path} (key: {key_name})")
        try:
            key_content = self.vault_client.read_secret(vault_path, key_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to retrieve GPG key from Vault: {e}\n"
                f"Make sure:\n"
                f"  1. Vault token has access to {vault_path}\n"
                f"  2. The key '{key_name}' exists in the secret"
            )

        # Import the key into GPG
        # Use --batch and --no-tty to avoid interactive prompts and agent issues
        # --pinentry-mode loopback allows non-interactive key import
        import_cmd = [
            'gpg',
            '--batch',
            '--no-tty',
            '--pinentry-mode', 'loopback',
            '--import'
        ]

        # Set environment to disable GPG agent if needed
        env = os.environ.copy()
        env['GPG_TTY'] = '/dev/tty' if os.path.exists('/dev/tty') else '/dev/null'
        # Disable GPG agent to avoid ioctl errors
        env.pop('GPG_AGENT_INFO', None)

        import_result = subprocess.run(import_cmd, input=key_content, text=True,
                                      capture_output=True, env=env)

        # Check if import was successful by looking at the output
        # GPG may return non-zero exit code due to agent errors, but still import the key
        # GPG outputs import status to stderr, not stdout
        import_success = False
        imported_count = 0

        # Combine stdout and stderr for checking (GPG outputs to stderr)
        combined_output = import_result.stdout + import_result.stderr

        # Look for "imported: N" or "secret keys imported: N" pattern
        imported_match = re.search(r'(?:imported|secret keys imported):\s*(\d+)', combined_output, re.IGNORECASE)
        if imported_match:
            imported_count = int(imported_match.group(1))
            if imported_count > 0:
                import_success = True

        # Also check for "secret keys read: N" as an indicator of success
        secret_keys_match = re.search(r'secret keys read:\s*(\d+)', combined_output, re.IGNORECASE)
        if secret_keys_match and int(secret_keys_match.group(1)) > 0:
            import_success = True

        # Also check for "unchanged: N" - key was already imported but that's fine
        unchanged_match = re.search(r'unchanged:\s*(\d+)', combined_output, re.IGNORECASE)
        if unchanged_match and int(unchanged_match.group(1)) > 0:
            # Key was already imported, that's fine - check if we can use it
            import_success = True

        # Only fail if no keys were imported/read and return code is non-zero
        if not import_success and import_result.returncode != 0:
            raise RuntimeError(
                f"Failed to import GPG key. No keys were imported.\n"
                f"STDOUT: {import_result.stdout}\n"
                f"STDERR: {import_result.stderr}\n"
                f"Return code: {import_result.returncode}"
            )

        # Extract key ID from the imported key output
        # Look for "key XXXXXX" pattern (the key ID that was imported)
        # Check both stdout and stderr
        key_id_match = re.search(r'key\s+([A-F0-9]+)', combined_output, re.IGNORECASE)
        if key_id_match:
            self.gpg_key_id = key_id_match.group(1)
            print(f"Imported GPG key: {self.gpg_key_id}")
        else:
            # Try to get key ID from key content directly
            key_id_match = re.search(r'^pub\s+.*/([A-F0-9]{16})', key_content, re.MULTILINE | re.IGNORECASE)
            if key_id_match:
                self.gpg_key_id = key_id_match.group(1)
                print(f"Extracted GPG key ID from key content: {self.gpg_key_id}")
            else:
                # List keys to find the one we just imported
                list_cmd = ['gpg', '--list-secret-keys', '--keyid-format', 'LONG', '--batch', '--no-tty']
                list_result = subprocess.run(list_cmd, capture_output=True, text=True, env=env)
                # Extract the most recent key ID
                key_id_match = re.search(r'sec\s+.*/([A-F0-9]{16})', list_result.stdout)
                if key_id_match:
                    self.gpg_key_id = key_id_match.group(1)
                    print(f"Found GPG key ID from keyring: {self.gpg_key_id}")
                else:
                    raise RuntimeError(
                        f"Could not determine GPG key ID after import.\n"
                        f"Import STDOUT: {import_result.stdout}\n"
                        f"Import STDERR: {import_result.stderr}\n"
                        f"List keys output: {list_result.stdout}"
                    )

        self.gpg_key_imported = True
        print(f"Using GPG key ID: {self.gpg_key_id}")

        # Retrieve GPG passphrase from Vault
        vault_path = 'development/kv/data/sign'
        passphrase_name = 'passphrase'

        print(f"Retrieving GPG passphrase from Vault: {vault_path} (key: {passphrase_name})")
        try:
            self.gpg_passphrase = self.vault_client.read_secret(vault_path, passphrase_name)
            print("Retrieved GPG passphrase from Vault")
        except Exception as e:
            raise RuntimeError(
                f"Failed to retrieve GPG passphrase from Vault: {e}\n"
                f"Make sure:\n"
                f"  1. Vault token has access to {vault_path}\n"
                f"  2. The key '{passphrase_name}' exists in the secret"
            )

        return self.gpg_key_id

    def sign_artifacts(self):
        """Sign all artifacts that need signing (.jar, .pom, .war, .ear, and SBOM files)."""
        if not self.gpg_key_id or not self.gpg_passphrase:
            raise RuntimeError("GPG key and passphrase must be imported before signing")

        # Find all files that need signing
        # Include standard artifacts, SBOM files (cyclonedx.json, cyclonedx.xml), and module files
        patterns = ['*.jar', '*.pom', '*.war', '*.ear', '*-cyclonedx.json', '*-cyclonedx.xml', '*.module']
        files_to_sign = []

        for pattern in patterns:
            files_to_sign.extend(Path(self.local_repo_dir).rglob(pattern))

        # Filter out .asc files and checksum files
        files_to_sign = [f for f in files_to_sign if not f.name.endswith('.asc')
                        and not f.name.endswith('.md5')
                        and not f.name.endswith('.sha1')
                        and not f.name.endswith('.sha256')]

        if not files_to_sign:
            print("No files found to sign")
            return

        print(f"Found {len(files_to_sign)} files to sign")

        # Set up environment for GPG signing
        env = os.environ.copy()
        env['GPG_TTY'] = '/dev/tty' if os.path.exists('/dev/tty') else '/dev/null'
        env.pop('GPG_AGENT_INFO', None)

        # Sign each file
        for file_path in files_to_sign:
            print(f"Signing: {file_path}")
            cmd = [
                'gpg',
                '--batch',
                '--no-tty',
                '--pinentry-mode', 'loopback',
                '--armor',
                '--detach-sign',
                '--local-user', self.gpg_key_id,
                '--passphrase-fd', '0',  # Read passphrase from stdin
                str(file_path)
            ]

            # Pass passphrase via stdin
            result = subprocess.run(cmd, input=self.gpg_passphrase, text=True,
                                  capture_output=True, env=env)

            if result.returncode != 0:
                raise RuntimeError(f"Failed to sign {file_path}: {result.stderr}")

            # Verify signature
            verify_cmd = ['gpg', '--verify', f'{file_path}.asc', str(file_path)]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)

            if verify_result.returncode != 0:
                print(f"Warning: Signature verification failed for {file_path}")
            else:
                print(f"✓ Signed and verified: {file_path}")

    def cleanup_gpg_key(self, dry_run: bool = False):
        """Remove imported GPG key if needed."""
        if dry_run or not self.gpg_key_imported:
            return

        # Optionally remove the key (commented out by default)
        # Uncomment if you want to clean up the key after use
        # cmd = ['gpg', '--delete-secret-key', '--batch', '--yes', self.gpg_key_id]
        # subprocess.run(cmd, capture_output=True)
        print(f"GPG key {self.gpg_key_id} remains imported (not cleaned up)")

