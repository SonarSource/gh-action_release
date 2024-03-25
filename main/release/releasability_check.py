from release.releasability.releasability import Releasability
from release.utils.burgr import Burgr
from release.utils.github import GitHub
from release.utils.release import releasability_checks
from release.vars import burgrx_url, burgrx_user, burgrx_password

def do_releasability_checks():
    github = GitHub()
    release_request = github.get_release_request()
    burgr = Burgr(burgrx_url, burgrx_user, burgrx_password, release_request)
    releasability = Releasability(release_request)
    releasability_checks(github, burgr, releasability, release_request)


if __name__ == "__main__":
    do_releasability_checks()
