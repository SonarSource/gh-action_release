from dryable import Dryable
from release.steps.ReleaseRequest import ReleaseRequest


class Releasability:
    release_request: ReleaseRequest

    def __init__(self, release_request):
        self.release_request = release_request
        version = self.release_request.version
        # SLVSCODE-specific
        if self.release_request.project == 'sonarlint-vscode':
            version = version.split('+')[0]
        self.version = version

    @Dryable(logging_msg='{function}()')
    def start_releasability_checks(self):
        print(f"Starting releasability check: {self.release_request.project}#{self.version}")
