"""Utilities for retrieving secrets from Vault."""

import json
import urllib.error
import urllib.request
from typing import Optional


class VaultClient:
    """Client for retrieving secrets from Vault."""

    def __init__(self, vault_url: str, vault_token: str):
        self.vault_url = vault_url.rstrip('/')
        self.vault_token = vault_token
        self.headers = {
            'X-Vault-Token': vault_token,
            'Content-Type': 'application/json'
        }

    def read_secret(self, path: str, key: Optional[str] = None) -> str:
        """Read a secret from Vault.

        Args:
            path: Vault path (e.g., 'development/kv/data/ossrh' for KV v2, or 'development/artifactory/token/...' for other engines)
            key: Key name within the secret (e.g., 'token'). If None, returns the entire secret as JSON.

        Returns:
            Secret value as string, or entire secret as JSON string if key is None
        """
        url = f"{self.vault_url}/v1/{path}"

        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))

                # Handle KV v2 format (has /data/ in path)
                if '/kv/data/' in path or '/data/' in path:
                    # KV v2 format: { "data": { "data": { "key": "value" } } }
                    if 'data' in data and 'data' in data['data']:
                        secret_data = data['data']['data']
                    elif 'data' in data:
                        secret_data = data['data']
                    else:
                        secret_data = data
                else:
                    # Other secret engines (e.g., artifactory): { "data": { "key": "value" } }
                    if 'data' in data:
                        secret_data = data['data']
                    else:
                        secret_data = data

                if key:
                    value = secret_data.get(key, '')
                    if value is None:
                        return ''
                    return str(value)
                else:
                    return json.dumps(secret_data)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Failed to read secret from Vault path '{path}': HTTP {e.code} - {error_body}")

    def read_artifactory_token(self, repo_owner_name: Optional[str] = None, role_suffix: str = 'qa-deployer') -> str:
        """Read Artifactory token from Vault.

        Args:
            repo_owner_name: Repository owner name (optional, defaults to 'SonarSource-gh-action_release')
            role_suffix: Role suffix (default: 'qa-deployer')

        Returns:
            Artifactory access token
        """
        # Default to SonarSource-gh-action_release role (preserve exact case)
        if not repo_owner_name:
            repo_name_dash = 'SonarSource-gh-action_release'
        else:
            # Convert repo name to dash format
            # Handle project names like 'sonar-dummy' or 'sonar_dummy' -> 'SonarSource-sonar-dummy'
            repo_name = repo_owner_name.replace('_', '-')
            # If it doesn't start with 'SonarSource-', prepend it
            if not repo_name.startswith('SonarSource-'):
                repo_name_dash = f'SonarSource-{repo_name}'
            else:
                repo_name_dash = repo_name
        path = f"development/artifactory/token/{repo_name_dash}-{role_suffix}"
        return self.read_secret(path, 'access_token')

