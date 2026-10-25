"""Generate a color-preserving BQ79616-Q1 PAP0064F STEP model with CadQuery.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

Package dimensions are transcribed from Texas Instruments drawing PAP0064F
in the BQ7961X-Q1 data sheet (SLUSE81F): 10 mm nominal body, 12 mm nominal
lead span, 0.5 mm lead pitch, 1.2 mm maximum height, and a 5.3 mm to 6.5 mm
exposed pad. The model uses nominal dimensions within those limits and places
the terminal seating plane at Z = 0 for direct use by the KiCad footprint.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import cadquery as cq


DATASHEET = "https://www.ti.com/lit/gpn/bq79616-q1"
BODY_SIZE = 10.0
BODY_BOTTOM = 0.15
BODY_HEIGHT = 1.00
LEAD_PITCH = 0.50
LEAD_WIDTH = 0.22
EXPOSED_PAD_SIZE = 5.90

BLACK_EPOXY = cq.Color(0.025, 0.025, 0.025)
TERMINAL_METAL = cq.Color(0.76, 0.78, 0.80)


def make_body() -> cq.Workplane:
    """Return the molded package body with a recessed pin-one identifier."""
    body = (
        cq.Workplane("XY")
        .box(BODY_SIZE, BODY_SIZE, BODY_HEIGHT, centered=(True, True, False))
        .edges("|Z")
        .fillet(0.18)
        .translate((0, 0, BODY_BOTTOM))
    )
    pin_one_dimple = (
        cq.Workplane("XY", origin=(-4.15, -4.15, BODY_BOTTOM + BODY_HEIGHT - 0.04))
        .circle(0.32)
        .extrude(0.08)
    )
    return body.cut(pin_one_dimple)


def make_right_lead(offset: float) -> cq.Workplane:
    """Create one gull-wing lead on the package's right side."""
    profile = [
        (4.72, 0.46),
        (5.00, 0.46),
        (5.28, 0.12),
        (6.00, 0.12),
        (6.00, 0.00),
        (5.18, 0.00),
        (4.86, 0.34),
        (4.72, 0.34),
    ]
    return (
        cq.Workplane("XZ", origin=(0, offset, 0))
        .polyline(profile)
        .close()
        .extrude(LEAD_WIDTH / 2, both=True)
    )


def make_assembly() -> cq.Assembly:
    """Build the black-body package, all 64 leads, and exposed pad 65."""
    assembly = cq.Assembly(name="BQ79616-Q1_PAP0064F")
    assembly.add(make_body(), name="black_epoxy_body", color=BLACK_EPOXY)

    positions = [-3.75 + index * LEAD_PITCH for index in range(16)]

    for pin_number, target_y in enumerate(positions, 1):
        lead = make_right_lead(-target_y).rotate((0, 0, 0), (0, 0, 1), 180)
        assembly.add(lead, name=f"lead_{pin_number:02d}", color=TERMINAL_METAL)

    for pin_number, target_x in zip(range(17, 33), positions):
        lead = make_right_lead(-target_x).rotate((0, 0, 0), (0, 0, 1), 90)
        assembly.add(lead, name=f"lead_{pin_number:02d}", color=TERMINAL_METAL)

    for pin_number, target_y in zip(range(33, 49), reversed(positions)):
        assembly.add(
            make_right_lead(target_y),
            name=f"lead_{pin_number:02d}",
            color=TERMINAL_METAL,
        )

    for pin_number, target_x in zip(range(49, 65), reversed(positions)):
        lead = make_right_lead(target_x).rotate((0, 0, 0), (0, 0, 1), -90)
        assembly.add(lead, name=f"lead_{pin_number:02d}", color=TERMINAL_METAL)

    exposed_pad = (
        cq.Workplane("XY")
        .box(EXPOSED_PAD_SIZE, EXPOSED_PAD_SIZE, 0.08, centered=(True, True, False))
    )
    assembly.add(exposed_pad, name="exposed_pad_65", color=TERMINAL_METAL)
    return assembly


def export_step(output: Path) -> None:
    """Export a color-preserving AP214 STEP assembly."""
    output.parent.mkdir(parents=True, exist_ok=True)
    make_assembly().export(str(output), exportType="STEP", mode="default")
    content = output.read_text(encoding="utf-8")
    description = (
        "BQ79616-Q1 PAP0064F generated with CadQuery; "
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
        r"FILE_NAME('BQ79616-Q1 PAP0064F','\1',('Gerhard Malberg'),('CadQuery / Open CASCADE')",
        content,
        count=1,
    )
    output.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    default_output = (
        Path(__file__).resolve().parents[1]
        / "custom_3dmodels.3dshapes"
        / "BQ79616-Q1.step"
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
