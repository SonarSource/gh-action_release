import json
import urllib
import requests
import tempfile

from release.utils.buildinfo import BuildInfo


class Artifactory:
    url = 'https://repox.jfrog.io/repox'
    api_key = None
    headers = {'content-type': 'application/json'}

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers['X-JFrog-Art-Api'] = api_key

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

    def promote(self, release_request, buildinfo, revoke=False):
        status = 'released'
        try:
            # We compute the source and target repositories using metadata from the Artifactory
            # This is the normal case where promotion was done by JFrog integration such as CLI, Rest API or AzureDevOps
            sourcerepo, targetrepo = buildinfo.get_source_and_target_repos(revoke)
            print(f"Promoting build {release_request.project}#{release_request.buildnumber} from {sourcerepo} to "
                  f"{targetrepo}")

            url = f"{self.url}/api/build/promote/{release_request.project}/{release_request.buildnumber}"
            if revoke:
                status = "it-passed"
            json_payload = {
                "status": f"{status}",
                "sourceRepo": f"{sourcerepo}",
                "targetRepo": f"{targetrepo}"
            }
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

            print(f"Promoting multi repositories: {moreparams}")

            url = f"{self.url}/api/plugins/execute/multiRepoPromote?params=" + ";".join(
                "{!s}={!s}".format(key, val) for (key, val) in params.items())
            r = requests.get(url, headers=self.headers)
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
        opener = urllib.request.build_opener()
        opener.addheaders = [('X-JFrog-Art-Api', self.api_key)]
        urllib.request.install_opener(opener)
        # for sonarqube rename artifact from sonar-application.zip to sonarqube.zip
        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
        temp_file = f"{tempfile.gettempdir()}/{filename}"
        urllib.request.urlretrieve(url, temp_file)
        print(f'downloaded {temp_file}')
        for checksum in (checksums or []):
            urllib.request.urlretrieve(f"{url}.{checksum}", f"{temp_file}.{checksum}")
            print(f'downloaded {temp_file}.{checksum}')
        return temp_file
