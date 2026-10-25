"""Generate a color-preserving BQ79600-Q1 PW0016A STEP model with CadQuery.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

Package dimensions are transcribed from Texas Instruments drawing PW0016A
in the BQ79600-Q1 data sheet (SLUSDS1A): 5.0 mm nominal body length,
4.4 mm nominal body width, 6.4 mm nominal lead span, 0.65 mm lead pitch,
and 1.2 mm maximum height. The model uses nominal dimensions within those
limits and places the terminal seating plane at Z = 0 for direct use by the
matching KiCad footprint.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import cadquery as cq


DATASHEET = "https://www.ti.com/lit/gpn/bq79600-q1"
BODY_WIDTH = 4.40
BODY_LENGTH = 5.00
BODY_BOTTOM = 0.15
BODY_HEIGHT = 0.90
LEAD_SPAN = 6.40
LEAD_PITCH = 0.65
LEAD_WIDTH = 0.22

# A charcoal resin makes the package edges and drafted sides easier to read
# than a near-zero black while retaining the intended dark molded appearance.
CHARCOAL_EPOXY = cq.Color(0.12, 0.13, 0.14)
TERMINAL_METAL = cq.Color(0.76, 0.78, 0.80)


def make_body() -> cq.Workplane:
    """Return the drafted molded body with a recessed pin-one identifier."""
    body = (
        cq.Workplane("XY")
        .workplane(offset=BODY_BOTTOM)
        .rect(BODY_WIDTH, BODY_LENGTH)
        .workplane(offset=BODY_HEIGHT)
        .rect(BODY_WIDTH - 0.24, BODY_LENGTH - 0.24)
        .loft(combine=True)
    )
    pin_one_dimple = (
        cq.Workplane(
            "XY",
            # KiCad presents the STEP model's Y axis opposite to the footprint
            # editor's Y axis. Positive model Y therefore places the dimple
            # beside footprint pin 1 rather than pin 8.
            origin=(-1.55, 1.85, BODY_BOTTOM + BODY_HEIGHT - 0.04),
        )
        .circle(0.25)
        .extrude(0.08)
    )
    return body.cut(pin_one_dimple)


def make_right_lead(offset: float) -> cq.Workplane:
    """Create one gull-wing lead on the package's right side."""
    body_edge = BODY_WIDTH / 2
    toe = LEAD_SPAN / 2
    profile = [
        (body_edge - 0.15, 0.55),
        (body_edge + 0.08, 0.55),
        (body_edge + 0.38, 0.12),
        (toe, 0.12),
        (toe, 0.00),
        (body_edge + 0.31, 0.00),
        (body_edge, 0.40),
        (body_edge - 0.15, 0.40),
    ]
    return (
        cq.Workplane("XZ", origin=(0, offset, 0))
        .polyline(profile)
        .close()
        .extrude(LEAD_WIDTH / 2, both=True)
    )


def make_assembly() -> cq.Assembly:
    """Build the charcoal package body and all 16 metallic leads."""
    assembly = cq.Assembly(name="BQ79600-Q1_PW0016A")
    assembly.add(make_body(), name="charcoal_epoxy_body", color=CHARCOAL_EPOXY)

    positions = [-2.275 + index * LEAD_PITCH for index in range(8)]

    for pin_number, target_y in enumerate(positions, 1):
        lead = make_right_lead(-target_y).rotate((0, 0, 0), (0, 0, 1), 180)
        assembly.add(lead, name=f"lead_{pin_number:02d}", color=TERMINAL_METAL)

    for pin_number, target_y in zip(range(9, 17), reversed(positions)):
        assembly.add(
            make_right_lead(target_y),
            name=f"lead_{pin_number:02d}",
            color=TERMINAL_METAL,
        )

    return assembly


def export_step(output: Path) -> None:
    """Export a color-preserving AP214 STEP assembly."""
    output.parent.mkdir(parents=True, exist_ok=True)
    make_assembly().export(str(output), exportType="STEP", mode="default")
    content = output.read_text(encoding="utf-8")
    description = (
        "BQ79600-Q1 PW0016A generated with CadQuery; "
        f"Source: {DATASHEET}; Copyright 2026 Gerhard Malberg; "
        "SPDX-License-Identifier: CERN-OHL-P-2.0"
    )
    content = content.replace(
        "FILE_DESCRIPTION(('Open CASCADE Model'),'2;1');",
        f"FILE_DESCRIPTION(('{description}'),'2;1');",
        1,
    )
    content = re.sub(
        r"FILE_NAME\('Open CASCADE Shape Model','([^']*)',\('Author'\),\(\s*'Open CASCADE'\)",
        r"FILE_NAME('BQ79600-Q1 PW0016A','\1',('Gerhard Malberg'),('CadQuery / Open CASCADE')",
        content,
        count=1,
    )
    output.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    default_output = (
        Path(__file__).resolve().parents[1]
        / "custom_3dmodels.3dshapes"
        / "BQ79600-Q1.step"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"STEP output path (default: {default_output})",
    )
    args = parser.parse_args()
    export_step(args.output.resolve())
    print(f"Generated {args.output.resolve()}")
    print(f"Dimensional source: {DATASHEET}")


if __name__ == "__main__":
    main()
