import sys
import traceback

from release.utils.artifactory import Artifactory
from release.utils.release import ReleaseRequest

if __name__ == "__main__":


    try:
        rr = ReleaseRequest('SonarSource', 'sonar-dotnet-autoscan', '46191')
        artifactory = Artifactory('AKCp8kqCB2PoMKVWDHKGogwciqFmRHwCEUHUEPzYj4NLXByDJSMn2LUjyFFhYNWkYZaAieQTb')
        buildinfo = artifactory.receive_build_info(rr)

        artifactory.promote(rr, buildinfo)
    except Exception as e:
        print(f"::error releasability did not complete correctly. " + str(e))
        print(traceback.format_exc())
        print('DAVID')
        raise e
