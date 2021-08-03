#!/bin/sh

set -euo pipefail

set -x

GH_PAGES_FOLDER="$(pwd)/../gh-pages"
git worktree add "$GH_PAGES_FOLDER" gh-pages
ls -l "$1"
helm repo index --merge "$GH_PAGES_FOLDER/index.yaml" "$1"
(cd "$GH_PAGES_FOLDER" && {
    git add index.yaml
    git commit --message "Update index"
    git push
})
