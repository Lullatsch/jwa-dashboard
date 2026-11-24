"""Integration tests use disposable repositories; never push fixtures to GitHub."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
HUMAN = ('Lullatsch', '106073825+Lullatsch@users.noreply.github.com')
BOT = ('jwa-data-bot', 'jwa-data-bot@users.noreply.github.com')
BAD = ('JulianWinter1124', 'JulianWinter1124@web.de')
ZERO = '0' * 40


class GuardTests(unittest.TestCase):
    def cmd(self, *args, ok=True, env=None, input=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        e.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
        e.update(env or {})
        p = subprocess.run(args, cwd=self.repo, env=e, input=input,
                           text=True, capture_output=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout)
        return p.stdout.strip()

    def git(self, *args, **kw):
        return self.cmd('git', *args, **kw)

    def identity(self, who):
        self.git('config', 'user.name', who[0])
        self.git('config', 'user.email', who[1])

    def make_commit(self, verify=True, env=None):
        return self.git('commit', '--allow-empty', '-m', 'fixture',
                        *([] if verify else ['--no-verify']), env=env)

    def head(self):
        return self.git('rev-parse', 'HEAD')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.identity(BAD)
        self.make_commit(False)
        self.base = self.head()
        shutil.copytree(SOURCE / 'security', self.repo / 'security')
        shutil.copytree(SOURCE / '.githooks', self.repo / '.githooks')
        policy = json.loads((self.repo / 'security/identities.json').read_text())
        policy['historical_tip'] = self.base
        (self.repo / 'security/identities.json').write_text(json.dumps(policy))
        self.git('config', 'core.hooksPath', '.githooks')
        self.remote = str(Path(self.temp.name) / 'remote.git')
        self.git('init', '--bare', self.remote)
        self.git('remote', 'add', 'origin', self.remote)
        self.git('push', 'origin', 'main')  # Grandfathered historical identity.
        self.identity(HUMAN)

    def test_human_commit_and_normal_push(self):
        self.make_commit()
        self.git('push', 'origin', 'main')

    def test_private_commit_blocked(self):
        self.identity(BAD)
        self.git('commit', '--allow-empty', '-m', 'bad', ok=False)

    def test_wrong_email_blocked(self):
        self.identity(('Lullatsch', 'wrong@example.org'))
        self.git('commit', '--allow-empty', '-m', 'bad', ok=False)

    def test_author_override_blocked(self):
        self.git('commit', '--allow-empty', '--author=JulianWinter1124 <x@y>', '-m', 'bad', ok=False)

    def test_committer_environment_override_blocked(self):
        self.git('commit', '--allow-empty', '-m', 'bad', ok=False,
                 env={'GIT_COMMITTER_NAME': BAD[0], 'GIT_COMMITTER_EMAIL': BAD[1]})

    def test_bad_push_blocked_after_skipping_hook(self):
        self.identity(BAD)
        self.make_commit(False)
        self.git('push', 'origin', 'main', ok=False)

    def test_bad_committer_only_push_blocked(self):
        self.make_commit(False, env={'GIT_COMMITTER_NAME': BAD[0], 'GIT_COMMITTER_EMAIL': BAD[1]})
        self.git('push', 'origin', 'main', ok=False)

    def test_bot_push(self):
        # CI has no human pre-commit hook; it invokes the same pre-push checker.
        self.identity(BOT)
        self.make_commit(False)
        self.git('push', 'origin', 'main')

    def ci(self, event, ok):
        path = self.repo / 'event.json'
        path.write_text(json.dumps(event))
        self.cmd('python3', 'security/identity_guard.py', 'ci', ok=ok,
                 env={'GITHUB_EVENT_PATH': str(path)})

    def test_ci_rejects_hook_bypass_for_push_and_pr(self):
        self.identity(BAD)
        self.make_commit(False)
        self.ci({'before': self.base, 'after': self.head()}, False)
        self.ci({'pull_request': {'base': {'sha': self.base}, 'head': {'sha': self.head()}}}, False)

    def test_ci_accepts_human_and_bot(self):
        self.make_commit()
        self.ci({'before': self.base, 'after': self.head()}, True)
        self.identity(BOT)
        self.make_commit(False)
        self.ci({'before': self.base, 'after': self.head()}, True)

    def test_new_branch_and_deletion(self):
        self.make_commit()
        self.git('push', 'origin', 'HEAD:refs/heads/new')
        self.git('push', 'origin', ':refs/heads/new')

    def test_bad_new_branch_blocked(self):
        self.identity(BAD)
        self.make_commit(False)
        self.git('push', 'origin', 'HEAD:refs/heads/new', ok=False)

    def test_initial_push_checks_new_commits(self):
        empty = str(Path(self.temp.name) / 'empty.git')
        self.git('init', '--bare', empty)
        self.identity(BAD)
        self.make_commit(False)
        self.git('push', empty, 'main', ok=False)

    def test_ci_new_and_deleted_branch(self):
        self.make_commit()
        self.ci({'before': ZERO, 'after': self.head()}, True)
        self.ci({'before': self.head(), 'after': ZERO}, True)

    def test_bad_annotated_tag_blocked(self):
        self.identity(BAD)
        self.make_commit(False)
        self.git('tag', '-a', 'bad', '-m', 'bad')
        self.git('push', 'origin', 'refs/tags/bad', ok=False)

    def test_multiple_refs_cannot_hide_bad_branch(self):
        self.make_commit()
        self.git('branch', 'good')
        self.identity(BAD)
        self.make_commit(False)
        self.git('push', 'origin', 'good', 'main', ok=False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
