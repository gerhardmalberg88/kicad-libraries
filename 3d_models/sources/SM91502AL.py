"""Generate a color-preserving Bourns SM91502AL STEP model with CadQuery.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

Package dimensions are transcribed from the Bourns SM91502AL data sheet:
7.62 mm body width, 8.89 mm nominal overall lead span, 2.54 mm pin pitch,
0.51 mm terminal width, 0.72 mm nominal terminal foot length, and 5.72 mm
maximum height. The 7.11 mm body depth follows the illustrated package
outline and the matching 7.11 mm inner-land gap. The model uses nominal
dimensions within the published envelope and places the terminal seating
plane at Z = 0 for direct use by the matching KiCad footprint.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import cadquery as cq


DATASHEET = "https://www.bourns.com/docs/product-datasheets/SM91502AL.pdf"
BODY_WIDTH = 7.62
BODY_DEPTH = 7.11
BODY_BOTTOM = 0.40
BODY_TOP = 5.60
BODY_DRAFT = 0.28
LEAD_PITCH = 2.54
LEAD_WIDTH = 0.51
LEAD_OUTER_EDGE = 8.89 / 2

BLACK_EPOXY = cq.Color(0.035, 0.035, 0.035)
TERMINAL_METAL = cq.Color(0.76, 0.78, 0.80)


def make_body() -> cq.Workplane:
    """Return the drafted molded body with a recessed pin-one identifier."""
    body = (
        cq.Workplane("XY")
        .workplane(offset=BODY_BOTTOM)
        .rect(BODY_WIDTH, BODY_DEPTH)
        .workplane(offset=BODY_TOP - BODY_BOTTOM)
        .rect(BODY_WIDTH - 2 * BODY_DRAFT, BODY_DEPTH - 2 * BODY_DRAFT)
        .loft(combine=True)
    )
    pin_one_dimple = (
        cq.Workplane("XY", origin=(-2.75, -2.45, BODY_TOP + 0.02))
        .circle(0.30)
        .extrude(-0.12)
    )
    return body.cut(pin_one_dimple)


def make_positive_y_lead(x_position: float) -> cq.Workplane:
    """Create one gull-wing terminal on the pin-one side of the package."""
    profile = [
        (3.30, 0.88),
        (3.60, 0.88),
        (3.78, 0.65),
        (3.78, 0.25),
        (3.90, 0.12),
        (LEAD_OUTER_EDGE, 0.12),
        (LEAD_OUTER_EDGE, 0.00),
        (LEAD_OUTER_EDGE - 0.72, 0.00),
        (3.60, 0.18),
        (3.60, 0.55),
        (3.30, 0.72),
    ]
    return (
        cq.Workplane("YZ", origin=(x_position, 0, 0))
        .polyline(profile)
        .close()
        .extrude(LEAD_WIDTH / 2, both=True)
    )


def make_assembly() -> cq.Assembly:
    """Build the molded body and all six separately colored terminals."""
    assembly = cq.Assembly(name="SM91502AL")
    assembly.add(make_body(), name="black_epoxy_body", color=BLACK_EPOXY)

    x_positions = (-LEAD_PITCH, 0.0, LEAD_PITCH)
    for pin_number, x_position in enumerate(x_positions, 1):
        assembly.add(
            make_positive_y_lead(x_position),
            name=f"lead_{pin_number}",
            color=TERMINAL_METAL,
        )

    for pin_number, x_position in zip((6, 5, 4), x_positions):
        negative_y_lead = make_positive_y_lead(-x_position).rotate(
            (0, 0, 0),
            (0, 0, 1),
            180,
        )
        assembly.add(
            negative_y_lead,
            name=f"lead_{pin_number}",
            color=TERMINAL_METAL,
        )
    return assembly


def export_step(output: Path) -> None:
    """Export a color-preserving AP214 STEP assembly with provenance."""
    output.parent.mkdir(parents=True, exist_ok=True)
    make_assembly().export(str(output), exportType="STEP", mode="default")
    content = output.read_text(encoding="utf-8")
    description = (
        "Bourns SM91502AL generated with CadQuery; "
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
        r"FILE_NAME('SM91502AL','\1',('Gerhard Malberg'),('CadQuery / Open CASCADE')",
        content,
        count=1,
    )
    output.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    default_output = (
        Path(__file__).resolve().parents[1]
        / "custom_3dmodels.3dshapes"
        / "SM91502AL.step"
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
