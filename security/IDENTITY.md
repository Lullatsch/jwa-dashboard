# Git identity safeguards

Status 2026-11-24: local safeguards and GitHub workflow deployed and validated.
Mandatory GitHub enforcement remains pending administrative configuration.
The operator authorized and completed the historical identity migration on
2026-11-24, retaining all content. Further history rewrites and credential
removal/revocation require separate explicit authorization.

## Policy and scope

Both raw author and raw committer must match an exact name/email pair:

- Human: `Lullatsch <106073825+Lullatsch@users.noreply.github.com>`.
- Reviewed existing collector: `jwa-data-bot <jwa-data-bot@users.noreply.github.com>`.
  Verified against the live private collector workflow and published commit metadata.
  This is Git metadata, not proof of an authenticated GitHub bot account.

`security/identities.json` freezes existing history at
`56864ca5ea5fff51d8ee1da739881eeec522464e`, the mapped clean equivalent of the original
pre-guard baseline after the authorized migration. Only that commit and its
ancestors are exempt; all were individually verified to use approved identities.
The migration is complete. Never advance this baseline to accommodate a new
invalid commit or merge the old private-account history back into main. Mailmap and replacement objects cannot mask
identities. Tags pointing to commits are checked; tagger identity and blob/tree
tags are outside the commit-identity policy.

## Installation and recovery

Requires Git, Python 3 and Bash. From a new complete checkout:

```sh
bash security/install.sh /path/to/existing/Lullatsch-private-key
python3 security/test_identity_guard.py
```

The installer sets repository-local `user.name`, `user.email`,
`user.useConfigOnly=true`, `core.hooksPath=.githooks`, an empty credential helper,
and a pinned SSH command. It ignores user SSH configuration and agents, selects
only the supplied key, and uses batch mode. On this host the existing key is
`/home/julian/.ssh/lullatsch`; GitHub's SSH greeting confirms `Lullatsch`.
This account-specific key is also used by other Lullatsch repositories; no key
was created, copied, revoked or re-registered. This is equivalent repository-local
account isolation rather than a new repository-exclusive SSH key/host alias.
The remote is `git@github.com:Lullatsch/jwa-dashboard.git` with no push URL.
Keep HTTPS/token remotes out of this checkout.

Before changing important config, make a restricted ignored backup. Verified
host backup: `HomeServer/secrets/jwa-dashboard-identity-20261124/` contains the
original Git config and a verified full Git bundle. Recover local configuration
by restoring that config; inspect current work and remote refs before restoring
anything else. Ordinary rollback is a new revert commit; never force-push.

The common configuration covers linked worktrees. When `extensions.worktreeConfig`
is enabled, rerun installation in each worktree so its worktree config cannot
retain an override; ensure each checked-out branch contains the hooks.
New clones must install hooks separately. The audited checkout has one worktree.

## Local checks and their limits

Pre-commit checks Git's effective prospective author and committer, including
`--author`, amend/reuse, command-line configuration and environment overrides.
It allows humans only. Bots commit in disposable CI checkouts without the human
hook, then enable `.githooks` before pushing. Pre-push checks the exact approved
human/bot pairs in every commit reachable from the proposed tips but not the
actual destination's advertised heads/tags or historical baseline. It queries
the real destination rather than trusting stale tracking refs and fetches missing
advertised objects without changing tracking refs. Empty remotes, new branches,
multi-ref pushes and deletions are supported. Shallow history and lookup failures
fail closed. Large histories may require more time for the remote comparison.

Local hooks and config can be deliberately bypassed (`--no-verify`, `-c
core.hooksPath=/dev/null`, altered scripts, `GIT_SSH_COMMAND`, etc.).
`user.useConfigOnly` alone does not stop environment overrides; the hooks provide
that check. None of these measures cryptographically proves who wrote a commit.

## GitHub check and required protection

`.github/workflows/identity-check.yml` runs `identity-check` for PRs and branch/tag
pushes with only `contents: read`, no stored checkout credentials and no secrets.
It checks both raw fields for the PR base-to-head or push before-to-after range,
excluding the fixed historical baseline. PRs execute the checker from the base
commit and fetch head objects without checking out or running PR code. No path
filters omit data-only changes. Integration tests also run on GitHub, including
an invalid commit made after bypassing local hooks, without publishing invalid
fixtures to GitHub. Push checks are detection after upload, not pre-receive hooks.

Audited ruleset `20586074`, `Protect public dashboard main`, is active and has
`deletion`, `non_fast_forward`, and `update` restrictions, but no required status
check. The real main push explicitly reported a bypass of its update restriction
for the authenticated Lullatsch account. Public API responses do not disclose its bypass list. Available connector
tools cannot change rulesets or inspect deploy-key permissions/secrets; SSH push
access does not grant REST administration. A repo administrator must inspect the
full bypass list and add the successful `identity-check` context from GitHub
Actions as a required check for `main`. Protect changes to this workflow, hooks
and policy via CODEOWNERS review (the file alone does not enforce reviews).

**Do not blindly require the check for the existing direct-push collector:** a
fresh bot commit has no successful check until after upload. This would stop
scheduled publishing. Choose and validate one deployment design first:

1. Prefer moving the publisher to a branch/PR flow with suitably scoped API
   authentication; require the check for merges, enforce for admins, avoid
   bypass actors, and prevent unreviewed policy/workflow changes.
2. Preserve direct bot publishing only with an explicitly documented deploy-key
   bypass and the bot's local pre-push guard. Such a bypass also bypasses required
   checks and cannot give universal server-side prevention. Its post-push check
   detects failures but cannot undo uploaded commits.

Repository owners can change rules; admins and configured bypass roles/apps/keys
may evade rules. GitHub-created merge/squash commits can carry GitHub committer
metadata: do not silently allow `web-flow` or `github-actions[bot]`; use an
approved local merge/commit identity until separately reviewed. No server-rule
change is claimed as active until inspected and tested with the publisher.

## Automation and credential audit

| Producer | Push authentication | Author / committer | Safeguard / evidence |
| --- | --- | --- | --- |
| This checkout, human scripts/tools | Existing pinned SSH key, verified GitHub account Lullatsch | Exact approved human pair | Local config, human pre-commit and pre-push |
| Private `Lullatsch/jwaclient` scheduled/manual `publish-public-dashboard.yml` | `PUBLIC_DASHBOARD_DEPLOY_KEY`, documented dashboard-only deploy key; actual GitHub key permissions not visible here | Explicit exact jwa-data-bot pair | Reviewed live main workflow; publisher hardening described below |
| Collector's private version-state push | Its repository GITHUB_TOKEN (GitHub Actions installation identity), not the dashboard deploy key | jwa-data-bot pair | Separate private-repo write; never pushes dashboard with this token |
| Host cron/systemd | No dashboard push found | N/A | Julian has no crontab; root has no active jobs; system/user timers and custom units inspected |
| Docker/Compose and self-hosted runner | No local dashboard publisher found | N/A | Active container inventory and runner mounts inspected; runner belongs to JulianWinterOrg and has no dashboard bind mount; unrelated runner not changed |
| Shell/Python client and simulator code | No Git push found in dashboard render/export paths | N/A | Sources and host scripts searched; rendering does not commit or push |

System config file absent; global config has private Julian identity and remains
unchanged for other repositories. No includes/includeIf, worktree overrides,
URL rewrites, credential helpers or HTTP auth headers found for the target.
No Git author/committer/config/SSH command overrides in this session; the SSH
agent socket is present but disabled by the pinned command. No standard Git
credential stores or gh hosts file exist for this user. No secret values were
printed or removed. Remote Actions secrets cannot be read back; verify the
actual deploy key and any other hosts/CI integrations in GitHub administration.
This audit cannot rule out unconnected machines or undisclosed external CI.

Publisher hardening: explicitly set both author and committer environment pairs,
set `user.useConfigOnly`, and enable dashboard `.githooks` after the bot commit
and before pushing. This preserves the bot exception without installing the
human pre-commit policy in CI. The private collector hardening is deployed on main through `b431564`. Its public
checkout now uses `fetch-depth: 0` so the baseline and commit graph are available.

## Validation

Run `python3 security/test_identity_guard.py`. Nineteen disposable-repository
integration tests passed locally on 2026-11-24: approved human commit/push,
private identity rejection, wrong email, explicit author and committer override,
invalid push after hook bypass, invalid committer-only push, bot push,
CI push/PR rejection and human/bot acceptance, new/deleted branches, initial
push, annotated tag, multiple refs, missing pre-rewrite CI tips and rejection of
merged private history. The production baseline contains only approved identities. SSH greeting confirmed Lullatsch with agent and
user SSH config disabled. No invalid test commit is sent to GitHub.

Official references:
- https://git-scm.com/docs/githooks
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository


### Deployment evidence

- Dashboard implementation: `aba2c008`, normal push to main with exact human pair.
- GitHub run https://github.com/Lullatsch/jwa-dashboard/actions/runs/45341298081
  succeeded, including raw commit validation and all 16 integration tests.
- Collector main: `49ac909` plus `b431564` (complete history needed by checker).
- The exact collector public-artifact shell step was exercised against a local
  bare remote with intentionally hostile inherited author/committer variables:
  it pinned the exact bot pair and pushed successfully with the guard enabled.
  An initial fixture lacked a tracking upstream and failed before push; correcting
  the fixture to match an Actions branch checkout made the test pass. No remote
  data collection or scheduled production publisher run was triggered.
- Ruleset enforcement and inspection of actual deploy-key scopes remain manual
  admin gates; the current result is PARTIAL for universal server-side prevention.

### Concrete administrative setup

`security/github-ruleset-main.json` is a deliberately **disabled** additional
ruleset payload, preserving the existing ruleset and requiring the observed
GitHub Actions app ID `15368` for `identity-check`, with no bypass actors.
An administrator can create it through the GitHub rulesets API, inspect the
result, then activate it only after validating the publishing path. See
https://docs.github.com/en/rest/repos/rules . No admin token is stored here.

Another way to retain SSH-only authentication while requiring checks is to push
the exact candidate commit to a staging branch, wait for that commit's check to
succeed, then fast-forward main to the same SHA. This needs a publisher change
and validation of deploy-key branch permissions, concurrency and failure
handling before enabling the ruleset. It is not deployed by this change.


## Completed historical attribution migration — 2026-11-24

The operator authorized reattributing the four legacy human commits to Lullatsch,
keeping every content change. An isolated raw-object rewrite preserved all 349
historical trees, commit messages, timestamps, remaining headers and parent
order/topology; exactly four author and four committer pairs changed. This
necessarily changed 104 commit hashes. The final historical root tree matched
before/after exactly; `data/`, `docs/`, and `public_assets/` also remained identical
after the additional policy/runbook commit. No bot identity was changed.

A separate restricted full-history backup and old/new mapping are kept only in
HomeServer's ignored `secrets/jwa-dashboard-history-20261124/`. No old-history
backup branch/tag is published. Main publication uses an explicit expected-old-SHA
`--force-with-lease` via the pinned Lullatsch SSH identity. If concurrent data
publishing advances main, the lease must fail and the new commits be inspected.

The guard's baseline is the mapped clean historical baseline, not the old DAG.
CI handles a missing old push tip by validating the complete reachable graph
beyond this baseline. A fresh clone must pass without access to old objects.

### Existing checkout recovery

Prefer a fresh clone and run `bash security/install.sh` to install local guards.
Do not pull/merge/rebase old public history into the migrated branch. Before
replacing an existing checkout, preserve any uncommitted work and unpublished
commits outside that checkout; port needed changes as patches with approved
identities. An old clone can retain legacy objects locally even after main moves.
The host's clean managed dashboard checkout is refreshed to the new main.
The hosted data publisher uses a fresh complete checkout each job.

GitHub contributor statistics may take approximately 24 hours to refresh after
a rewrite. If the private account remains in the contributor display after that,
contact GitHub Support. Old commit URLs, caches, and external clones can retain
old objects: this change removes the private attribution from reachable public
main history, not every previously distributed copy. Official cache guidance:
https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors
