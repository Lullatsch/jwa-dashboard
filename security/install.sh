#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [[ $(git remote get-url origin) != *[Ll]ullatsch/jwa-dashboard.git ]]; then
  echo 'Expected the Lullatsch/jwa-dashboard repository.' >&2
  exit 1
fi
key=${1:-/home/julian/.ssh/lullatsch}
[[ -f "$key" ]] || { echo 'Supply the Lullatsch SSH private-key path as argument.' >&2; exit 1; }
git config --local user.name Lullatsch
git config --local user.email 106073825+Lullatsch@users.noreply.github.com
git config --local user.useConfigOnly true
git config --local core.hooksPath .githooks
if [[ $(git config --get extensions.worktreeConfig || true) == true ]]; then
  git config --worktree user.name Lullatsch
  git config --worktree user.email 106073825+Lullatsch@users.noreply.github.com
  git config --worktree user.useConfigOnly true
  git config --worktree core.hooksPath .githooks
fi
# Store a shell-quoted path; ignore user SSH config and the agent for this repo.
printf -v quoted_key '%q' "$key"
git config --local core.sshCommand "ssh -F /dev/null -i $quoted_key -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes"
git config --local credential.helper ''
python3 security/identity_guard.py current
