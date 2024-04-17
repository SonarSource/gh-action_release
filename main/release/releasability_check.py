from release.releasability.releasability import Releasability
from release.utils.github import GitHub
from release.utils.release import releasability_checks

def do_releasability_checks():
    github = GitHub()
    release_request = github.get_release_request()
    releasability = Releasability(release_request)
    releasability_checks(github, releasability, release_request)


if __name__ == "__main__":
    do_releasability_checks()
