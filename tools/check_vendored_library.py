#!/usr/bin/env python3
"""Identify which upstream commit a vendored copy of this library came from.

Git names every object by the SHA-1 of its contents, so a tree copied unmodified
between two repositories has the same tree hash in both. That hash is the link
back to upstream: find the commit whose tree matches and the provenance follows,
without a version field, a manifest, or anything recorded at copy time.

    python check_vendored_library.py --upstream ../../../kicad-libraries

Exit codes:

    0  identical to an upstream commit, and that commit is the newest
    1  identical to an upstream commit, but upstream has moved on
    2  locally modified - no upstream tree matches
    3  the upstream path is missing or is not a git repository

Run it from anywhere inside a consuming project; the vendored tree is located
relative to this file. Run it inside kicad-libraries itself and it compares the
working tree against HEAD.

Copyright (C) 2021-2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY_ROOT = os.path.dirname(HERE)


def git(repo, *args, check=True):
    r = subprocess.run(['git', '-C', repo, *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        return None
    return r.stdout.strip()


def is_repo(path):
    return bool(path) and os.path.isdir(path) and \
        git(path, 'rev-parse', '--git-dir') is not None


def vendored_tree(root):
    """Tree hash of the library as it sits on disk, tracked or not.

    Uses the containing repository's index when the library is vendored inside
    one, so .gitattributes normalisation is applied the same way upstream
    applies it. Falls back to hashing the working tree directly.
    """
    owner = git(root, 'rev-parse', '--show-toplevel')
    if owner:
        rel = os.path.relpath(root, owner).replace(os.sep, '/')
        if rel == '.':
            return git(owner, 'rev-parse', 'HEAD^{tree}'), owner, rel
        return git(owner, 'rev-parse', 'HEAD:' + rel), owner, rel
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', required=True,
                    help='path to a clone of the kicad-libraries repository')
    ap.add_argument('--vendored', default=LIBRARY_ROOT,
                    help='the vendored library to check (default: this file\'s library)')
    args = ap.parse_args()

    up = os.path.abspath(os.path.expanduser(args.upstream))
    if not is_repo(up):
        print('not a git repository: %s' % up, file=sys.stderr)
        print('clone kicad-libraries and pass its path with --upstream', file=sys.stderr)
        return 3

    tree, owner, rel = vendored_tree(os.path.abspath(args.vendored))
    if tree is None:
        print('could not read the vendored tree at %s' % args.vendored, file=sys.stderr)
        print('it must sit inside a git repository and be committed', file=sys.stderr)
        return 3

    print('vendored : %s' % rel)
    print('tree     : %s' % tree)

    # The tree hash above describes the committed state. Uncommitted edits to
    # the vendored copy would otherwise be invisible here and report CURRENT,
    # so check the working tree separately and say so.
    dirty = git(owner, 'status', '--porcelain', '--', rel, check=False)
    if dirty:
        print()
        print('LOCALLY MODIFIED - the vendored copy has uncommitted changes:')
        for line in dirty.splitlines()[:40]:
            print('  %s' % line.strip())
        print()
        print('Make library changes upstream and re-vendor, rather than editing')
        print('the copy in place.')
        return 2

    log = git(up, 'log', '--all', '--format=%H %T') or ''
    match = next((line.split()[0] for line in log.splitlines()
                  if line.split()[1:2] == [tree]), None)

    if match is None:
        print()
        print('LOCALLY MODIFIED - no upstream commit has this tree.')
        head = git(up, 'rev-parse', 'HEAD^{tree}')
        if head:
            diff = git(up, 'diff', '--name-only', tree, head, check=False)
            if diff:
                print('differs from upstream HEAD in:')
                for line in diff.splitlines()[:40]:
                    print('  %s' % line)
        print()
        print('Either the copy was edited in place, or a file was saved through')
        print('the KiCad editor, which rewrites UUIDs and the generator string.')
        print('Make library changes upstream and re-vendor.')
        return 2

    subject = git(up, 'log', '-1', '--format=%h %ad %s', '--date=short', match)
    revision = git(up, 'rev-list', '--count', match)
    behind = git(up, 'rev-list', '--count', '%s..HEAD' % match) or '0'

    print('upstream : %s' % subject)
    print('revision : %s (commits up to that point)' % revision)

    if behind == '0':
        print()
        print('CURRENT - matches the newest upstream commit.')
        return 0

    print()
    print('BEHIND by %s commit(s):' % behind)
    newer = git(up, 'log', '--format=  %h %ad %s', '--date=short',
                '%s..HEAD' % match) or ''
    for line in newer.splitlines()[:20]:
        print(line)
    print()
    print('Re-vendor by copying %s over the vendored copy.' % up)
    print('A differing hash says the content changed, not whether it matters -')
    print('read the commit subjects above.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
