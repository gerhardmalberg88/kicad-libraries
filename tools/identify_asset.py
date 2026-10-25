#!/usr/bin/env python3
"""Identify which commit of this library a loose asset file came from.

The whole-tree check in check_vendored_library.py answers "is this copy of the
library current". This answers the other question: somebody hands back a single
footprint, symbol or model, and you need to know where it came from and whether
it still matches.

Three methods are tried in order, cheapest first, and the report says which one
answered:

  EXACT       the file is byte-identical to a blob in this repository. Git names
              every object by the SHA-1 of its contents, so this is proof, not
              inference. Fails if the file was re-saved through the KiCad editor
              or had its line endings converted.

  EQUIVALENT  the design content matches, though the bytes do not. Compares a
              fingerprint built only from design-meaningful facts - pad numbers,
              positions, sizes, drills and layer sets; pin numbers, names and
              types - so UUID rewrites, generator strings, numeric respellings
              and KiCad format migrations do not register. Measured against the
              real KiCad 8 to 9 migration of 280 footprints: byte comparison
              matched 0, this matched all 280.

  DIVERGED    neither matched, so the file is ranked against every historical
              version of that path by diff size and the nearest one is reported
              with the differences. This is the method that tells you *what*
              changed rather than just that something did, and it is the only
              one that still answers when a part has genuinely been edited.

Usage:

    python identify_asset.py <file> [<file> ...] [--upstream <repo>]
    python identify_asset.py --manifest <manifest.tsv> [--upstream <repo>]
    python identify_asset.py <file> --show-diff

Exit codes:

    0  every file identified as EXACT or EQUIVALENT
    1  at least one file DIVERGED from the version it most resembles
    2  at least one file could not be attributed to this library at all
    3  the upstream path is missing or is not a git repository

Copyright (C) 2021-2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY_ROOT = os.path.dirname(HERE)

# Rewritten by any editor save or format migration; carry no design meaning.
VOLATILE = [
    re.compile(rb'\(uuid\s+"[^"]*"\)'),
    re.compile(rb'\(generator\s+"[^"]*"\)'),
    re.compile(rb'\(generator_version\s+"[^"]*"\)'),
    re.compile(rb'\(version\s+\d+\)'),
    re.compile(rb'\(tedit\s+[0-9A-Fa-f]+\)'),
]

TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')


def git(repo, *args, binary=False):
    r = subprocess.run(['git', '-C', repo, *args], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode('utf-8', 'replace').strip()


def is_repo(path):
    return bool(path) and os.path.isdir(path) and \
        git(path, 'rev-parse', '--git-dir') is not None


def has_commits(path):
    """A repository with no commits has nothing to identify anything against.

    Worth saying plainly: every asset would otherwise be reported as not
    existing in the library, when in fact the files are there and simply have
    not been committed.
    """
    return git(path, 'rev-parse', '--verify', 'HEAD') is not None


def blob_hash(data):
    """The name git would give this content."""
    h = hashlib.sha1()
    h.update(b'blob %d\0' % len(data))
    h.update(data)
    return h.hexdigest()


# ---------------------------------------------------------------- parsing ---
def parse(text):
    """Parse the first complete S-expression in `text`."""
    it = iter(TOKEN.findall(text))

    def build():
        out = []
        for t in it:
            if t == '(':
                out.append(build())
            elif t == ')':
                return out
            else:
                out.append(t[1:-1] if t.startswith('"') else t)
        return out

    for t in it:
        if t == '(':
            return build()
    return []


def children(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]


def number(value):
    """Normalise numeric spelling so 0, 0.0 and 0.00 compare equal."""
    try:
        return '%.6g' % float(value)
    except (TypeError, ValueError):
        return str(value)


def footprint_facts(root):
    facts = ['footprint=' + root[1]]
    for pad in children(root, 'pad'):
        at = children(pad, 'at')
        size = children(pad, 'size')
        drill = children(pad, 'drill')
        layers = children(pad, 'layers')
        facts.append('pad %s %s %s at=%s size=%s drill=%s layers=%s' % (
            pad[1], pad[2], pad[3],
            ' '.join(number(v) for v in at[0][1:]) if at else '',
            ' '.join(number(v) for v in size[0][1:]) if size else '',
            ' '.join(number(v) for v in drill[0][1:]) if drill else '',
            # a layer set is a set; KiCad 9 reordered these with no design change
            ','.join(sorted(layers[0][1:])) if layers else ''))
    for model in children(root, 'model'):
        facts.append('model ' + model[1].replace('\\', '/').split('/')[-1])
    return facts


def symbol_facts(root):
    facts = []
    for symbol in children(root, 'symbol'):
        facts.append('symbol=' + symbol[1])
        for unit in children(symbol, 'symbol'):
            for pin in children(unit, 'pin'):
                at = children(pin, 'at')
                name = children(pin, 'name')
                num = children(pin, 'number')
                facts.append('pin %s %s %s %s at=%s' % (
                    num[0][1] if num else '?',
                    name[0][1] if name else '?',
                    pin[1] if len(pin) > 1 else '',
                    pin[2] if len(pin) > 2 else '',
                    ' '.join(number(v) for v in at[0][1:]) if at else ''))
    return facts


def fingerprint(data, filename):
    """Design-meaningful facts only, canonically ordered. None if unsupported."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ('.kicad_mod', '.kicad_sym'):
        return None
    try:
        root = parse(data.decode('utf-8', 'replace'))
    except (ValueError, IndexError):
        return None
    if not root:
        return None
    try:
        facts = footprint_facts(root) if root[0] == 'footprint' else \
            symbol_facts(root) if root[0] == 'kicad_symbol_lib' else None
    except (IndexError, TypeError):
        return None
    if facts is None:
        return None
    return hashlib.sha1('\n'.join(sorted(facts)).encode()).hexdigest()


def canonical_lines(data):
    """Text with editor-volatile tokens removed, for readable diffs."""
    data = data.replace(b'\r\n', b'\n')
    for rx in VOLATILE:
        data = rx.sub(b'', data)
    data = re.sub(rb'[ \t]+', b' ', data)
    return [l for l in data.decode('utf-8', 'replace').split('\n') if l.strip()]


# ------------------------------------------------------------ upstream ------
SYM_HEADER = ('(kicad_symbol_lib\n'
              '\t(version 20231120)\n'
              '\t(generator "kicad_symbol_editor")\n'
              '\t(generator_version "9.0")\n')


def symbol_library_name(symbol_name):
    """The upstream single-symbol library file for a symbol.

    Mirrors generate_original_kicad_assets.symbol_library_name: the symbol name
    lowercased, runs of non-alphanumeric characters collapsed to "_".
    """
    return re.sub(r'[^a-z0-9]+', '_', symbol_name.lower()).strip('_')


def top_level_blocks(text):
    """Every top-level (symbol "...") block, by name, without changing a byte."""
    out = {}
    for m in re.finditer(r'^\t\(symbol "([^"]*)"', text, re.M):
        depth, quoted, esc = 0, False, False
        for i in range(m.start(), len(text)):
            c = text[i]
            if quoted:
                if esc:
                    esc = False
                elif c == '\\':
                    esc = True
                elif c == '"':
                    quoted = False
            elif c == '"':
                quoted = True
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    out[m.group(1)] = text[m.start():i + 1]
                    break
    return out


def expand(filename):
    """Yield (label, bytes, upstream-name) targets for one file.

    A project library holds imported copies of several symbols, so comparing it
    whole against upstream is meaningless - upstream has no such file. Each
    block is checked against the single-symbol library it came from instead.
    """
    data = open(filename, 'rb').read()
    base = os.path.basename(filename)
    if not base.lower().endswith('.kicad_sym'):
        return [(filename, data, base)]
    blocks = top_level_blocks(data.decode('utf-8', 'replace'))
    if len(blocks) <= 1:
        return [(filename, data, base)]
    return [
        ('%s (%s)' % (filename, name),
         (SYM_HEADER + block + '\n)\n').encode('utf-8'),
         symbol_library_name(name) + '.kicad_sym')
        for name, block in blocks.items()
    ]


def internal_name(data, filename):
    """The design's own name, used when the file was renamed after copying.

    KiCad names a footprint file after the footprint and a single-symbol
    library after the symbol, so this recovers the upstream filename even when
    whoever copied it chose a different one.
    """
    ext = os.path.splitext(filename)[1].lower()
    text = data.decode('utf-8', 'replace')
    if ext == '.kicad_mod':
        m = re.search(r'\(footprint\s+"([^"]*)"', text)
    elif ext == '.kicad_sym':
        m = re.search(r'\(symbol\s+"([^"]*)"', text)
    else:
        return None
    return m.group(1) + ext if m else None


def candidate_paths(repo, *basenames):
    """Every path in any commit whose basename matches, newest first."""
    wanted = [b for b in basenames if b]
    if not wanted:
        return []
    listing = git(repo, 'rev-list', '--objects', '--all') or ''
    seen = []
    for line in listing.splitlines():
        if ' ' not in line:
            continue
        path = line.split(' ', 1)[1]
        if path.rsplit('/', 1)[-1] in wanted and path not in seen:
            seen.append(path)
    return seen


def history(repo, paths):
    """Every (commit, content) across all paths this file has lived at.

    A directory rename puts the same asset at two paths, and plain `git log`
    stops at the rename, so every path the basename has ever had is walked and
    the results merged. Without this a file older than the last rename would be
    ranked only against versions newer than it.
    """
    out = []
    seen = set()
    for path in paths:
        last = None
        for c in (git(repo, 'log', '--all', '--format=%H', '--', path) or '').split():
            data = git(repo, 'show', '%s:%s' % (c, path), binary=True)
            if data is None or data == last:
                continue
            last = data
            key = (c, hashlib.sha1(data).hexdigest())
            if key in seen:
                continue
            seen.add(key)
            out.append((c, data))
    return out


def describe(repo, commit):
    return git(repo, 'log', '-1', '--format=%h %ad %s', '--date=short', commit)


def path_at(repo, commit, sha):
    """Where this blob sat in a given commit's tree."""
    for line in (git(repo, 'ls-tree', '-r', commit) or '').splitlines():
        meta, _, path = line.partition('\t')
        parts = meta.split()
        if len(parts) >= 3 and parts[2] == sha:
            return path
    return None


_HEAD_BLOBS = {}


def head_path_of(repo, sha):
    """Where this blob sits at HEAD, or None if HEAD no longer contains it.

    --find-object alone cannot answer this: it reports every commit that adds
    or removes the blob, and a plain directory rename does both, which would
    otherwise make an unchanged current file look superseded.
    """
    if repo not in _HEAD_BLOBS:
        table = {}
        for line in (git(repo, 'ls-tree', '-r', 'HEAD') or '').splitlines():
            meta, _, path = line.partition('\t')
            parts = meta.split()
            if len(parts) >= 3:
                table.setdefault(parts[2], path)
        _HEAD_BLOBS[repo] = table
    return _HEAD_BLOBS[repo].get(sha)


def read_manifest(path):
    """File paths from a manifest: a markdown table, or one path per line.

    The project manifest doubles as the notice a reader sees, so it is a table
    in a README rather than a machine-only file. First column, backticks and
    table pipes stripped; separator rows, headers and prose ignored.
    """
    out = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if not cells:
                continue
            cell = cells[0].strip('`').strip()
            # a symbol imported into a merged library reads "file (SymbolName)";
            # the file is what gets checked, and its blocks are expanded later
            cell = re.sub(r'\s*\([^()]*\)$', '', cell).strip()
        else:
            cell = re.split(r'\t|  +', line.split('#', 1)[0])[0].strip('` ')
        # Prose, commands and links share a line format with paths, so require
        # something that can actually be a relative path.
        if (not cell or ' ' in cell or '://' in cell or '\\' in cell
                or cell.startswith(('/', '-', '<'))
                or '/' not in cell or '.' not in cell.rsplit('/', 1)[-1]):
            continue
        if cell not in out:
            out.append(cell)
    return out


# -------------------------------------------------------------- reporting ---
def identify(repo, data, base, show_diff=False):
    """Return (status, detail_lines) for one asset's bytes."""
    named = internal_name(data, base)
    lines = []

    # 1. EXACT - byte identity, including an LF retry for files that made a
    #    round trip through a tool that rewrote the line endings.
    for label, candidate in (('', data), (' after LF normalisation',
                                          data.replace(b'\r\n', b'\n'))):
        sha = blob_hash(candidate)
        # The object existing is not enough: a loose blob can be written into
        # the database without ever being committed. Only a commit that
        # actually contains it is evidence of where the file came from.
        found = (git(repo, 'log', '--all', '--format=%H',
                     '--find-object=' + sha) or '').split()
        if not found:
            continue
        # --find-object reports commits that add *or remove* the blob, newest
        # first. The newest is where this content was superseded; the oldest is
        # where it was introduced, which is the answer to "where is this from".
        commit = found[-1]
        at_head = head_path_of(repo, sha)
        where = at_head or path_at(repo, commit, sha) \
            or (candidate_paths(repo, base, named) or ['?'])[0]
        lines.append('  blob    : %s%s' % (sha[:12], label))
        lines.append('  path    : %s' % where)
        lines.append('  commit  : %s' % describe(repo, commit))
        if at_head is None:
            lines.append('  superseded at %s - this is not the current version'
                         % describe(repo, found[0]).split()[0])
        return 'EXACT', lines

    paths = candidate_paths(repo, base, named)
    if not paths:
        lines.append('  no file named %s%s exists anywhere in this library'
                     % (base, '' if not named or named == base
                        else ' (or %s)' % named))
        return 'UNKNOWN', lines
    path = paths[0]
    versions = history(repo, paths)
    if not versions:
        lines.append('  %s has no history' % path)
        return 'UNKNOWN', lines

    # 2. EQUIVALENT - same design, different bytes. Survives editor saves and
    #    KiCad format migrations, which byte comparison does not.
    mine = fingerprint(data, base)
    if mine is not None:
        for commit, content in versions:
            if fingerprint(content, base) == mine:
                lines.append('  path    : %s' % path)
                lines.append('  commit  : %s' % describe(repo, commit))
                lines.append('  bytes differ but every pad, pin and layer set '
                             'matches; this is an editor save or a format '
                             'migration, not a design change')
                return 'EQUIVALENT', lines

    # 3. DIVERGED - rank every historical version and report what differs.
    mine_lines = canonical_lines(data)
    ranked = []
    for commit, content in versions:
        theirs = canonical_lines(content)
        delta = sum(1 for d in difflib.unified_diff(theirs, mine_lines, n=0)
                    if d[:1] in '+-' and d[:3] not in ('+++', '---'))
        ranked.append((delta, commit, theirs))
    ranked.sort(key=lambda r: r[0])
    delta, commit, theirs = ranked[0]
    lines.append('  path    : %s' % path)
    lines.append('  nearest : %s' % describe(repo, commit))
    lines.append('  differs by %d line(s) from that version' % delta)
    for other_delta, other_commit, _ in ranked[1:4]:
        lines.append('            (%s: %d lines)'
                     % (describe(repo, other_commit).split()[0], other_delta))
    if show_diff:
        for d in list(difflib.unified_diff(
                theirs, mine_lines, 'library', 'yours', n=1))[:60]:
            lines.append('  | ' + d.rstrip())
    else:
        lines.append('  re-run with --show-diff to see the differences')
    return 'DIVERGED', lines


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='asset files to identify')
    ap.add_argument('--upstream', default=LIBRARY_ROOT,
                    help='clone of kicad-libraries (default: this file\'s library)')
    ap.add_argument('--manifest',
                    help='read the file list from a manifest instead, one path '
                         'per line, "#" comments and extra columns ignored')
    ap.add_argument('--show-diff', action='store_true',
                    help='print the differences for files that diverged')
    args = ap.parse_args()

    repo = os.path.abspath(os.path.expanduser(args.upstream))
    if not is_repo(repo):
        print('not a git repository: %s' % repo, file=sys.stderr)
        print('clone kicad-libraries and pass its path with --upstream',
              file=sys.stderr)
        return 3
    if not has_commits(repo):
        print('%s has no commits yet' % repo, file=sys.stderr)
        print('identification resolves content to the commit that introduced '
              'it, so there is nothing to compare against until the library '
              'has been committed at least once.', file=sys.stderr)
        return 3

    files = list(args.files)
    if args.manifest:
        root = os.path.dirname(os.path.abspath(args.manifest))
        for rel in read_manifest(args.manifest):
            files.append(os.path.join(root, rel))
        if not files:
            print('no file paths found in %s' % args.manifest, file=sys.stderr)
            return 2
    if not files:
        ap.error('give at least one file, or --manifest')

    tally = {'EXACT': 0, 'EQUIVALENT': 0, 'DIVERGED': 0, 'UNKNOWN': 0}
    checked = 0
    for filename in files:
        if not os.path.isfile(filename):
            print('%-12s %s' % ('MISSING', filename))
            tally['UNKNOWN'] += 1
            checked += 1
            continue
        for label, data, base in expand(filename):
            status, detail = identify(repo, data, base, args.show_diff)
            tally[status] += 1
            checked += 1
            shown = label
            path, _, suffix = label.partition(' (')
            rel = os.path.relpath(path)
            if not rel.startswith('..'):
                shown = rel + (' (' + suffix if suffix else '')
            else:
                shown = os.path.basename(path) + (' (' + suffix if suffix else '')
            print('%-12s %s' % (status, shown))
            for line in detail:
                print(line)

    print()
    print('%d asset(s): %d exact, %d equivalent, %d diverged, %d unknown'
          % (checked, tally['EXACT'], tally['EQUIVALENT'],
             tally['DIVERGED'], tally['UNKNOWN']))
    if tally['UNKNOWN']:
        return 2
    if tally['DIVERGED']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
