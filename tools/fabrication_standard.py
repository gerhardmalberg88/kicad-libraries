"""Apply/check the reference-only fabrication style documented in README.md.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

This edits display properties and fabrication graphics only. It never imports
stock KiCad assets into this library. --geometry requires KiCad's Python.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
FAB_LAYERS = {"F.Fab", "B.Fab"}

# (height/width, stroke, local x, local y), in mm. Explicit package sizes
# take precedence over the conservative automatic size for a new package.
REFERENCE_STYLES = {
    "Littelfuse_470-Series_Fuse_1206": (0.65, 0.10, 0, 0),
    "Schurter_USF-1206_Fuse_3.2x1.6mm": (0.65, 0.10, 0, 0),
    "Schurter_MGA-A_Fuse_3.2x1.6mm": (0.65, 0.10, 0, 0),
    "Vishay_RCL1225_2W_3.2x6.3mm": (0.65, 0.10, 0, 0),
    "Bourns_SMBJ-Q_DO-214AA": (0.60, 0.09, 0, 0),
    "LTC3639_MSE16-12": (0.60, 0.09, 0, 0),
    "Littelfuse_SZSMFxxA_SOD-123FL": (0.40, 0.06, 0.225, 0),
    "Bourns_CDSOD323-TxxC_SOD-323_Compact": (0.25, 0.04, 0.15, 0),
    # Project-local stock footprint: retain its upstream ownership. The rule
    # below fits reference-only fabrication text inside a supplied copy.
    "D_SOD-323": (0.25, 0.04, 0.15, 0),
}


def block_end(text: str, start: int) -> int:
    depth = 0
    quoted = escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("Unclosed S-expression")


def children(text: str):
    """Yield immediate child expressions of a footprint, preserving offsets."""
    root = re.search(r'\((?:footprint|module)\s+"(?:[^"\\]|\\.)*"', text)
    if root is None:
        raise ValueError("Expected a named footprint")
    i = root.end()
    while i < len(text):
        if text[i] == "(":
            end = block_end(text, i)
            yield i, end, text[i:end]
            i = end
        elif text[i] == ")":
            break
        else:
            i += 1


def layer_of(block: str) -> str | None:
    match = re.search(r'\(layer "([^"]+)"\)', block)
    return match.group(1) if match else None


def fab_bounds(graphics: list[str]) -> tuple[float, float, float, float]:
    points = []
    for graphic in graphics:
        for match in re.finditer(r'\((?:xy|start|end) (-?[\d.]+) (-?[\d.]+)\)', graphic):
            points.append(tuple(map(float, match.groups())))
    if not points:
        raise ValueError("A fabrication body outline is required")
    return (min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points), max(y for x, y in points))


def apply_standard(text: str, name: str | None = None) -> str:
    """Return an idempotent, narrowly edited footprint without reserializing."""
    if name is None:
        name = re.search(r'\((?:footprint|module)\s+"([^"]+)"', text).group(1)
    items = list(children(text))
    edits = []
    for side in sorted(FAB_LAYERS):
        graphics = [b for a, z, b in items if b.startswith(("(fp_line", "(fp_rect", "(fp_poly")) and layer_of(b) == side]
        references = [(a, z, b) for a, z, b in items if b.startswith('(fp_text user "${REFERENCE}"') and layer_of(b) == side]
        if not graphics and not references:
            continue
        if len(references) != 1:
            raise ValueError(f"{name}: exactly one visible ${{REFERENCE}} required on {side}")
        xmin, ymin, xmax, ymax = fab_bounds(graphics)
        style_name = name.removesuffix("_MinimalSilkscreen")
        if style_name in REFERENCE_STYLES:
            size, stroke, x, y = REFERENCE_STYLES[style_name]
        else:
            x = 0.0 if xmin < 0 < xmax else (xmin + xmax) / 2
            y = 0.0 if ymin < 0 < ymax else (ymin + ymax) / 2
            width = 2 * min(x - xmin, xmax - x) - 0.30
            height = 2 * min(y - ymin, ymax - y) - 0.30
            # Conservative envelope for the KiCad stroke-font REF** placeholder
            # and a one-letter / three-digit designator. Exact geometry is
            # checked separately, including chamfers and orientation marks.
            size = math.floor(min(1.0, width / 4.7, height / 1.8) * 20 + 1e-9) / 20
            if size < 0.20:
                raise ValueError(f"{name}: needs a reviewed placement/rotation override")
            stroke = round(size * 0.15, 3)

        if name == "D_SOD-323":
            # Replace only the six central diode-symbol lines with a pin-one
            # end marker. Keep the existing package rectangle and all other
            # layers. This rule acts on a caller-supplied project copy.
            pad = next(b for a, z, b in items if b.startswith('(pad "1"'))
            pad_x = float(re.search(r'\(at (-?[\d.]+)', pad).group(1))
            marker_x = -0.6 if pad_x < 0 else 0.6
            x = 0.15 if pad_x < 0 else -0.15
            internal = []
            for a, z, b in items:
                if not b.startswith("(fp_line") or layer_of(b) != side:
                    continue
                coords = [tuple(map(float, m.groups())) for m in re.finditer(r'\((?:start|end) (-?[\d.]+) (-?[\d.]+)\)', b)]
                if len(coords) == 2 and all(xmin < px < xmax and ymin < py < ymax for px, py in coords):
                    internal.append((a, z, b))
            if internal:
                if len(internal) != 6:
                    raise ValueError(f"{name}: unexpected central fabrication symbol")
                for index, (a, z, b) in enumerate(internal):
                    replacement = ""
                    if index == 0:
                        replacement = re.sub(r'\(start [^()]+\)', f'(start {marker_x:g} {ymin:g})', b)
                        replacement = re.sub(r'\(end [^()]+\)', f'(end {marker_x:g} {ymax:g})', replacement)
                    edits.append((a, z, replacement))

        a, z, reference = references[0]
        new = re.sub(r'\(size [^()]+\)', f'(size {size:g} {size:g})', reference, count=1)
        new = re.sub(r'\(thickness [^()]+\)', f'(thickness {stroke:g})', new, count=1)
        at = re.search(r'\(at ([^()]+)\)', new)
        angle = at.group(1).split()[2] if len(at.group(1).split()) > 2 else "0"
        new = new[:at.start()] + f'(at {x:g} {y:g} {angle})' + new[at.end():]
        new = re.sub(r'\s*\(hide yes\)', '', new)
        # Older KiCad fp_text syntax carries a bare hide flag.
        new = re.sub(r'(?<=\))\s+hide(?=\s|\))', '', new)
        edits.append((a, z, new))

    for a, z, b in items:
        if not b.startswith('(property ') or layer_of(b) not in FAB_LAYERS:
            continue
        field = re.match(r'\(property "([^"]+)"', b).group(1)
        if field == "Reference" or '(hide yes)' in b:
            continue
        if '(hide no)' in b:
            new = b.replace('(hide no)', '(hide yes)', 1)
        else:
            layer = re.search(r'\(layer "[^"]+"\)', b)
            new = b[:layer.end()] + '\n\t\t(hide yes)' + b[layer.end():]
        edits.append((a, z, new))
    for a, z, replacement in sorted(edits, reverse=True):
        text = text[:a] + replacement + text[z:]
    return text


def verify_geometry(path: Path) -> list[str]:
    """Check real KiCad text envelopes against body edges on both board sides."""
    import pcbnew

    fp = pcbnew.FootprintLoad(str(path.parent.resolve()), path.stem)
    if fp is None:
        return ["KiCad could not load footprint"]
    # Flip needs a board's copper-layer mapping in KiCad 10. A detached
    # library footprint can otherwise crash inside the native API.
    board = pcbnew.BOARD()
    board.Add(fp)
    errors = []
    for flipped in (False, True):
        if flipped:
            fp.Flip(pcbnew.VECTOR2I(0, 0), False)
        layer = pcbnew.B_Fab if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Fab
        shapes = [g for g in fp.GraphicalItems() if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == layer]
        texts = [g for g in fp.GraphicalItems() if isinstance(g, pcbnew.PCB_TEXT) and g.GetLayer() == layer]
        refs = [t for t in texts if t.GetText() == '${REFERENCE}' and t.IsVisible()]
        if len(refs) != 1 or len(texts) != 1 or not shapes:
            errors.append(f"{'back' if layer == pcbnew.B_Fab else 'front'}: need body graphics and one reference as the only visible fabrication text")
            continue
        if any(field.IsVisible() for field in fp.GetFields() if field.GetLayer() == layer and field.GetName() != 'Reference'):
            errors.append("Visible fabrication value/description")
        boxes = [g.GetBoundingBox() for g in shapes]
        xmin = min(bb.GetLeft() for bb in boxes)
        xmax = max(bb.GetRight() for bb in boxes)
        ymin = min(bb.GetTop() for bb in boxes)
        ymax = max(bb.GetBottom() for bb in boxes)
        text = refs[0]
        for sample in ('REF**', 'U999', 'R999', 'D999', 'F999'):
            text.SetText(sample)  # Avoid cached ${REFERENCE} expansion.
            bb = text.GetBoundingBox()
            if not (xmin < bb.GetLeft() and bb.GetRight() < xmax and ymin < bb.GetTop() and bb.GetBottom() < ymax):
                errors.append(f"{sample}: reference extends outside body")
            rect = pcbnew.SHAPE_RECT(bb.GetPosition(), bb.GetWidth(), bb.GetHeight())
            if any(g.GetEffectiveShape().Collide(rect, 0) for g in shapes):
                errors.append(f"{sample}: reference touches outline or orientation marker")
        text.SetText('${REFERENCE}')
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path, help='Footprints or directories; defaults to this shared library')
    parser.add_argument('--apply', action='store_true', help='Write cosmetic changes (default: read-only check)')
    parser.add_argument('--geometry', action='store_true', help="Also validate text/body fit using KiCad's Python")
    args = parser.parse_args()
    paths = args.paths or [ROOT / 'footprints' / 'custom_footprints.pretty']
    files = sorted({q for p in paths for q in (p.rglob('*.kicad_mod') if p.is_dir() else [p])})
    if not files:
        parser.error('No footprints found')
    failed = changed = 0
    for path in files:
        content = path.read_text(encoding='utf-8')
        try:
            styled = apply_standard(content)
            if styled != content:
                if args.apply:
                    path.write_text(styled, encoding='utf-8', newline='\n')
                    changed += 1
                else:
                    print(f'STALE {path.name}: fabrication style differs')
                    failed += 1
            if args.geometry:
                for error in verify_geometry(path):
                    print(f'FAIL {path.name}: {error}')
                    failed += 1
        except (ValueError, StopIteration) as error:
            print(f'FAIL {path.name}: {error}')
            failed += 1
    print(f'{len(files)} footprints checked; {changed} updated; {failed} problems')
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
