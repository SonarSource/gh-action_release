from release.steps import ReleaseRequest


class VersionHelper:

    @staticmethod
    def as_standardized_version(release_request: ReleaseRequest) -> str:
        version = release_request.version
        # SLVSCODE-specific
        if release_request.project == 'sonarlint-vscode':
            version = version.split('+')[0]

        return version
