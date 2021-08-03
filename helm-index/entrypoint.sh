#!/bin/sh

set -euo pipefail

set -x

GH_PAGES_FOLDER="$(pwd)/../gh-pages"
git worktree add "$GH_PAGES_FOLDER" gh-pages
cp -r "$1/" "$GH_PAGES_FOLDER/"
(cd "$GH_PAGES_FOLDER" && {
    helm repo index --merge index.yaml .
    git add index.yaml
    git commit --message "Update index"
    git push
})
