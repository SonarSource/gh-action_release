import os
import requests

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
attach_to_github_release = None
run_rules_cov = None


def get_release_info(release_request, version):
    url = f"{githup_api_url}/repos/{release_request.org}/{release_request.project}/releases"
    headers = {'Authorization': f"token {github_token}"}
    r = requests.get(url, headers=headers)
    releases = r.json()
    for release in releases:
        if not isinstance(release, str) and release.get('tag_name') == version:
            return release
    print(f"::error No release info found for tag '{version}'.\nReleases: {releases}")
    return None


def get_release_info(repo: str, version):
    url = f"{githup_api_url}/repos/{repo}/releases"
    headers = {'Authorization': f"token {github_token}"}
    r = requests.get(url, headers=headers)
    releases = r.json()
    for release in releases:
        if not isinstance(release, str) and release.get('tag_name') == version:
            return release
    print(f"::error No release info found for tag '{version}'.\nReleases: {releases}")
    return None


def attach_asset_to_github_release(release_info, file_path, filename):
    files = {'upload_file': open(file_path, 'rb')}
    upload_url = release_info.get('upload_url').replace('{?name,label}', f"?name={filename}")
    print(upload_url)
    headers = {'Authorization': f"token {github_token}"}
    r = requests.post(upload_url, files=files, headers=headers)
    return r

def revoke_release(repo, version):
    release_info = get_release_info(repo, version)
    if not release_info or not release_info.get('id'):
        return None
    url = f"{githup_api_url}/repos/{repo}/releases/{release_info.get('id')}"
    headers = {'Authorization': f"token {github_token}"}
    payload = {'draft': True, 'tag_name': version}
    r = requests.patch(url, json=payload, headers=headers)
    # delete tag
    url = f"{githup_api_url}/repos/{repo}/git/refs/tags/{version}"
    requests.delete(url, headers=headers)
    return r.json()
