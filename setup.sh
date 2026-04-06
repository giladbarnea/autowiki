#!/usr/bin/env zsh -i

set -euo pipefail

repo_root="$(cd "$(dirname "$0")" && pwd)"

git -C "$repo_root" config core.hooksPath .githooks

echo "Configured git hooks path to .githooks for $repo_root"
