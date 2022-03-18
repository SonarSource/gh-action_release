
List of checkpoint to verify/do before merging a PR.

**Dev checklist:**

* [ ] Functional validation
* [ ] Test depending on the change (Maven Central sync, publication, ...) on Public and private projects

**Reviewer checklist:**

* [ ] Code review
* [ ] Functional validation
* [ ] Check commits are clean

**Check if major version upgrade is needed:**

If one of those changes is checked, this requires an update of the major version:

* [ ] Introducing a new mandatory secret for a workflow
* [ ] Introducing a new mandatory input for the action without default value
* [ ] Removing a secret from a reusable workflow

In case of new major version:
* [ ] Update the version (version must be the branch) of the local GitHub action in the reusable workflows
* [ ] Update [README.md](README.md) with the new version
* [ ] Explain the change that needs to be done to the caller workflows in the release note

[Limitations on reuasable workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows#limitations)
