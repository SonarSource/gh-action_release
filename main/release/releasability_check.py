import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from release.utils.github import GitHub
from release.utils.releasability import Releasability
from release.utils.release import releasability_checks


def main():
    github = GitHub()
    release_request = github.get_release_request()
    releasability_checks(
        github,
        Releasability(env_type="Dev", release_request=release_request),
        release_request,
    )


if __name__ == "__main__":
    main()
