import fnmatch
import os
import shutil
import subprocess

import requests

GH_ACTION_REPO_DIR = os.path.join(os.environ.get("GITHUB_WORKSPACE", ""), "gh-action_release")
PUBLISH_SCRIPT = os.path.join(GH_ACTION_REPO_DIR, "maven-central-sync", "maven-central-publish.sh")

# md5/sha1 are required by Central Portal for every artifact; asc (GPG signature) is fetched
# best-effort so a genuinely-missing signature surfaces as Central's own validation failure
# (the same failure the real, later upload would hit) rather than an error from this script.
CENTRAL_REQUIRED_CHECKSUMS = ["md5", "sha1"]
CENTRAL_OPTIONAL_CHECKSUMS = ["asc"]

# Public artifacts (org.sonarsource.*, the only ones ever synced to Central) always live under
# this repo pre-promotion. Used only as a fallback for multiRepoPromote builds (sonar-enterprise /
# slang-enterprise), which have no single buildInfo.statuses[0].repository to derive it from -
# see the matching fallback in Artifactory.promote().
MULTI_REPO_PROMOTE_PUBLIC_SOURCE = "sonarsource-public-builds"

PUBLIC_GROUP_ID_PREFIX = "org.sonarsource"


def download_artifacts_for_central(artifactory, buildinfo, dest_dir, exclusions="-"):
    """Download this build's to-publish artifacts (pre-promotion) into dest_dir, Maven-repo-shaped.

    Only org.sonarsource.* artifacts are considered — com.sonarsource.* are commercial/private and
    must never reach a Central bundle. exclusions is one or more ";"-separated glob patterns
    matched against each artifact id and its Maven path; "-" means none (e.g. sonar-enterprise
    excludes its shaded scanner-engine jar).
    """
    allartifacts = buildinfo.get_artifacts_to_publish()
    if not allartifacts:
        return
    try:
        sourcerepo, _ = buildinfo.get_source_and_target_repos(False)
    except KeyError:
        # Homemade multipromote plugin (sonar-enterprise / slang-enterprise): no single
        # statuses[0].repository. Central only ever gets org.sonarsource.* (public) artifacts.
        sourcerepo = MULTI_REPO_PROMOTE_PUBLIC_SOURCE
    version = buildinfo.get_version()
    patterns = [p for p in exclusions.split(";") if p and p != "-"] if exclusions else []
    for artifact_to_publish in allartifacts.split(","):
        gid, aid, ext = artifact_to_publish.split(":")[:3]
        if not gid.startswith(PUBLIC_GROUP_ID_PREFIX):
            print(f"skipping non-public artifact {artifact_to_publish} for Maven Central")
            continue
        artifact_path = f"{gid.replace('.', '/')}/{aid}/{version}/{aid}-{version}.{ext}"
        if any(fnmatch.fnmatchcase(aid, p) or fnmatch.fnmatchcase(artifact_path, p) for p in patterns):
            continue
        qual = artifact_to_publish.split(":")[3] if artifact_to_publish.count(":") > 2 else ""
        _download_optional(artifactory, dest_dir, sourcerepo, gid, aid, qual, ext, version)
        _download_optional(artifactory, dest_dir, sourcerepo, gid, aid, "", "pom", version)
        if ext == "jar":
            _download_optional(artifactory, dest_dir, sourcerepo, gid, aid, "sources", "jar", version)
            _download_optional(artifactory, dest_dir, sourcerepo, gid, aid, "javadoc", "jar", version)


def _download_optional(artifactory, dest_dir, repo, gid, aid, qual, ext, version):
    """Download one file, its required checksums, and its signature into dest_dir's Maven layout.

    Missing companion files (sources/javadoc/pom for a module that genuinely lacks them) are
    skipped so Central's own validation is the judge of whether the bundle is complete. Once
    download_named() succeeds, the main file and every CENTRAL_REQUIRED_CHECKSUMS sibling are
    guaranteed to exist (it raises otherwise); downloaded_optional lists exactly which optional
    siblings (e.g. .asc) actually came back, so there is nothing left to probe on disk.
    """
    filename = f"{aid}-{version}-{qual}.{ext}" if qual else f"{aid}-{version}.{ext}"
    try:
        downloaded, downloaded_optional = artifactory.download_named(
            repo, gid, aid, version, filename,
            checksums=CENTRAL_REQUIRED_CHECKSUMS, optional_checksums=CENTRAL_OPTIONAL_CHECKSUMS)
    except requests.HTTPError as e:
        missing_main_file = e.response is not None and e.response.url is not None and e.response.url.endswith(filename)
        if e.response is not None and e.response.status_code == 404 and missing_main_file:
            return
        raise
    target_dir = os.path.join(dest_dir, gid.replace(".", "/"), aid, version)
    os.makedirs(target_dir, exist_ok=True)
    suffixes = [""] + [f".{c}" for c in CENTRAL_REQUIRED_CHECKSUMS] + [f".{c}" for c in downloaded_optional]
    for suffix in suffixes:
        src = downloaded + suffix
        shutil.move(src, os.path.join(target_dir, os.path.basename(src)))


def validate_before_promote(local_repo_dir, central_url, central_token, deployment_name):
    """Upload local_repo_dir as a USER_MANAGED deployment and wait for Central to validate it.

    Returns the deployment id, left pending-publish for finalize() to publish later. Raises on
    failure, or if a successful validation's deployment id could not be recovered.
    """
    env = {**os.environ, "CENTRAL_TOKEN": central_token, "DEPLOYMENT_NAME": deployment_name}
    result = subprocess.run(
        [PUBLISH_SCRIPT, local_repo_dir, central_url, "validate", ""],
        env=env, check=False,
    )
    deployment_id = _read_deployment_id()
    if result.returncode != 0:
        raise RuntimeError(f"Maven Central validation failed for {deployment_name} (deployment {deployment_id})")
    if not deployment_id:
        raise RuntimeError(
            f"Maven Central validation for {deployment_name} succeeded but no deployment id was "
            "reported; refusing to promote since the deployment could not be published later")
    return deployment_id


def finalize(deployment_id, central_url, central_token):
    """Publish an already-validated deployment (no re-upload)."""
    env = {**os.environ, "CENTRAL_TOKEN": central_token}
    result = subprocess.run(
        [PUBLISH_SCRIPT, "", central_url, "finalize", deployment_id],
        env=env, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Maven Central publish failed for deployment {deployment_id}")


def _read_deployment_id():
    """Last "deployment-id=..." line written to GITHUB_OUTPUT (it's append-only across the job)."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output or not os.path.exists(github_output):
        return None
    deployment_id = None
    with open(github_output) as f:
        for line in f:
            if line.startswith("deployment-id="):
                deployment_id = line.strip().split("=", 1)[1]
    return deployment_id
