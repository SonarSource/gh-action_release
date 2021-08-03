#!/bin/sh

set -euo pipefail

GH_PAGES_FOLDER="$(pwd)/../gh-pages"
git worktree add "$GH_PAGES_FOLDER" gh-pages
helm index --merge "$GH_PAGES_FOLDER/index.ymal" "$1"
(cd $GH_PAGES_FOLDER && {
    git add index.ymal
    git commit --message "Update index"
    git push
})
