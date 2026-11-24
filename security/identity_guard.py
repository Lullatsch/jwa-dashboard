#!/usr/bin/env python3
"""Check exact raw Git identities without mailmap; Python standard library only."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# Replacement objects must never mask the raw identities being validated.
os.environ['GIT_NO_REPLACE_OBJECTS'] = '1'

POLICY = json.loads(Path(__file__).with_name('identities.json').read_text())


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def pair(name, email, label, bots=True):
    if [name, email] not in POLICY['humans'] + (POLICY['bots'] if bots else []):
        raise ValueError(f'{label}: identity rejected: {name} <{email}>. '
                         'Use Lullatsch <106073825+Lullatsch@users.noreply.github.com>; '
                         'only the documented exact bot pair is also allowed for pushes.')


def current():
    # Git exports the prospective author, including --author/-C/amend, to hooks.
    for role in ('AUTHOR', 'COMMITTER'):
        match = re.fullmatch(r'(.*) <([^<>]*)> \d+ [+-]\d{4}', git('var', f'GIT_{role}_IDENT'))
        if not match:
            raise ValueError(f'Cannot parse effective {role} identity')
        pair(*match.groups(), role, bots=False)


def commit(oid):
    fields = git('show', '-s', '--format=%an%x00%ae%x00%cn%x00%ce', oid).split('\0')
    pair(*fields[:2], f'{oid} author')
    pair(*fields[2:], f'{oid} committer')


def revisions(heads, excludes):
    if git('rev-parse', '--is-shallow-repository') != 'false':
        raise ValueError('Shallow history cannot be checked safely; fetch full history first.')
    return git('rev-list', *heads, '--not', *excludes).splitlines() if heads else []


def baseline():
    oid = POLICY['historical_tip']
    git('cat-file', '-e', oid + '^{commit}')
    return oid


def peel(oid):
    p = subprocess.run(['git', 'rev-parse', '--verify', oid + '^{commit}'], text=True, capture_output=True)
    return p.stdout.strip() if p.returncode == 0 else None


def push(remote):
    updates = [line.split() for line in sys.stdin if line.strip()]
    if any(len(row) != 4 for row in updates):
        raise ValueError('Malformed pre-push input')
    heads = []
    for _, local, _, _ in updates:
        if set(local) != {'0'}:  # Deletions transmit no commits.
            oid = peel(local)  # Blob/tree tags carry no commit identity.
            if oid:
                heads.append(oid)
    if not heads:
        return
    # Query the actual destination, never stale local remote-tracking refs.
    tips = {baseline()}
    for line in git('ls-remote', remote).splitlines():
        oid, ref = line.split()
        if ref == 'HEAD' or ref.startswith(('refs/heads/', 'refs/tags/')):
            if subprocess.run(['git', 'cat-file', '-e', oid], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode:
                git('fetch', '--no-tags', '--no-write-fetch-head', remote, oid)
            tip = peel(oid)
            if tip:
                tips.add(tip)
    for oid in revisions(heads, sorted(tips)):
        commit(oid)


def ci(event):
    if 'pull_request' in event:
        pr = event['pull_request']
        before, after = pr['base']['sha'], pr['head']['sha']
    else:
        before, after = event['before'], event['after']
    if set(after) == {'0'}:
        return
    excludes = [baseline()]
    if set(before) != {'0'}:
        excludes.append(before)
    for oid in revisions([after], excludes):
        commit(oid)


def main():
    try:
        mode = sys.argv[1]
        if mode == 'current':
            current()
        elif mode == 'push':
            push(sys.argv[2])
        elif mode == 'ci':
            ci(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()))
        else:
            raise ValueError('Unknown mode')
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Identity guard: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
