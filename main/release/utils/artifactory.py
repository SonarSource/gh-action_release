import json
import requests
import tempfile

from dryable import Dryable
from release.utils.buildinfo import BuildInfo

SBOM_EXTENSIONS = ('.json', '.xml')


class Artifactory:
    url = 'https://repox.jfrog.io/repox'
    access_token = None
    headers = {'content-type': 'application/json'}

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers['Authorization'] = "Bearer "+access_token

    @Dryable(logging_msg='{function}()')
    def receive_build_info(self, release_request):
        url = f"{self.url}/api/build/{release_request.project}/{release_request.buildnumber}"
        r = requests.get(url, headers=self.headers)
        buildinfo = r.json()
        if r.status_code == 200:
            return BuildInfo(buildinfo)
        else:
            print(r.status_code)
            print(r.content)
            raise Exception('unknown build')

    @Dryable(logging_msg='{function}()')
    def promote(self, release_request, buildinfo, revoke=False):
        status = 'released'
        try:
            # We compute the source and target repositories using metadata from the Artifactory
            # This is the normal case where promotion was done by JFrog integration such as CLI, Rest API or AzureDevOps
            sourcerepo, targetrepo = buildinfo.get_source_and_target_repos(revoke)
            url = f"{self.url}/api/build/promote/{release_request.project}/{release_request.buildnumber}"
            if revoke:
                status = "it-passed"
            json_payload = {
                "status": f"{status}",
                "sourceRepo": f"{sourcerepo}",
                "targetRepo": f"{targetrepo}"
            }
            print(f"Promoting {release_request.project}/{release_request.buildnumber} with {json_payload}")
            r = requests.post(url, data=json.dumps(json_payload), headers=self.headers)
        except KeyError:
            # The promotion was not done by a JFrog integration (the homemade user plugin multipromote was used instead)
            # This is used by sonar-enterprise and slang-enterprise where OSS and private artifacts need to be promoted
            # In this case, the release status does not have the key 'repository' set and the source and target repositories are hardcoded
            if revoke:
                status = "it-passed"
                moreparams = {
                    'src1': 'sonarsource-private-releases',
                    'target1': 'sonarsource-private-builds',
                    'src2': 'sonarsource-public-releases',
                    'target2': 'sonarsource-public-builds',
                }
            else:
                moreparams = {
                    'src1': 'sonarsource-private-builds',
                    'target1': 'sonarsource-private-releases',
                    'src2': 'sonarsource-public-builds',
                    'target2': 'sonarsource-public-releases',
                }
            params = {
                'buildName': release_request.project,
                'buildNumber': release_request.buildnumber,
                'status': status
            }
            params.update(moreparams)

            print(f"Promoting to multiple repositories with {params}")

            url = f"{self.url}/api/plugins/execute/multiRepoPromote?params=" + ";".join(
                "{!s}={!s}".format(key, val) for (key, val) in params.items())
            r = requests.get(url, headers=self.headers)
            print(f"Successful promotion. Response: {r.text}")
        if not r.ok:
            raise Exception(f"Promotion failed with code: {r.status_code}. Response was: {r.text}")

    def download(self, artifactory_repo, gid, aid, qual, ext, version, checksums=None):
        gid_path = gid.replace(".", "/")
        if gid.startswith('com.'):
            artifactory_repo = artifactory_repo.replace('public', 'private')
        artifactory = self.url + "/" + artifactory_repo

        filename = f"{aid}-{version}.{ext}"
        if qual:
            filename = f"{aid}-{version}-{qual}.{ext}"
        url = f"{artifactory}/{gid_path}/{aid}/{version}/{filename}"
        print(url)
        # for sonarqube rename artifact from sonar-application.zip to sonarqube.zip
        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
        temp_file = f"{tempfile.gettempdir()}/{filename}"
        r = requests.get(url, headers=self.headers, stream=True)
        r.raise_for_status()
        with open(temp_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f'downloaded {temp_file}')

        for checksum in (checksums or []):
            checksum_url = f"{url}.{checksum}"
            checksum_file = f"{temp_file}.{checksum}"
            r = requests.get(checksum_url, headers=self.headers)
            r.raise_for_status()
            with open(checksum_file, 'wb') as f:
                f.write(r.content)
            print(f'downloaded {checksum_file}')
        return temp_file

    def _resolve_repo(self, artifactory_repo, gid):
        if gid.startswith('com.'):
            return artifactory_repo.replace('public', 'private')
        return artifactory_repo

    @staticmethod
    def _is_sbom_candidate(name):
        """An SBOM file is a '.json'/'.xml' mentioning 'cyclonedx'/'sbom'.

        Checksum/signature siblings (.asc/.md5/.sha1/.sha256) are excluded implicitly since they
        never end with an SBOM extension.
        """
        lowered = name.lower()
        return lowered.endswith(SBOM_EXTENSIONS) and ('cyclonedx' in lowered or 'sbom' in lowered)

    @staticmethod
    def _sbom_sort_key(name):
        # Artifactory listing order is not guaranteed; pick deterministically: prefer an explicit
        # CycloneDX file, then .json over .xml, then by name.
        lowered = name.lower()
        return (0 if 'cyclonedx' in lowered else 1, 0 if lowered.endswith('.json') else 1, lowered)

    def find_sbom_filename(self, artifactory_repo, gid, aid, version):
        """Discover the SBOM file co-located with the artifact in its Repox version folder.

        SBOM naming is not uniform across products (e.g. '-cyclonedx.json',
        '.sbom-cyclonedx.json', 'SonarLint.visualstudio.sbom-<v>-<year>.json'), so we match any
        '.json'/'.xml' child whose name mentions 'cyclonedx' or 'sbom' and is not a checksum or
        signature. Returns the filename or None when no SBOM is published for this artifact.
        """
        repo = self._resolve_repo(artifactory_repo, gid)
        gid_path = gid.replace(".", "/")
        url = f"{self.url}/api/storage/{repo}/{gid_path}/{aid}/{version}"
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            print(f"could not list {url} (status {r.status_code}) to find an SBOM")
            return None
        names = (c.get('uri', '').lstrip('/') for c in r.json().get('children', []) if not c.get('folder'))
        candidates = sorted((n for n in names if self._is_sbom_candidate(n)), key=self._sbom_sort_key)
        if not candidates:
            return None
        if len(candidates) > 1:
            print(f"multiple SBOM candidates found, using {candidates[0]} (from {candidates})")
        return candidates[0]

    def download_named(self, artifactory_repo, gid, aid, version, filename, checksums=None,
                       optional_checksums=None):
        """Download an exact filename (and its checksum siblings) from a Repox version folder.

        Unlike download(), the filename is provided verbatim (used for SBOMs whose name does not
        follow the {aid}-{version}.{ext} pattern). Checksums in `optional_checksums` are fetched
        best-effort and skipped when absent (e.g. a product that does not sign its SBOM).
        """
        repo = self._resolve_repo(artifactory_repo, gid)
        gid_path = gid.replace(".", "/")
        url = f"{self.url}/{repo}/{gid_path}/{aid}/{version}/{filename}"
        print(url)
        temp_file = f"{tempfile.gettempdir()}/{filename}"
        r = requests.get(url, headers=self.headers, stream=True)
        r.raise_for_status()
        with open(temp_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f'downloaded {temp_file}')

        for checksum in (checksums or []):
            r = requests.get(f"{url}.{checksum}", headers=self.headers)
            r.raise_for_status()
            with open(f"{temp_file}.{checksum}", 'wb') as f:
                f.write(r.content)
            print(f'downloaded {temp_file}.{checksum}')

        downloaded_optional = []
        for checksum in (optional_checksums or []):
            r = requests.get(f"{url}.{checksum}", headers=self.headers)
            if r.status_code != 200:
                print(f"skipping optional {filename}.{checksum} (status {r.status_code})")
                continue
            with open(f"{temp_file}.{checksum}", 'wb') as f:
                f.write(r.content)
            print(f'downloaded {temp_file}.{checksum}')
            downloaded_optional.append(checksum)
        return temp_file, downloaded_optional
