from release.utils.release import revoke_release, publish_all_artifacts_to_binaries, set_output, releasability_checks
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.burgr import Burgr
from release.utils.github import GitHub
from release.utils.slack import notify_slack
from release.vars import burgrx_url, burgrx_user, burgrx_password, artifactory_access_token, binaries_bucket_name


def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    print(f"::error Aborting release")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    set_output("release", f"{rr.project}:{rr.buildnumber} revoked")


def main():
    github = GitHub()
    release_request = github.get_release_request()

    burgr = Burgr(burgrx_url, burgrx_user, burgrx_password, release_request=release_request)
    releasability_checks(github, burgr, release_request)

    artifactory = Artifactory(artifactory_access_token)
    buildinfo = artifactory.receive_build_info(release_request)
    binaries = None
    try:
        artifactory.promote(release_request, buildinfo)
        set_output("promote", 'done')  # There is no value to do it expect to not break existing workflows

        if github.is_publish_to_binaries():
            binaries = Binaries(binaries_bucket_name)
            publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo)
            set_output("publish_to_binaries", "done")  # There is no value to do it expect to not break existing workflows

        burgr.notify('passed')
        notify_slack(f"Successfully released {release_request.project}:{release_request.version}")
    except Exception as e:
        notify_slack(f"Released {release_request.project}:{release_request.version} failed")
        abort_release(github, artifactory, binaries, release_request)
        raise e


if __name__ == "__main__":
    main()
