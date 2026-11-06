#!/usr/bin/env bash
# Push screenshots to an orphan branch `pr-assets/<branch>` and print their
# raw.githubusercontent.com URLs for embedding in a PR body. Uses git plumbing
# with a temporary index, so the current worktree, index and checkout are
# never touched.
#
# Usage:  push_pr_assets.sh <branch> <file.png> [file.png ...]
set -euo pipefail

[ $# -ge 2 ] || { echo "usage: $0 <branch> <file> [file...]" >&2; exit 2; }
branch="$1"; shift

repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
ref="refs/heads/pr-assets/${branch}"

idx="$(mktemp -u)"
trap 'rm -f "$idx"' EXIT
export GIT_INDEX_FILE="$idx"
git read-tree --empty
for f in "$@"; do
    blob="$(git hash-object -w "$f")"
    git update-index --add --cacheinfo "100644,${blob},$(basename "$f")"
done
tree="$(git write-tree)"
commit="$(git commit-tree "$tree" -m "pr-assets: ${branch} screenshots")"
unset GIT_INDEX_FILE

git push -q --force origin "${commit}:${ref}"

for f in "$@"; do
    echo "https://raw.githubusercontent.com/${repo}/pr-assets/${branch}/$(basename "$f")"
done
