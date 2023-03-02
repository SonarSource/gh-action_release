from release.utils.burgr import Burgr
from release.utils.github import GitHub
from release.utils.release import releasability_checks
from release.vars import burgrx_url, burgrx_user, burgrx_password


def do_releasability_checks():
    github = GitHub()
    release_request = github.get_release_request()
    releasability_checks(github, Burgr(burgrx_url, burgrx_user, burgrx_password, release_request), release_request)


if __name__ == "__main__":
    do_releasability_checks()
