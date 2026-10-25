#!/usr/bin/env python3
"""Assemble one merged .kicad_sym from the single-symbol libraries here.

Optional. Nothing in this repository needs it: each symbol is its own library,
which is what gives every part its own git history. It exists for consuming
projects, which usually want the opposite - a single library of just the parts
they use, so their lib_ids stay stable no matter how this repository is
organised.

Symbol blocks are copied without a byte changed, so every symbol in the merged
file still identifies against the single-symbol library it came from:

    python tools/identify_asset.py <merged file> --upstream <this repo>

reports one line per symbol block rather than one for the file.

Select what goes in, three ways:

    --all                       every symbol in symbols/
    --symbols SYMBOL_A SYMBOL_B  named symbols
    --used-by <path>            whatever a project's schematics reference

Examples:

    # a project library holding exactly what the schematics use
    python tools/build_symbol_library.py --used-by <project-dir> \\
        --output <project-dir>/kicad-libraries/symbols/custom_symbols.kicad_sym

    # add one part to a project library that already exists
    python tools/build_symbol_library.py --symbols SYMBOL_NAME --update \\
        --output <project-dir>/kicad-libraries/symbols/custom_symbols.kicad_sym

    # fail a build when a project library has drifted from its sources
    python tools/build_symbol_library.py --used-by <project-dir> --check \\
        --output <project-dir>/kicad-libraries/symbols/custom_symbols.kicad_sym

Symbols are written in sorted order, so re-running produces the same bytes and
an unchanged library is an empty diff.

Exit codes:

    0  written, or --check found the output already correct
    1  --check found the output missing, stale, or holding extra symbols
    2  a requested symbol does not exist in symbols/
    3  a path argument is wrong

Copyright (C) 2021-2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY_ROOT = os.path.dirname(HERE)
SYMBOL_DIR = os.path.join(LIBRARY_ROOT, 'symbols')

HEADER = ('(kicad_symbol_lib\n'
          '\t(version 20231120)\n'
          '\t(generator "kicad_symbol_editor")\n'
          '\t(generator_version "9.0")\n')


def blocks_in(text):
    """Every top-level (symbol "...") block, by name, byte for byte."""
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


def available(symbol_dir):
    """symbol name -> its source file, across every library in the directory."""
    found = {}
    for path in sorted(glob.glob(os.path.join(symbol_dir, '*.kicad_sym'))):
        text = io.open(path, encoding='utf-8').read()
        for name in blocks_in(text):
            found.setdefault(name, path)
    return found


def referenced_by(paths, nickname):
    """Symbol names a project's schematics load from `nickname`.

    Returns (names, files, bad). A path that is neither a directory nor an
    existing file is reported rather than opened, so a mistyped design
    directory fails with a readable message instead of a traceback.
    """
    files, bad = [], []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, '*.kicad_sch')))
        elif os.path.isfile(p):
            files.append(p)
        else:
            bad.append(p)
    names = set()
    pattern = re.compile(r'\(lib_id "%s:([^"]*)"' % re.escape(nickname))
    for f in files:
        names |= set(pattern.findall(
            io.open(f, encoding='utf-8', errors='replace').read()))
    return names, files, bad


def assemble(names, sources):
    text = HEADER
    for name in sorted(names):
        text += blocks_in(io.open(sources[name], encoding='utf-8').read())[name] + '\n'
    return text + ')\n'


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', help='merged .kicad_sym to write')
    ap.add_argument('--symbols', nargs='+', metavar='NAME',
                    help='symbols to include')
    ap.add_argument('--all', action='store_true',
                    help='include every symbol in the symbol directory')
    ap.add_argument('--used-by', nargs='+', metavar='PATH',
                    help='include whatever these schematics (or this design '
                         'directory) reference')
    ap.add_argument('--nickname', default='custom_symbols',
                    help='library nickname --used-by looks for '
                         '(default: custom_symbols)')
    ap.add_argument('--symbol-dir', default=SYMBOL_DIR,
                    help='where the single-symbol libraries are')
    ap.add_argument('--update', action='store_true',
                    help='keep symbols already in the output and add to them')
    ap.add_argument('--check', action='store_true',
                    help='verify the output matches its sources; write nothing')
    ap.add_argument('--list', action='store_true',
                    help='list the symbols available and exit')
    args = ap.parse_args()

    if not os.path.isdir(args.symbol_dir):
        print('not a directory: %s' % args.symbol_dir, file=sys.stderr)
        return 3
    sources = available(args.symbol_dir)
    if not sources:
        print('no symbols found in %s' % args.symbol_dir, file=sys.stderr)
        return 3

    if args.list:
        print('%d symbol(s) in %s:' % (len(sources), args.symbol_dir))
        for name in sorted(sources):
            print('  %-42s %s' % (name, os.path.basename(sources[name])))
        return 0

    if not args.output:
        ap.error('--output is required unless --list is given')

    # ---- work out what goes in ---------------------------------------------
    wanted = set()
    if args.all:
        wanted |= set(sources)
    if args.symbols:
        wanted |= set(args.symbols)
    if args.used_by:
        found, scanned, bad = referenced_by(args.used_by, args.nickname)
        for p in bad:
            print('no such file or directory: %s' % p, file=sys.stderr)
        if bad or not scanned:
            if not bad:
                print('no .kicad_sch files found under %s'
                      % ', '.join(args.used_by), file=sys.stderr)
            return 3
        print('scanned %d schematic(s); %d symbol(s) referenced as %s:*'
              % (len(scanned), len(found), args.nickname))
        wanted |= found
    existing = {}
    if os.path.exists(args.output) and (args.update or args.check):
        existing = blocks_in(io.open(args.output, encoding='utf-8').read())
    if args.update:
        wanted |= set(existing)
    if not wanted:
        ap.error('nothing selected: give --all, --symbols or --used-by')

    missing = sorted(wanted - set(sources))
    if missing:
        for name in missing:
            print('not in %s: %s' % (args.symbol_dir, name), file=sys.stderr)
        return 2

    # ---- check mode --------------------------------------------------------
    if args.check:
        if not os.path.exists(args.output):
            print('MISSING  %s' % args.output)
            return 1
        want = {n: blocks_in(io.open(sources[n], encoding='utf-8').read())[n]
                for n in wanted}
        stale = sorted(n for n in want if existing.get(n) != want[n])
        extra = sorted(set(existing) - wanted)
        for name in stale:
            print('  STALE   %s%s' % (name,
                                      '' if name in existing else ' (absent)'))
        for name in extra:
            print('  EXTRA   %s (in the library but not referenced)' % name)
        if stale or extra:
            print('%s: %d stale, %d extra, of %d symbol(s)'
                  % (args.output, len(stale), len(extra), len(wanted)))
            return 1
        print('%s: %d symbol(s), all byte-identical to their sources'
              % (args.output, len(wanted)))
        return 0

    # ---- write -------------------------------------------------------------
    text = assemble(wanted, sources)
    parent = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    unchanged = os.path.exists(args.output) and \
        io.open(args.output, encoding='utf-8', newline='').read() == text
    io.open(args.output, 'w', encoding='utf-8', newline='\n').write(text)
    print('%s: %d symbol(s)%s' % (args.output, len(wanted),
                                  ' (unchanged)' if unchanged else ''))
    for name in sorted(wanted):
        print('  %-42s <- %s' % (name, os.path.basename(sources[name])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
