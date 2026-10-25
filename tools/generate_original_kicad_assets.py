"""Generate the original KiCad symbols and datasheet-backed footprints.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

Covered Source under CERN-OHL-P-2.0. Dimensions and pin-function facts are
transcribed from the official manufacturer datasheets identified by URL below.
No third-party CAD geometry, UUIDs, or distributor metadata is used.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, Sequence
from uuid import NAMESPACE_URL, uuid5

from fabrication_standard import apply_standard, children, layer_of


ROOT = Path(__file__).resolve().parents[1]
FOOTPRINT_DIR = ROOT / "footprints" / "custom_footprints.pretty"
SYMBOL_DIR = ROOT / "symbols"
LICENSE = "CERN-OHL-P-2.0"
COPYRIGHT = "Copyright 2026 Gerhard Malberg"
HARWIN_GECKO_M2P_DRAWING = (
    "https://content.harwin.com/asset/9080e3a3-bca3-45d8-8fc9-6c172eec098d/"
    "DRG-02638-Technical-Drawing-Datasheet-G125-MV1XX05M2P-pdf.pdf"
)

MOLEX_MINI50_VERT_DRAWING = "https://www.molex.com/en-us/products/part-detail/348250200"
MOLEX_MINI50_SR_DRAWING = "https://www.molex.com/en-us/products/part-detail/347920041"

DATASHEET_URLS = {
    "BQ79600-Q1": "https://www.ti.com/lit/gpn/bq79600-q1",
    "BQ79606A-Q1": "https://www.ti.com/lit/gpn/bq79606a-q1",
    "BQ79616-Q1": "https://www.ti.com/lit/gpn/bq79616-q1",
    "INA286_SOIC-8": "https://www.ti.com/lit/gpn/ina286",
    "STB45N65M5_D2PAK": "https://www.st.com/resource/en/datasheet/stb45n65m5.pdf",
    "CSS2H-3920R-L200F": "https://www.bourns.com/products/resistors/details/metal-strip/css2h-3920",
    "1N6263W_SOD-123": "https://www.diodes.com/part/view/1N6263W",
    "BVN-M-R001-1.0": "https://www.isabellenhuette.com/hubfs/Files/Data-sheets/BVN.pdf",
    "WE_7460305": "https://www.we-online.com/components/products/datasheet/7460305.pdf",
    "ACS781LLRTR-100U-T": "https://www.allegromicro.com/-/media/files/datasheets/acs781-datasheet.pdf",
    "INA190A3IDDFR_DDF": "https://www.ti.com/lit/gpn/ina190",
    "PG-HSOG-8-1_INF_gsd": "https://www.infineon.com/dgdl/Infineon-IPTG054N15NM5-DataSheet-v02_00-EN.pdf?fileId=8ac78c8c81ae03fc0181d36b00225f6f",
    "IRS2186S_SOIC-8": "https://www.infineon.com/dgdl/irs2186pbf.pdf?fileId=5546d462533600a40153567716c427ed",
    "L_Wuerth_WE-PD-Typ-LS-1210": "https://www.we-online.com/components/products/datasheet/7447709271.pdf",
    "L_Wuerth_WE-PD-Robust-7332": "https://www.we-online.com/components/products/datasheet/7447789222.pdf",
    "LFXTAL016178REEL": "https://www.iqdfrequencyproducts.com/products/pn/LFXTAL016178.pdf",
    "LTC3639_MSE16-12": "https://www.analog.com/media/en/technical-documentation/data-sheets/3639fd.pdf",
    "LM2576HV_TO-263-5": "https://www.ti.com/lit/gpn/lm2576hv",
    "LM2596S_TO-263-5": "https://www.ti.com/lit/gpn/lm2596",
    "NCS213R_SC70-6": "https://www.onsemi.com/pdf/datasheet/ncs210r-d.pdf",
    "STM32L071KBTx_Custom": "https://www.st.com/resource/en/datasheet/stm32l071kb.pdf",
    "SM91502AL": "https://www.bourns.com/docs/product-datasheets/SM91502AL.pdf",
    "Harwin_Gecko_G125-MV12005M2P_2x10_P1.25mm_Vertical": HARWIN_GECKO_M2P_DRAWING,
    "Harwin_Gecko_G125-MV10605M2P_2x03_P1.25mm_Vertical": HARWIN_GECKO_M2P_DRAWING,
    "JST_XH_B20B-XH-A_1x20_P2.50mm_Vertical": "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
    "Molex_Mini50_34825-0160_2x08_P2.00mm_Vertical": MOLEX_MINI50_VERT_DRAWING,
    "Molex_Mini50_34825-0200_2x10_P2.00mm_Vertical": MOLEX_MINI50_VERT_DRAWING,
    "Molex_Mini50_34792_1x04_P2.00mm_Vertical": MOLEX_MINI50_SR_DRAWING,
    "Harwin_Datamate_M80-5001642_2x08_P2.00mm_Vertical": "https://www.harwin.com/products/M80-5001642",
    "Harwin_Datamate_M80-5002042_2x10_P2.00mm_Vertical": "https://www.harwin.com/products/M80-5002042",
    "Harwin_Datamate_M80-5T10442MC_2x02_P2.00mm_Vertical": "https://www.harwin.com/products/M80-5T10442MC",
    "Harwin_Datamate_M80-8531642_2x08_P2.00mm_Vertical": "https://www.harwin.com/products/M80-8531642",
    "Harwin_Datamate_M80-8672022_2x10_P2.00mm_Vertical": "https://www.harwin.com/products/M80-8672022",
    "Harwin_Datamate_M80-8770222_1x02_P2.00mm_Vertical": "https://www.harwin.com/products/M80-8770222",
    "Schurter_USF-1206_Fuse_3.2x1.6mm": "https://www.schurter.com/en/datasheet/typ_USF_1206.pdf",
    "Littelfuse_SZSMFxxA_SOD-123FL": "https://www.littelfuse.com/products/overvoltage-protection/tvs-diodes/surface-mount/smf",
    "Schurter_MGA-A_Fuse_3.2x1.6mm": "https://www.schurter.com/en/datasheet/typ_MGA-A.pdf",
    "Bourns_SMBJ-Q_DO-214AA": "https://www.bourns.com/docs/product-datasheets/smbj-q.pdf",
    "Bourns_CDSOD323-TxxC_SOD-323_Compact": "https://www.bourns.com/docs/Product-Datasheets/CDSOD323-TxxC.pdf",
    "Vishay_RCL1225_2W_3.2x6.3mm": "https://www.vishay.com/docs/20046/rcle3.pdf",
    "Littelfuse_470-Series_Fuse_1206": "https://www.littelfuse.com/products/fuses-overcurrent-protection/fuses/surface-mount-fuses/thin-film-chip-fuses/470",
}


def uid(asset: str, item: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gerhard-malberg/{asset}/{item}"))


def effects(size: float = 1.0, thickness: float = 0.15) -> str:
    return f'(effects (font (size {size:g} {size:g}) (thickness {thickness:g})))'


def fp_property(asset: str, name: str, value: str, at: str, layer: str, hidden: bool = False) -> str:
    hide = "\n\t\t(hide yes)" if hidden else ""
    return (
        f'\t(property "{name}" "{value}"\n'
        f'\t\t(at {at})\n\t\t(layer "{layer}"){hide}\n'
        f'\t\t(uuid "{uid(asset, "property-" + name)}")\n\t\t{effects()}\n\t)'
    )


def fp_line(asset: str, item: str, start: tuple[float, float], end: tuple[float, float], layer: str, width: float) -> str:
    return (
        f'\t(fp_line (start {start[0]:g} {start[1]:g}) (end {end[0]:g} {end[1]:g})\n'
        f'\t\t(stroke (width {width:g}) (type solid)) (layer "{layer}")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def fp_circle(asset: str, item: str, center: tuple[float, float], radius: float, layer: str = "F.SilkS") -> str:
    return (
        f'\t(fp_circle (center {center[0]:g} {center[1]:g}) '
        f'(end {center[0] + radius:g} {center[1]:g})\n'
        f'\t\t(stroke (width 0) (type solid)) (fill solid) (layer "{layer}")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def fp_poly(asset: str, item: str, points: Sequence[tuple[float, float]], layer: str, width: float = 0.1) -> str:
    pts = " ".join(f"(xy {x:g} {y:g})" for x, y in points)
    return (
        f'\t(fp_poly (pts {pts})\n'
        f'\t\t(stroke (width {width:g}) (type default)) (fill none) (layer "{layer}")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def smd_pad(asset: str, item: str, number: str, x: float, y: float, sx: float, sy: float,
            shape: str = "roundrect", layers: str = '"F.Cu" "F.Paste" "F.Mask"',
            solder_mask_margin: float | None = None,
            solder_paste_margin: float | None = None,
            roundrect_rratio: float = 0.15) -> str:
    ratio = f"\n\t\t(roundrect_rratio {roundrect_rratio:g})" if shape == "roundrect" else ""
    mask_margin = (
        f"\n\t\t(solder_mask_margin {solder_mask_margin:g})"
        if solder_mask_margin is not None else ""
    )
    paste_margin = (
        f"\n\t\t(solder_paste_margin {solder_paste_margin:g})"
        if solder_paste_margin is not None else ""
    )
    return (
        f'\t(pad "{number}" smd {shape} (at {x:g} {y:g}) (size {sx:g} {sy:g})\n'
        f'\t\t(layers {layers}){ratio}{mask_margin}{paste_margin}\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def pth_pad(asset: str, item: str, number: str, x: float, y: float, size: float, drill: float) -> str:
    return (
        f'\t(pad "{number}" thru_hole circle (at {x:g} {y:g}) (size {size:g} {size:g}) '
        f'(drill {drill:g})\n\t\t(layers "*.Cu" "*.Mask")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def pth_pad_shaped(asset: str, item: str, number: str, x: float, y: float,
                   sx: float, sy: float, drill: float, shape: str = "oval") -> str:
    """Plated through hole with an independent pad width and height."""
    return (
        f'\t(pad "{number}" thru_hole {shape} (at {x:g} {y:g}) (size {sx:g} {sy:g}) '
        f'(drill {drill:g})\n\t\t(layers "*.Cu" "*.Mask")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def npth_pad(asset: str, item: str, x: float, y: float, diameter: float) -> str:
    """Unplated mounting hole, e.g. for a connector board-mount stud."""
    return (
        f'\t(pad "" np_thru_hole circle (at {x:g} {y:g}) '
        f'(size {diameter:g} {diameter:g}) (drill {diameter:g})\n'
        f'\t\t(layers "F&B.Cu" "*.Mask")\n'
        f'\t\t(uuid "{uid(asset, item)}"))'
    )


def rect_outline(asset: str, prefix: str, xmin: float, ymin: float, xmax: float, ymax: float,
                 layer: str, width: float) -> list[str]:
    pts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]
    return [fp_line(asset, f"{prefix}-{i}", pts[i], pts[i + 1], layer, width) for i in range(4)]


def courtyard(asset: str, xmin: float, ymin: float, xmax: float, ymax: float) -> list[str]:
    pts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]
    return [fp_line(asset, f"courtyard-{i}", pts[i], pts[i + 1], "F.CrtYd", 0.05) for i in range(4)]


def footprint(name: str, description: str, datasheet: str, graphics: Iterable[str], pads: Iterable[str],
              attr: str = "smd", model_extension: str = ".step",
              model_opacity: float | None = None, model_name: str | None = None,
              model_rotation: str = "0 0 0", model_offset: str = "0 0 0",
              reference_at: str = "0 -7 0", value_at: str = "0 7 0",
              project_library_path: str = "kicad-libraries",
              tag_name: str | None = None) -> str:
    source = datasheet or "Original generic dimensional definition"
    model_lines = [
        f'\t(model "${{KIPRJMOD}}/{project_library_path}/3d_models/custom_3dmodels.3dshapes/{model_name or name}{model_extension}"',
    ]
    if model_opacity is not None:
        model_lines.append(f'\t\t(opacity {model_opacity:.4f})')
    model_lines += [
        f'\t\t(offset (xyz {model_offset}))',
        '\t\t(scale (xyz 1 1 1))',
        f'\t\t(rotate (xyz {model_rotation}))',
        '\t)',
    ]
    parts = [
        f'(footprint "{name}"',
        '\t(version 20241229)',
        '\t(generator "pcbnew")',
        '\t(generator_version "9.0")',
        '\t(layer "F.Cu")',
        f'\t(descr "{description}")',
        f'\t(tags "{tag_name or name} original datasheet")',
        fp_property(name, "Reference", "REF**", reference_at, "F.SilkS"),
        fp_property(name, "Value", name, value_at, "F.Fab"),
        fp_property(name, "Datasheet", datasheet, "0 0 0", "F.Fab", True),
        fp_property(name, "Description", description, "0 0 0", "F.Fab", True),
        f'\t(attr {attr})',
        *graphics,
        '\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab")',
        f'\t\t(uuid "{uid(name, "fab-reference")}") {effects()})',
        *pads,
        *model_lines,
        ')',
        '',
    ]
    return apply_standard("\n".join(parts), name)


def body_fab(asset: str, half_x: float, half_y: float, chamfer: float = 0.5) -> str:
    return fp_poly(
        asset,
        "fab-body",
        [(-half_x, -half_y), (half_x, -half_y), (half_x, half_y),
         (-half_x + chamfer, half_y), (-half_x, half_y - chamfer)],
        "F.Fab",
    )


def generate_footprints() -> dict[str, str]:
    generated: dict[str, str] = {}

    # Würth 7460305 is intrinsically an eight-pin press-fit terminal. The
    # datasheet explicitly states that reflow is not applicable, so it is the
    # sole plated-through-hole exception in this generated set.
    name = "WE_7460305"
    g = [body_fab(name, 4.5, 4.5)]
    g += [
        fp_line(name, "silk-left", (-4.5, -1.8), (-4.5, 1.8), "F.SilkS", 0.2),
        fp_line(name, "silk-right", (4.5, -1.8), (4.5, 1.8), "F.SilkS", 0.2),
        fp_line(name, "silk-top", (-1.8, -2.0), (1.8, -2.0), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom", (-1.8, 2.0), (1.8, 2.0), "F.SilkS", 0.2),
        *courtyard(name, -5.3, -5.3, 5.3, 5.3),
    ]
    pads = [
        pth_pad(name, f"pressfit-{row}-{col}", "1", x, y, 2.4, 1.475)
        for row, y in enumerate((-3.81, 3.81))
        for col, x in enumerate((-3.81, -1.27, 1.27, 3.81))
    ]
    generated[name] = footprint(
        name,
        "Wurth 7460305 REDCUBE M5 press-fit terminal; eight plated holes are one electrical terminal",
        DATASHEET_URLS[name],
        g,
        pads,
        "through_hole",
    )

    name = "INA190A3IDDFR_DDF"
    g = [body_fab(name, 0.8, 1.45, 0.25)]
    g += [
        fp_line(name, "silk-top", (-0.75, -1.45), (0.75, -1.45), "F.SilkS", 0.15),
        fp_line(name, "silk-bottom", (-0.75, 1.45), (0.75, 1.45), "F.SilkS", 0.15),
        fp_circle(name, "pin1", (-1.95, -1.45), 0.18),
        *courtyard(name, -2.15, -1.75, 2.15, 1.75),
    ]
    pads = []
    ys = (-0.975, -0.325, 0.325, 0.975)
    for i, y in enumerate(ys, 1):
        pads.append(smd_pad(name, f"pad-{i}", str(i), -1.3, y, 1.05, 0.45))
    for i, y in zip(range(5, 9), reversed(ys)):
        pads.append(smd_pad(name, f"pad-{i}", str(i), 1.3, y, 1.05, 0.45))
    generated[name] = footprint(
        name,
        "Texas Instruments INA190 DDF 8-pin thin SOT-23, manufacturer land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
        model_rotation="0 0 180",
        reference_at="0 -2.5 0",
    )

    name = "PG-HSOG-8-1_INF_gsd"
    g = [body_fab(name, 5.95, 5.05, 0.6), fp_circle(name, "pin1", (-6.35, -4.95), 0.2)]
    g += courtyard(name, -6.75, -5.3, 6.9, 5.3)
    pads = []
    for index, y in enumerate((-4.2, -3.0, -1.8, -0.6, 0.6, 1.8, 3.0, 4.2)):
        pad_number = "1" if index == 0 else "2"
        pads.append(smd_pad(name, f"pad-{index + 1}", pad_number, -5.0, y, 2.8, 0.9))
    pads.append(smd_pad(name, "drain-copper", "3", 2.6255, 0, 8.0, 9.7, "rect", '"F.Cu" "F.Mask"'))
    for col, x in enumerate((0.9, 3.3125, 5.725)):
        for row, y in enumerate((-3.2, 0.0, 3.2)):
            pads.append(smd_pad(name, f"drain-paste-{col}-{row}", "", x, y, 1.7, 2.4, "rect", '"F.Paste"'))
    generated[name] = footprint(
        name,
        "Infineon IPTG054N15NM5 PG-HSOG-8/TOLL package, split-paste drain land",
        DATASHEET_URLS[name],
        g,
        pads,
        model_name="PG-HSOG-8-1_INF",
    )

    name = "IRS2186S_SOIC-8"
    g = [body_fab(name, 1.95, 2.45, 0.4)]
    g += [
        fp_line(name, "silk-left", (-1.3, -2.45), (-1.3, 2.45), "F.SilkS", 0.15),
        fp_line(name, "silk-right", (1.3, -2.45), (1.3, 2.45), "F.SilkS", 0.15),
        fp_circle(name, "pin1", (-2.4, -2.65), 0.18),
        *courtyard(name, -3.5, -2.85, 3.5, 2.85),
    ]
    ys = (-1.905, -0.635, 0.635, 1.905)
    pads = [smd_pad(name, f"pad-{i}", str(i), -2.34, y, 1.78, 0.72) for i, y in enumerate(ys, 1)]
    pads += [
        smd_pad(name, f"pad-{i}", str(i), 2.342 if i == 7 else 2.34, y, 1.78, 0.72)
        for i, y in zip(range(5, 9), reversed(ys))
    ]
    generated[name] = footprint(
        name,
        "Infineon IRS2186S 8-lead SOIC, manufacturer 0.72 x 1.78 mm land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
        model_rotation="0 0 180",
        reference_at="0 -3.5 0",
        value_at="0 4 0",
    )

    name = "LFXTAL016178REEL"
    g = [body_fab(name, 3.95, 1.9, 0.35)]
    g += [
        fp_line(name, "silk-left", (-4.05, -0.4), (-4.05, 0.4), "F.SilkS", 0.15),
        fp_line(name, "silk-right", (4.05, -0.4), (4.05, 0.4), "F.SilkS", 0.15),
        fp_circle(name, "pin1", (-3.75, 2.75), 0.18),
        *courtyard(name, -4.35, -2.8, 4.35, 2.8),
    ]
    pads = [
        smd_pad(name, "pad-1", "1", -2.75, 1.6, 1.3, 1.9),
        smd_pad(name, "pad-2", "2", 2.75, 1.6, 1.3, 1.9),
        smd_pad(name, "pad-3", "3", 2.75, -1.6, 1.3, 1.9),
        smd_pad(name, "pad-4", "4", -2.75, -1.6, 1.3, 1.9),
    ]
    generated[name] = footprint(
        name,
        "IQD LFXTAL016178 / 85SMX watch crystal, manufacturer land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
        reference_at="0 -3.5 0",
    )

    for name, description, courtyard_left in (
        ("LM2576HV_TO-263-5", "Texas Instruments LM2576HV KTT 5-pin DDPAK/TO-263", -8.35),
        ("LM2596S_TO-263-5", "Texas Instruments LM2596S KTT 5-pin DDPAK/TO-263", -8.5),
    ):
        g = [
            body_fab(name, 4.32, 5.08, 0.45),
            fp_circle(name, "pin1", (2.2, 4.7), 0.18),
            *courtyard(name, courtyard_left, -5.65, 8.0, 5.65),
        ]
        pads = [
            smd_pad(name, "tab-3", "3", -4.57, 0, 6.99, 10.8, "rect"),
        ]
        for pin in range(1, 6):
            y = 3.4 - (pin - 1) * 1.7
            pads.append(smd_pad(name, f"lead-{pin}", str(pin), 6.10, y, 2.16, 1.07))
        generated[name] = footprint(
            name,
            description + ", manufacturer land dimensions; tab is pad 3",
            DATASHEET_URLS[name],
            g,
            pads,
            model_offset="-0.5 0 0",
        )

    name = "NCS213R_SC70-6"
    g = [body_fab(name, 1.0, 0.625, 0.2)]
    g += [
        fp_line(name, "silk-top", (-1.0, -0.45), (1.0, -0.45), "F.SilkS", 0.15),
        fp_line(name, "silk-bottom", (-0.95, 0.45), (1.05, 0.45), "F.SilkS", 0.15),
        fp_circle(name, "pin1", (-1.15, 0.95), 0.14),
        *courtyard(name, -1.25, -1.5, 1.25, 1.5),
    ]
    coords = {
        1: (-0.65, 0.92), 2: (0.0, 0.92), 3: (0.65, 0.92),
        4: (0.65, -0.92), 5: (0.0, -0.92), 6: (-0.65, -0.92),
    }
    pads = [smd_pad(name, f"pad-{pin}", str(pin), x, y, 0.30, 0.66) for pin, (x, y) in coords.items()]
    generated[name] = footprint(
        name,
        "onsemi NCS213RSQT2G SC70-6 / SC-88 case 419B manufacturer mounting footprint",
        DATASHEET_URLS[name],
        g,
        pads,
        reference_at="0 -2.6 0",
    )

    # Isabellenhuette BVN size 1216, recommended reflow land pattern. Pads 1
    # and 4 are the large current terminals; pads 2 and 3 are the Kelvin
    # sense terminals. The asymmetric pattern is centered on its full extent.
    name = "BVN-M-R001-1.0"
    g = [fp_poly(
        name,
        "fab-body",
        [(-1.30, -2.05), (1.55, -2.05), (1.55, 2.05),
         (-1.55, 2.05), (-1.55, -1.80)],
        "F.Fab",
    )]
    g += [
        fp_line(name, "silk-left", (-2.10, -2.15), (-2.10, 2.15), "F.SilkS", 0.2),
        fp_line(name, "silk-right", (2.10, -2.15), (2.10, 2.15), "F.SilkS", 0.2),
        fp_line(name, "silk-top", (-1.80, 2.40), (1.80, 2.40), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom", (-1.80, -2.40), (1.80, -2.40), "F.SilkS", 0.2),
        *courtyard(name, -2.25, -2.55, 2.25, 2.55),
    ]
    pads = [
        smd_pad(name, "current-1", "1", -1.05, -0.60, 1.50, 2.95, "rect"),
        smd_pad(name, "sense-2", "2", -1.05, 1.725, 1.50, 0.70, "rect"),
        smd_pad(name, "sense-3", "3", 1.05, 1.725, 1.50, 0.70, "rect"),
        smd_pad(name, "current-4", "4", 1.05, -0.60, 1.50, 2.95, "rect"),
    ]
    generated[name] = footprint(
        name,
        "Isabellenhuette BVN-M-R001 1 mOhm four-terminal shunt, size 1216, manufacturer reflow land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
        model_rotation="0 0 180",
        reference_at="0 -3.3 0",
    )

    # Wurth 7447709271 WE-PD size 1210. The datasheet shows the lands in a
    # vertical arrangement; this equivalent 90-degree rotation preserves the
    # existing footprint orientation with pin 1 on the left.
    name = "L_Wuerth_WE-PD-Typ-LS-1210"
    g = [fp_poly(
        name,
        "fab-body",
        [(-5.40, -6.00), (6.00, -6.00), (6.00, 6.00),
         (-6.00, 6.00), (-6.00, -5.40)],
        "F.Fab",
    )]
    g += [
        fp_line(name, "silk-top", (-6.15, -6.15), (6.15, -6.15), "F.SilkS", 0.20),
        fp_line(name, "silk-bottom", (-6.15, 6.15), (6.15, 6.15), "F.SilkS", 0.20),
        fp_line(name, "silk-left-top", (-6.15, -6.15), (-6.15, -3.15), "F.SilkS", 0.20),
        fp_line(name, "silk-left-bottom", (-6.15, 3.15), (-6.15, 6.15), "F.SilkS", 0.20),
        fp_line(name, "silk-right-top", (6.15, -6.15), (6.15, -3.15), "F.SilkS", 0.20),
        fp_line(name, "silk-right-bottom", (6.15, 3.15), (6.15, 6.15), "F.SilkS", 0.20),
        fp_circle(name, "start-of-winding", (-5.25, -5.25), 0.20),
        *courtyard(name, -6.65, -6.65, 6.65, 6.65),
    ]
    pads = [
        smd_pad(name, "pad-1", "1", -4.95, 0, 2.90, 5.40, "rect"),
        smd_pad(name, "pad-2", "2", 4.95, 0, 2.90, 5.40, "rect"),
    ]
    generated[name] = footprint(
        name,
        "Wurth Elektronik 7447709271 WE-PD shielded power inductor, size 1210, manufacturer land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
        model_name="L_Wuerth_WE-PD-Typ-LS",
        tag_name="L_Wuerth_WE-PD-Typ-LS",
    )

    # Wurth 7447789222 WE-PD Robust, size/type 7332.  Body 7.30 x 7.30 x 3.20 mm.
    # Manufacturer land pattern: 4.00 mm gap between pads, each pad 1.70 mm along
    # the gap axis by 2.00 mm across, so the pad centres sit at +/-2.85 mm and the
    # land spans 7.40 mm.  Rotated to the same pin-1-on-the-left convention used
    # by the WE-PD 1210 footprint above.
    name = "L_Wuerth_WE-PD-Robust-7332"
    half = 3.65
    g = [fp_poly(
        name,
        "fab-body",
        [(-half + 0.60, -half), (half, -half), (half, half),
         (-half, half), (-half, -half + 0.60)],
        "F.Fab",
    )]
    silk = 3.80
    g += [
        fp_line(name, "silk-top", (-silk, -silk), (silk, -silk), "F.SilkS", 0.20),
        fp_line(name, "silk-bottom", (-silk, silk), (silk, silk), "F.SilkS", 0.20),
        fp_line(name, "silk-left-top", (-silk, -silk), (-silk, -1.20), "F.SilkS", 0.20),
        fp_line(name, "silk-left-bottom", (-silk, 1.20), (-silk, silk), "F.SilkS", 0.20),
        fp_line(name, "silk-right-top", (silk, -silk), (silk, -1.20), "F.SilkS", 0.20),
        fp_line(name, "silk-right-bottom", (silk, 1.20), (silk, silk), "F.SilkS", 0.20),
        fp_circle(name, "start-of-winding", (-3.00, -3.00), 0.20),
        *courtyard(name, -4.30, -4.30, 4.30, 4.30),
    ]
    pads = [
        smd_pad(name, "pad-1", "1", -2.85, 0, 1.70, 2.00, "rect"),
        smd_pad(name, "pad-2", "2", 2.85, 0, 1.70, 2.00, "rect"),
    ]
    generated[name] = footprint(
        name,
        "Wurth Elektronik 7447789222 WE-PD Robust shielded power inductor, size 7332, manufacturer land pattern",
        DATASHEET_URLS[name],
        g,
        pads,
    )

    # Analog Devices LTC3639 in the MSE16(12) package: a 16-lead MSOP outline with
    # pins 2, 4, 13 and 15 removed for high-voltage creepage, plus exposed pad 17.
    # Lead pitch 0.50 mm BSC, lead span 4.90 mm, body 3.00 x 4.039 mm, exposed pad
    # 1.651 x 2.845 mm.  Land pattern follows the datasheet solder-pad layout:
    # 0.305 mm pad width on a 0.50 mm pitch with a 5.10 mm outer span.
    name = "LTC3639_MSE16-12"
    g = [fp_poly(
        name,
        "fab-body",
        [(-1.50, -2.02 + 0.50), (-1.50 + 0.50, -2.02), (1.50, -2.02),
         (1.50, 2.02), (-1.50, 2.02)],
        "F.Fab",
    )]
    g += [
        fp_line(name, "silk-top", (-1.50, -2.13), (1.50, -2.13), "F.SilkS", 0.12),
        fp_line(name, "silk-bottom", (-1.50, 2.13), (1.50, 2.13), "F.SilkS", 0.12),
        fp_circle(name, "pin1", (-2.58, -2.13), 0.15),
        *courtyard(name, -2.80, -2.35, 2.80, 2.35),
    ]
    # Eight lead sites per side on a 0.50 mm pitch; the removed pins leave gaps.
    # Pads sit at +/-2.11 with a 1.016 mm length, so the land spans 5.236 mm
    # (datasheet minimum 5.10) and clears the exposed pad by 0.78 mm.
    sites = [-1.75 + i * 0.50 for i in range(8)]
    left_pins = {0: 1, 2: 3, 4: 5, 5: 6, 6: 7, 7: 8}
    right_pins = {7: 9, 6: 10, 5: 11, 4: 12, 2: 14, 0: 16}
    pads = []
    for index, number in sorted(left_pins.items()):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), -2.11, sites[index], 1.016, 0.305,
            roundrect_rratio=1 / 6,
        ))
    for index, number in sorted(right_pins.items()):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), 2.11, sites[index], 1.016, 0.305,
            roundrect_rratio=1 / 6,
        ))
    pads.append(smd_pad(name, "powerpad-17", "17", 0, 0, 1.651, 2.845, "rect"))
    generated[name] = footprint(
        name,
        "Analog Devices LTC3639 MSE16(12) 16-lead MSOP with four pins removed and exposed die pad",
        DATASHEET_URLS[name],
        g,
        pads,
        reference_at="0 -3.3 0",
        value_at="0 3.3 0",
    )

    name = "Power_Pad_6x6mm"
    g = [
        body_fab(name, 3.0, 3.0, 0.3),
        fp_circle(name, "pin1", (-3.35, 3.35), 0.16),
        *courtyard(name, -3.25, -3.25, 3.25, 3.25),
    ]
    pads = [smd_pad(name, "pad-1", "1", 0, 0, 6.0, 6.0, "rect")]
    generated[name] = footprint(
        name,
        "Original generic 6 x 6 mm SMD power connection pad",
        "",
        g,
        pads,
        reference_at="0 -4 0",
        model_rotation="0 0 -90",
    )

    # TI PW0016A: 16 perimeter lands on 0.65 mm pitch. The manufacturer
    # example board layout specifies 5.8 mm between opposite pad centre
    # lines and 1.5 x 0.45 mm lands. There is no exposed pad.
    name = "BQ79600-Q1"
    g = [fp_poly(
        name,
        "fab-body",
        [(-1.8, -2.5), (2.2, -2.5), (2.2, 2.5),
         (-2.2, 2.5), (-2.2, -2.1)],
        "F.Fab",
    )]
    g += [
        fp_line(name, "silk-top", (-2.35, -2.65), (2.35, -2.65), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom", (-2.35, 2.65), (2.35, 2.65), "F.SilkS", 0.2),
        fp_circle(name, "pin1", (-3.75, -2.75), 0.10),
        *courtyard(name, -3.90, -2.90, 3.90, 2.90),
    ]
    pads = []
    positions = [-2.275 + index * 0.65 for index in range(8)]
    for number, y in enumerate(positions, 1):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), -2.90, y, 1.50, 0.45,
            roundrect_rratio=1 / 6,
        ))
    for number, y in zip(range(9, 17), reversed(positions)):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), 2.90, y, 1.50, 0.45,
            roundrect_rratio=1 / 6,
        ))
    generated[name] = footprint(
        name,
        "Texas Instruments BQ79600-Q1 PW0016A 16-pin TSSOP, manufacturer land pattern",
        DATASHEET_URLS[name], g, pads,
        reference_at="0 -3.8 0",
        value_at="0 3.8 0",
    )

    # TI PHP0048N: 48 perimeter lands on 0.5 mm pitch. The 8.5 mm
    # dimension is the distance between opposite pad centre lines, not the
    # overall land-pattern width. Pad 49 uses the retained
    # 5.17 mm copper size and its retained local mask/paste margins. Pin order
    # follows the top-view package drawing.
    name = "BQ79606A-Q1"
    g = [body_fab(name, 3.5, 3.5, 0.45)]
    g += [
        fp_line(name, "silk-top-left", (-3.7, -3.7), (-3.1, -3.7), "F.SilkS", 0.2),
        fp_line(name, "silk-top-right", (3.1, -3.7), (3.7, -3.7), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom-left", (-3.7, 3.7), (-3.1, 3.7), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom-right", (3.1, 3.7), (3.7, 3.7), "F.SilkS", 0.2),
        fp_line(name, "silk-left-top", (-3.7, -3.7), (-3.7, -3.1), "F.SilkS", 0.2),
        fp_line(name, "silk-left-bottom", (-3.7, 3.1), (-3.7, 3.7), "F.SilkS", 0.2),
        fp_line(name, "silk-right-top", (3.7, -3.7), (3.7, -3.1), "F.SilkS", 0.2),
        fp_line(name, "silk-right-bottom", (3.7, 3.1), (3.7, 3.7), "F.SilkS", 0.2),
        fp_circle(name, "pin1", (-5.0, -3.30), 0.18),
        *courtyard(name, -5.30, -5.30, 5.30, 5.30),
    ]
    pads = []
    positions = [-2.75 + i * 0.5 for i in range(12)]
    for i, y in enumerate(positions, 1):
        pads.append(smd_pad(
            name, f"pad-{i}", str(i), -4.25, y, 1.60, 0.30,
            roundrect_rratio=1 / 6,
        ))
    for i, x in zip(range(13, 25), positions):
        pads.append(smd_pad(
            name, f"pad-{i}", str(i), x, 4.25, 0.30, 1.60,
            roundrect_rratio=1 / 6,
        ))
    for i, y in zip(range(25, 37), reversed(positions)):
        pads.append(smd_pad(
            name, f"pad-{i}", str(i), 4.25, y, 1.60, 0.30,
            roundrect_rratio=1 / 6,
        ))
    for i, x in zip(range(37, 49), reversed(positions)):
        pads.append(smd_pad(
            name, f"pad-{i}", str(i), x, -4.25, 0.30, 1.60,
            roundrect_rratio=1 / 6,
        ))
    pads.append(smd_pad(
        name, "powerpad-49", "49", 0, 0, 5.17, 5.17, "rect",
        solder_mask_margin=-0.665,
        solder_paste_margin=-0.665,
    ))
    generated[name] = footprint(
        name,
        "Texas Instruments BQ79606A-Q1 PHP0048N 48-pin PowerPAD HTQFP, manufacturer land pattern",
        DATASHEET_URLS[name], g, pads,
        model_rotation="0 0 90",
    )

    # TI PAP0064F: 64 perimeter lands on 0.5 mm pitch with an exposed
    # thermal pad numbered 65. The manufacturer land pattern specifies
    # 11.4 mm between opposite pad centre lines, 1.5 x 0.3 mm perimeter
    # lands, and a 6.5 x 6.5 mm exposed-pad land. Thermal vias are optional
    # and deliberately left to the board designer.
    name = "BQ79616-Q1"
    g = [fp_poly(
        name,
        "fab-body",
        [(-4.5, -5.0), (5.0, -5.0), (5.0, 5.0),
         (-5.0, 5.0), (-5.0, -4.5)],
        "F.Fab",
    )]
    corner = 5.15
    inner = 4.55
    g += [
        fp_line(name, "silk-top-left", (-corner, -corner), (-inner, -corner), "F.SilkS", 0.2),
        fp_line(name, "silk-left-top", (-corner, -corner), (-corner, -inner), "F.SilkS", 0.2),
        fp_line(name, "silk-top-right", (inner, -corner), (corner, -corner), "F.SilkS", 0.2),
        fp_line(name, "silk-right-top", (corner, -corner), (corner, -inner), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom-left", (-corner, corner), (-inner, corner), "F.SilkS", 0.2),
        fp_line(name, "silk-left-bottom", (-corner, inner), (-corner, corner), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom-right", (inner, corner), (corner, corner), "F.SilkS", 0.2),
        fp_line(name, "silk-right-bottom", (corner, inner), (corner, corner), "F.SilkS", 0.2),
        fp_circle(name, "pin1", (-6.15, -4.4), 0.18),
        *courtyard(name, -6.70, -6.70, 6.70, 6.70),
    ]
    pads = []
    positions = [-3.75 + i * 0.5 for i in range(16)]
    for number, y in enumerate(positions, 1):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), -5.70, y, 1.50, 0.30,
            roundrect_rratio=1 / 6,
        ))
    for number, x in zip(range(17, 33), positions):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), x, 5.70, 0.30, 1.50,
            roundrect_rratio=1 / 6,
        ))
    for number, y in zip(range(33, 49), reversed(positions)):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), 5.70, y, 1.50, 0.30,
            roundrect_rratio=1 / 6,
        ))
    for number, x in zip(range(49, 65), reversed(positions)):
        pads.append(smd_pad(
            name, f"pad-{number}", str(number), x, -5.70, 0.30, 1.50,
            roundrect_rratio=1 / 6,
        ))
    pads.append(smd_pad(name, "powerpad-65", "65", 0, 0, 6.50, 6.50, "rect"))
    generated[name] = footprint(
        name,
        "Texas Instruments BQ79616-Q1 PAP0064F 64-pin PowerPAD HTQFP, manufacturer land pattern",
        DATASHEET_URLS[name], g, pads,
        reference_at="0 -7.5 0",
        value_at="0 7.5 0",
        model_rotation="0 0 90",
    )

    name = "INA286_SOIC-8"
    g = [body_fab(name, 1.95, 2.45, 0.35)]
    g += [
        fp_line(name, "silk-top", (-2.05, -2.45), (2.05, -2.45), "F.SilkS", 0.15),
        fp_line(name, "silk-bottom", (-2.05, 2.45), (2.05, 2.45), "F.SilkS", 0.15),
        fp_circle(name, "pin1", (-2.25, -2.7), 0.16),
        *courtyard(name, -3.75, -2.85, 3.75, 2.85),
    ]
    ys = (-1.905, -0.635, 0.635, 1.905)
    pads = [smd_pad(name, f"pad-{i}", str(i), -2.70, y, 1.55, 0.60) for i, y in enumerate(ys, 1)]
    pads += [smd_pad(name, f"pad-{i}", str(i), 2.70, y, 1.55, 0.60) for i, y in zip(range(5, 9), reversed(ys))]
    generated[name] = footprint(
        name, "Texas Instruments INA286 D0008A SOIC-8, manufacturer land pattern",
        DATASHEET_URLS[name], g, pads,
        model_rotation="0 0 180",
        reference_at="0 -3.5 0",
    )

    name = "STB45N65M5_D2PAK"
    g = [body_fab(name, 5.1, 7.7, 0.5)]
    g += [
        fp_line(name, "silk-body-front", (-5.1, 3.75), (5.1, 3.75), "F.SilkS", 0.2),
        fp_circle(name, "pin1", (-3.45, 4.45), 0.18),
        *courtyard(name, -6.35, -8.70, 6.35, 8.70),
    ]
    pads = [
        smd_pad(name, "gate-1", "1", -2.54, 6.70, 1.60, 3.50, "rect"),
        smd_pad(name, "drain-tab-2", "2", 0, -3.575, 12.20, 9.75, "rect"),
        smd_pad(name, "source-3", "3", 2.54, 6.70, 1.60, 3.50, "rect"),
    ]
    generated[name] = footprint(
        name, "STMicroelectronics STB45N65M5 D2PAK TO-263 type A2, manufacturer recommended footprint",
        DATASHEET_URLS[name], g, pads,
        model_rotation="0 0 180",
        reference_at="0 -9.4 0",
    )

    name = "CSS2H-3920R-L200F"
    g = [body_fab(name, 5.0, 2.6, 0.3)]
    g += [
        fp_line(name, "silk-top", (-5.4, -3.35), (5.4, -3.35), "F.SilkS", 0.2),
        fp_line(name, "silk-bottom", (-5.4, 3.35), (5.4, 3.35), "F.SilkS", 0.2),
        *courtyard(name, -6.25, -3.65, 6.25, 3.65),
    ]
    pads = [
        smd_pad(name, "current-1", "1", -4.15, 0, 2.7, 6.20, "rect"),
        smd_pad(name, "current-2", "2", 4.15, 0, 2.7, 6.20, "rect"),
    ]
    generated[name] = footprint(
        name, "Bourns CSS2H-3920R-L200F four-terminal current-sense resistor, manufacturer recommended Kelvin layout",
        DATASHEET_URLS[name], g, pads,
        reference_at="0 -4.4 0",
    )

    name = "1N6263W_SOD-123"
    g = [body_fab(name, 1.325, 0.775, 0.15)]
    g += [
        fp_line(name, "silk-top", (-1.35, -0.9), (1.35, -0.9), "F.SilkS", 0.15),
        fp_line(name, "silk-bottom", (-1.35, 0.9), (1.35, 0.9), "F.SilkS", 0.15),
        fp_line(name, "cathode", (-0.9, -0.9), (-0.9, 0.9), "F.SilkS", 0.30),
        *courtyard(name, -2.30, -1.15, 2.30, 1.15),
    ]
    pads = [
        smd_pad(name, "cathode-1", "1", -1.575, 0, 0.90, 0.95),
        smd_pad(name, "anode-2", "2", 1.575, 0, 0.90, 0.95),
    ]
    generated[name] = footprint(
        name, "Diodes Incorporated 1N6263W Schottky diode, SOD-123 suggested pad layout",
        DATASHEET_URLS[name], g, pads,
        reference_at="0 -1.9 0",
    )

    # Bourns SM91502AL recommended layout. The drawing specifies 0.76 mm
    # land width, 9.65 mm outside span, and 7.11 mm inside gap. Therefore the
    # land length is (9.65 - 7.11) / 2 = 1.27 mm and the row centres are at
    # +/-4.19 mm. Pin order follows the top-view package drawing: 1-2-3 on
    # the pin-one side and 6-5-4 on the opposite side.
    name = "SM91502AL"
    g = [body_fab(name, 3.81, 3.555, 0.45)]
    g += [
        fp_line(name, "silk-left", (-3.95, -3.70), (-3.95, 3.70), "F.SilkS", 0.20),
        fp_line(name, "silk-right", (3.95, -3.70), (3.95, 3.70), "F.SilkS", 0.20),
        fp_line(name, "silk-top-left", (-3.95, -3.70), (-3.05, -3.70), "F.SilkS", 0.20),
        fp_line(name, "silk-top-right", (3.05, -3.70), (3.95, -3.70), "F.SilkS", 0.20),
        fp_line(name, "silk-bottom-left", (-3.95, 3.70), (-3.05, 3.70), "F.SilkS", 0.20),
        fp_line(name, "silk-bottom-right", (3.05, 3.70), (3.95, 3.70), "F.SilkS", 0.20),
        fp_circle(name, "pin1", (-4.25, 3.95), 0.18),
        *courtyard(name, -4.20, -5.10, 4.20, 5.10),
    ]
    pads = [
        smd_pad(name, "pad-1", "1", -2.54, 4.19, 0.76, 1.27, "rect"),
        smd_pad(name, "pad-2", "2", 0.00, 4.19, 0.76, 1.27),
        smd_pad(name, "pad-3", "3", 2.54, 4.19, 0.76, 1.27),
        smd_pad(name, "pad-4", "4", 2.54, -4.19, 0.76, 1.27),
        smd_pad(name, "pad-5", "5", 0.00, -4.19, 0.76, 1.27),
        smd_pad(name, "pad-6", "6", -2.54, -4.19, 0.76, 1.27),
    ]
    generated[name] = footprint(
        name,
        "Bourns SM91502AL six-pin BMS isolation transformer with integrated common-mode choke, manufacturer recommended layout",
        DATASHEET_URLS[name],
        g,
        pads,
        reference_at="0 -5.85 0",
        value_at="0 5.85 0",
    )

    generated.update(generate_connector_footprints())
    generated.update(generate_minimal_silkscreen_footprints(generated))

    return generated


# Harwin Gecko-SL G125-MV1XX05M2P, from customer information sheet DRG-02638
# issue 3. Table 1 gives DIM 'A' (Screw-Lok stud spacing), DIM 'B' (contact
# array span) and DIM 'C' (overall body) per circuit count. Every listed row
# satisfies B = (circuits/2 - 1) x 1.25, A = B + 7.80 and C = A + 4.90, so the
# table is reproduced here as those relations rather than as transcribed
# numbers; the 6- and 20-way values used below match the sheet exactly.
GECKO_PITCH = 1.25
GECKO_ROW_SPACING = 1.25
GECKO_CONTACT_DRILL = 0.55
GECKO_CONTACT_PAD = 0.95
GECKO_STUD_DRILL = 2.25
GECKO_STUD_OFFSET = 3.90      # end contact to stud centre
GECKO_BODY_OVERHANG = 2.45    # stud centre to body end
GECKO_BODY_HALF_WIDTH = 2.45  # 4.90 body width


def gecko_footprint(circuits: int) -> tuple[str, str]:
    """Return (name, footprint text) for a Gecko-SL vertical THT Screw-Lok plug.

    Contacts are numbered the Harwin way (Component Specification C125XX,
    Appendix 1): 1..n on the first row, n+1..2n on the second. The cell-tap
    interleaving that keeps adjacent contacts close in potential is expressed
    in the schematic pin assignment, not by renumbering these pads.
    """
    per_row = circuits // 2
    span = (per_row - 1) * GECKO_PITCH
    stud_x = span / 2.0 + GECKO_STUD_OFFSET
    body_x = stud_x + GECKO_BODY_OVERHANG
    part = f"G125-MV1{circuits:02d}05M2P"
    name = f"Harwin_Gecko_{part}_2x{per_row:02d}_P1.25mm_Vertical"

    row_y = GECKO_ROW_SPACING / 2.0
    cols = [-span / 2.0 + i * GECKO_PITCH for i in range(per_row)]

    silk_y = GECKO_BODY_HALF_WIDTH + 0.11
    silk_x = body_x + 0.11
    graphics = rect_outline(name, "fab", -body_x, -GECKO_BODY_HALF_WIDTH,
                            body_x, GECKO_BODY_HALF_WIDTH, "F.Fab", 0.1)
    graphics.append(fp_line(name, "fab-pin1", (-body_x, row_y + 0.55),
                            (-body_x + 1.0, GECKO_BODY_HALF_WIDTH), "F.Fab", 0.1))
    graphics += rect_outline(name, "silk", -silk_x, -silk_y, silk_x, silk_y, "F.SilkS", 0.12)
    graphics.append(fp_line(name, "silk-pin1", (-silk_x, silk_y + 0.5),
                            (-silk_x + 1.0, silk_y + 0.5), "F.SilkS", 0.12))
    graphics += courtyard(name, -(body_x + 0.25), -(GECKO_BODY_HALF_WIDTH + 0.3),
                          body_x + 0.25, GECKO_BODY_HALF_WIDTH + 0.3)

    pads = []
    for index, x in enumerate(cols):
        pads.append(pth_pad_shaped(
            name, f"pad-{index + 1}", str(index + 1), x, row_y,
            GECKO_CONTACT_PAD, GECKO_CONTACT_PAD, GECKO_CONTACT_DRILL,
            "rect" if index == 0 else "circle"))
    for index, x in enumerate(cols):
        pads.append(pth_pad_shaped(
            name, f"pad-{per_row + index + 1}", str(per_row + index + 1), x, -row_y,
            GECKO_CONTACT_PAD, GECKO_CONTACT_PAD, GECKO_CONTACT_DRILL, "circle"))
    pads.append(npth_pad(name, "stud-left", -stud_x, 0.0, GECKO_STUD_DRILL))
    pads.append(npth_pad(name, "stud-right", stud_x, 0.0, GECKO_STUD_DRILL))

    description = (
        f"Harwin Gecko-SL {part}, {circuits} contacts (2x{per_row}), 1.25mm pitch, male vertical "
        "THT, Screw-Lok M2x0.4 with 5mm board mount studs, gold, 2A per contact, 450V. "
        f"Contact span {span:.2f}mm, stud spacing {2 * stud_x:.2f}mm, body {2 * body_x:.2f}mm. "
        "Harwin contact numbering: 1-%d row one, %d-%d row two. "
        "Board mount nuts G125-4510000B or G125-4500000B ordered separately"
        % (per_row, per_row + 1, circuits)
    )
    return name, footprint(
        name, description, HARWIN_GECKO_M2P_DRAWING, graphics, pads,
        attr="through_hole",
        model_name=f"Harwin_Gecko_{part}",
        reference_at=f"0 {-(GECKO_BODY_HALF_WIDTH + 1.35):g} 0",
        value_at=f"0 {GECKO_BODY_HALF_WIDTH + 1.35:g} 0",
        tag_name="harwin gecko G125 1.25mm connector tht screwlok",
    )


def jst_xh_footprint(circuits: int) -> tuple[str, str]:
    """Return (name, footprint text) for a JST XH vertical THT shrouded header.

    XH dimensions follow the series relations: contact span A = (n - 1) x 2.50
    and moulded body B = A + 4.90, with a 5.75mm body offset 2.35mm ahead of
    and 3.40mm behind the contact row. Origin is the centre of the contact row.
    """
    pitch = 2.50
    span = (circuits - 1) * pitch
    body_x = span / 2.0 + 2.45
    front, back = -2.35, 3.40
    part = f"B{circuits}B-XH-A"
    name = f"JST_XH_{part}_1x{circuits:02d}_P2.50mm_Vertical"

    cols = [-span / 2.0 + i * pitch for i in range(circuits)]
    graphics = rect_outline(name, "fab", -body_x, front, body_x, back, "F.Fab", 0.1)
    graphics.append(fp_line(name, "fab-pin1", (-body_x, front + 1.0),
                            (-body_x + 1.0, front), "F.Fab", 0.1))
    graphics += rect_outline(name, "silk", -(body_x + 0.11), front - 0.11,
                             body_x + 0.11, back + 0.11, "F.SilkS", 0.12)
    graphics.append(fp_line(name, "silk-pin1", (-(body_x + 0.11), front - 0.61),
                            (-(body_x + 0.11) + 1.6, front - 0.61), "F.SilkS", 0.12))
    graphics += courtyard(name, -(body_x + 0.5), front - 0.5, body_x + 0.5, back + 0.5)

    pads = [
        pth_pad_shaped(name, f"pad-{i + 1}", str(i + 1), x, 0.0, 1.80, 2.00, 1.00,
                       "rect" if i == 0 else "oval")
        for i, x in enumerate(cols)
    ]
    description = (
        f"JST XH {part}, {circuits} circuits, 2.50mm pitch, single row male vertical THT shrouded "
        f"header, 250V, 3A. Contact span {span:.2f}mm, body {2 * body_x:.2f}mm x 5.75mm offset "
        "2.35mm / 3.40mm about the contact row. Origin at the centre of the contact row"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        attr="through_hole",
        reference_at=f"0 {front - 1.4:g} 0",
        value_at=f"0 {back + 1.4:g} 0",
        tag_name="jst xh connector 2.50mm tht shrouded header",
    )


# Molex Mini50 dual-row vertical through-hole header, series 34825, from sales
# drawing SD-348250200 ("MINI50 12-24CKT VERT HDR"). Values marked below as
# labelled come straight off the drawing; the row spacing is not called out as
# a single dimension, so it was measured from the drawn hole centres in the PCB
# layout views (2.20 mm, identical in all four views, rows aligned rather than
# staggered) and cross-checked against the two transverse callouts, whose
# difference 4.75 - 2.55 is exactly that row spacing.
MINI50_PITCH = 2.00            # labelled TYP 2.00
MINI50_ROW_SPACING = 2.20      # measured; 4.75 - 2.55 = 2.20 confirms it
MINI50_CONTACT_DRILL = 1.00    # labelled TYP 1.00 +/- 0.08
MINI50_CONTACT_PAD = 1.70
MINI50_POST_DRILL = 2.15       # POST HOLE TABLE, DIM E press fit (drop in 2.55)
MINI50_POST_TO_ROW = 2.55      # labelled; post axis beyond the second row
MINI50_POST_OUTBOARD = 4.85    # (post spacing - contact span) / 2, constant

# Labelled per circuit count. The sheet carries two length series: DIM C
# (20.40/24.40/28.40/32.40) and a second (22.63/26.63/30.63/34.63). The posts
# sit 1.025 outside DIM C once their diameter is counted, which a moulded peg
# cannot do, so the larger series is the overall body and DIM C is the shroud.
MINI50_BODY_LENGTH = {12: 22.63, 16: 26.63, 20: 30.63, 24: 34.63}
MINI50_SHROUD_LENGTH = {12: 20.40, 16: 24.40, 20: 28.40, 24: 32.40}
MINI50_POST_SPACING = {12: 19.70, 16: 23.70, 20: 27.70, 24: 31.70}


def mini50_footprint(circuits: int) -> tuple[str, str]:
    """Return (name, footprint text) for a Molex Mini50 34825 vertical header.

    Origin is the centre of the contact array, midway between the two rows.
    Pads 1..n/2 are the +Y row and n/2+1..n the -Y row; the drawing's circuit
    numbering view was not machine-readable, so confirm which physical row is
    circuit 1 before wiring this to a symbol.
    """
    per_row = circuits // 2
    span = (per_row - 1) * MINI50_PITCH
    post_x = MINI50_POST_SPACING[circuits] / 2.0
    body_x = MINI50_BODY_LENGTH[circuits] / 2.0
    row_y = MINI50_ROW_SPACING / 2.0
    post_y = -(row_y + MINI50_POST_TO_ROW)
    # Molex suffixes these by circuits x 10: 34825-0160 is the 16-way.
    part = f"34825-{circuits * 10:04d}"
    name = f"Molex_Mini50_{part}_2x{per_row:02d}_P2.00mm_Vertical"

    cols = [-span / 2.0 + i * MINI50_PITCH for i in range(per_row)]

    # Courtyard and silkscreen are derived from the confirmed features plus a
    # margin rather than from a body outline; the drawing's transverse body
    # dimensions were not resolvable from the PDF text.
    top = row_y + MINI50_CONTACT_PAD / 2.0
    bottom = post_y - MINI50_POST_DRILL / 2.0
    # The posts reach further out than the body edge once their hole diameter
    # is counted, so the courtyard is sized from whichever dominates.
    edge_x = max(body_x, post_x + MINI50_POST_DRILL / 2.0)

    graphics = rect_outline(name, "fab", -body_x, bottom - 0.2, body_x, top + 0.2, "F.Fab", 0.1)
    graphics.append(fp_line(name, "fab-pin1", (-body_x, top - 0.8),
                            (-body_x + 1.0, top + 0.2), "F.Fab", 0.1))
    graphics += rect_outline(name, "silk", -(body_x + 0.11), bottom - 0.31,
                             body_x + 0.11, top + 0.31, "F.SilkS", 0.12)
    graphics.append(fp_line(name, "silk-pin1", (-(body_x + 0.11), top + 0.81),
                            (-(body_x + 0.11) + 1.4, top + 0.81), "F.SilkS", 0.12))
    graphics += courtyard(name, -(edge_x + 0.5), bottom - 0.7, edge_x + 0.5, top + 0.7)

    pads = []
    for index, x in enumerate(cols):
        pads.append(pth_pad_shaped(
            name, f"pad-{index + 1}", str(index + 1), x, row_y,
            MINI50_CONTACT_PAD, MINI50_CONTACT_PAD, MINI50_CONTACT_DRILL,
            "rect" if index == 0 else "circle"))
    for index, x in enumerate(cols):
        pads.append(pth_pad_shaped(
            name, f"pad-{per_row + index + 1}", str(per_row + index + 1), x, -row_y,
            MINI50_CONTACT_PAD, MINI50_CONTACT_PAD, MINI50_CONTACT_DRILL, "circle"))
    pads.append(npth_pad(name, "post-left", -post_x, post_y, MINI50_POST_DRILL))
    pads.append(npth_pad(name, "post-right", post_x, post_y, MINI50_POST_DRILL))

    description = (
        f"Molex Mini50 {part}, {circuits} circuits (2x{per_row}), 2.00mm pitch, dual row male "
        "vertical THT unsealed automotive header, 500V, 4.0A, -40 to +105C, tin over nickel, "
        "USCAR-2. Contact holes 1.00mm on a 2.00mm pitch with 2.20mm row spacing; "
        f"2x {MINI50_POST_DRILL:.2f}mm press-fit post holes at {2 * post_x:.2f}mm spacing, "
        f"{MINI50_POST_TO_ROW:.2f}mm beyond the second contact row (drop-in variant uses 2.55mm). "
        f"Body {MINI50_BODY_LENGTH[circuits]:.2f} x 12.17mm, 15.60mm above the PCB, with a "
        f"{MINI50_SHROUD_LENGTH[circuits]:.2f}mm shroud. Origin at the centre of the contact "
        "array. Confirm which physical row carries circuit 1 against the drawing before wiring"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        attr="through_hole",
        reference_at=f"0 {top + 1.9:g} 0",
        value_at=f"0 {bottom - 1.5:g} 0",
        tag_name="molex mini50 34825 2.00mm connector tht vertical automotive",
    )


# Molex Mini50 single-row vertical through-hole header, series 34792, from
# sales drawing SD-34792-001 ("MINI50 4-8CKT VERTICAL HDR"). Pitch, contact
# hole and the DIM E post hole table are labelled on the drawing and match the
# dual-row 34825 exactly. The post hole spacing and the post offset from the
# contact row were read off the drawing by the user; note that the drawing's
# "2X 3.20" callout does NOT reconcile with the 11.70 post spacing, so 3.20 is
# something other than end-contact-to-post - do not re-derive from it.
MINI50_SR_POST_SPACING = {4: 11.70}
MINI50_SR_POST_TO_ROW = 2.55
MINI50_SR_BODY_WIDTH = 9.94       # +/- 0.08
MINI50_SR_BODY_LENGTH = {4: 14.62}


def mini50_single_row_footprint(circuits: int) -> tuple[str, str]:
    """Return (name, footprint text) for a Molex Mini50 34792 vertical header.

    Origin is the centre of the contact row, which lies on Y = 0; the two
    mounting posts sit 2.55 mm to -Y of it.
    """
    span = (circuits - 1) * MINI50_PITCH
    post_x = MINI50_SR_POST_SPACING[circuits] / 2.0
    post_y = -MINI50_SR_POST_TO_ROW
    part = f"34792-{circuits * 10:04d}1"
    name = f"Molex_Mini50_34792_1x{circuits:02d}_P2.00mm_Vertical"

    cols = [-span / 2.0 + i * MINI50_PITCH for i in range(circuits)]

    top = MINI50_CONTACT_PAD / 2.0
    bottom = post_y - MINI50_POST_DRILL / 2.0
    edge_x = max(post_x + MINI50_POST_DRILL / 2.0, span / 2.0 + MINI50_CONTACT_PAD / 2.0)

    graphics = rect_outline(name, "fab", -edge_x, bottom - 0.2, edge_x, top + 0.2, "F.Fab", 0.1)
    graphics.append(fp_line(name, "fab-pin1", (-edge_x, top - 0.6),
                            (-edge_x + 0.8, top + 0.2), "F.Fab", 0.1))
    graphics += rect_outline(name, "silk", -(edge_x + 0.11), bottom - 0.31,
                             edge_x + 0.11, top + 0.31, "F.SilkS", 0.12)
    graphics.append(fp_line(name, "silk-pin1", (-(edge_x + 0.11), top + 0.81),
                            (-(edge_x + 0.11) + 1.4, top + 0.81), "F.SilkS", 0.12))
    graphics += courtyard(name, -(edge_x + 0.5), bottom - 0.7, edge_x + 0.5, top + 0.7)

    pads = [
        pth_pad_shaped(name, f"pad-{i + 1}", str(i + 1), x, 0.0,
                       MINI50_CONTACT_PAD, MINI50_CONTACT_PAD, MINI50_CONTACT_DRILL,
                       "rect" if i == 0 else "circle")
        for i, x in enumerate(cols)
    ]
    pads.append(npth_pad(name, "post-left", -post_x, post_y, MINI50_POST_DRILL))
    pads.append(npth_pad(name, "post-right", post_x, post_y, MINI50_POST_DRILL))

    description = (
        f"Molex Mini50 34792 series, {circuits} circuits, 2.00mm pitch, single row male vertical "
        "THT unsealed automotive header, 500V, 4.0A, -40 to +105C, tin over nickel, USCAR-2, "
        "flush mount to PCB. Contact holes 1.00mm on a 2.00mm pitch; "
        f"2x {MINI50_POST_DRILL:.2f}mm press-fit post holes at {2 * post_x:.2f}mm spacing, "
        f"{MINI50_SR_POST_TO_ROW:.2f}mm to -Y of the contact row (drop-in variant uses 2.55mm). "
        f"Moulded body {MINI50_SR_BODY_LENGTH[circuits]:.2f} x {MINI50_SR_BODY_WIDTH:.2f}mm. "
        f"Origin at the centre of the contact row. SD-34792-001 covers several {circuits}-circuit "
        f"polarisation variants sharing this land pattern, e.g. {part}; confirm the order number "
        "and which end is circuit 1 before wiring"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        attr="through_hole",
        model_name="Molex_Mini50_34792_1x04",
        reference_at=f"0 {top + 1.9:g} 0",
        value_at=f"0 {bottom - 1.5:g} 0",
        tag_name="molex mini50 34792 2.00mm connector tht vertical automotive",
    )


# Harwin Datamate M80, 2.00mm pitch high-reliability rectangular connectors.
#
# Pitch, row spacing, contact positions, body envelope, above-board height and
# PC tail length were recovered by measuring the manufacturer reference solids
# supplied with each part (dimensional facts only - no geometry is reused, and
# every model and footprint here is drawn from scratch). The 0.90mm contact
# hole comes from the PCB layout view on Harwin drawing M80-511, measured
# against the known 2.00mm pitch, which resolves to 0.911mm on that sheet.
#
# The reference solids show the internal-thread jackscrews (Y 0.00..4.50) and
# the L-Tek latches (Y 0.40..8.35) sitting entirely at or above the seating
# plane, so none of these six needs a mounting hole - unlike the board-mount
# jackscrew variants such as M80-511, whose sheet shows 2.4mm holes.
#
# Contact numbering is row-wise per component specification C005XX Appendix 1
# (1..n/2 along one row, then n/2+1..n). Those diagrams are drawn looking onto
# the male contact face, so they mirror in a PCB top view; which physical row
# carries contact 1 relative to the polarising key is NOT established here.
M80_HOLE = 0.90
M80_PAD = 1.50
M80_PITCH = 2.00
M80_ROW_SPACING = 2.00

M80_PARTS = {
    # part: (contacts, rows, overall_x, body_y0, body_y1, above_board, tail,
    #        family, fixing, fixing_x, fixing_size_x)
    "M80-5001642": (16, 2, 26.00, -3.275, 2.775, 5.55, 3.30, "J-Tek", "jackscrew", 10.50, 3.10),
    "M80-5002042": (20, 2, 30.00, -3.275, 2.775, 5.55, 3.30, "J-Tek", "jackscrew", 12.50, 3.10),
    "M80-5T10442MC": (4, 2, 14.00, -3.275, 2.775, 5.55, 3.30, "J-Tek", "101-Lok", 4.50, 3.10),
    "M80-8531642": (16, 2, 19.90, -2.775, 3.075, 8.35, 3.30, "L-Tek", "latch", 9.35, 1.20),
    "M80-8672022": (20, 2, 23.90, -2.775, 3.075, 8.35, 3.30, "L-Tek", "latch", 11.35, 1.20),
    "M80-8770222": (2, 1, 7.90, -1.775, 2.075, 8.35, 3.30, "L-Tek", "latch", 3.35, 1.20),
}


def datamate_m80_lock_graphics(name: str, part: str) -> list[str]:
    """Visual locking-hardware clearance guides; no copper, holes or keepouts.

    Harwin drawings M80-500XXXX and M80-5T1XXXXMC put the locking axes on
    the contact-row midline (y=0), spaced by total contact count + 5 mm:
    https://content.harwin.com/asset/d4ebb836-b6ed-4f77-9fa4-5aa8f7c8ae78/DRG-01208-Technical-Drawing-Datasheet-M80-500-pdf.pdf
    https://content.harwin.com/asset/13228269-d433-42ef-b66c-9aca307698f8/DRG-01643-Technical-Drawing-Datasheet-M80-5T1XXXXMC-pdf.pdf

    The existing original models use a 3.10 x 3.10 mm fixing envelope.
    Add a chosen layout margin of 0.50 mm per side, giving a 4.10 mm square.
    This margin is a visual routing allowance, not a manufacturer-specified
    hole diameter or certified electrical clearance. Crosses mark the axes
    for optional future holes; these footprints do not drill those holes.
    """
    if part not in ("M80-5001642", "M80-5002042", "M80-5T10442MC"):
        return []
    fixing, fix_x, fix_w = M80_PARTS[part][8:11]
    half = fix_w / 2.0 + 0.50
    label = "M2 LOCK" if fixing == "jackscrew" else "101LOK"
    graphics = []
    for side, x in (("left", -fix_x), ("right", fix_x)):
        prefix = f"lock-guide-{side}"
        graphics += rect_outline(name, prefix, x - half, -half, x + half, half,
                                 "Dwgs.User", 0.15)
        graphics.append(fp_line(name, f"{prefix}-axis-x", (x - 0.45, 0),
                                (x + 0.45, 0), "Dwgs.User", 0.1))
        graphics.append(fp_line(name, f"{prefix}-axis-y", (x, -0.45),
                                (x, 0.45), "Dwgs.User", 0.1))
        for suffix, text, y in (("type", label, -1.25),
                                ("clearance", "NO COPPER", 1.25)):
            graphics.append(
                f'\t(fp_text user "{text}" (at {x:g} {y:g} 0) (layer "Dwgs.User")\n'
                f'\t\t(uuid "{uid(name, prefix + "-" + suffix)}") '
                f'{effects(0.4, 0.08)})'
            )
    return graphics


def datamate_m80_footprint(part: str) -> tuple[str, str]:
    """Return (name, footprint text) for a Harwin Datamate M80 vertical header."""
    (contacts, rows, overall_x, body_y0, body_y1, above, tail,
     family, fixing, fix_x, fix_w) = M80_PARTS[part]
    per_row = contacts // rows
    span = (per_row - 1) * M80_PITCH
    half = overall_x / 2.0
    row_ys = [M80_ROW_SPACING / 2.0, -M80_ROW_SPACING / 2.0] if rows == 2 else [0.0]
    layout = f"{rows}x{per_row:02d}" if rows == 2 else f"1x{per_row:02d}"
    name = f"Harwin_Datamate_{part}_{layout}_P2.00mm_Vertical"

    cols = [-span / 2.0 + i * M80_PITCH for i in range(per_row)]

    graphics = rect_outline(name, "fab", -half, body_y0, half, body_y1, "F.Fab", 0.1)
    graphics.append(fp_line(name, "fab-pin1", (-half, body_y1 - 1.0),
                            (-half + 1.0, body_y1), "F.Fab", 0.1))
    graphics += rect_outline(name, "silk", -(half + 0.11), body_y0 - 0.11,
                             half + 0.11, body_y1 + 0.11, "F.SilkS", 0.12)
    graphics.append(fp_line(name, "silk-pin1", (-(half + 0.11), body_y1 + 0.61),
                            (-(half + 0.11) + 1.4, body_y1 + 0.61), "F.SilkS", 0.12))
    graphics += courtyard(name, -(half + 0.5), body_y0 - 0.5, half + 0.5, body_y1 + 0.5)
    graphics += datamate_m80_lock_graphics(name, part)

    pads = []
    number = 1
    for y in row_ys:
        for i, x in enumerate(cols):
            pads.append(pth_pad_shaped(
                name, f"pad-{number}", str(number), x, y, M80_PAD, M80_PAD, M80_HOLE,
                "rect" if number == 1 else "circle"))
            number += 1

    fixing_text = {
        "jackscrew": f"M2 internal-thread jackscrews at x +/-{fix_x:.2f}mm",
        "101-Lok": f"101-Lok retainers at x +/-{fix_x:.2f}mm",
        "latch": f"locking latches at x +/-{fix_x:.2f}mm",
    }[fixing]
    description = (
        f"Harwin Datamate {family} {part}, {contacts} contacts "
        f"({'%d+%d' % (per_row, per_row) if rows == 2 else str(contacts)}), 2.00mm pitch, "
        f"{'DIL dual' if rows == 2 else 'SIL single'} row male vertical throughboard connector, "
        "3.3A per contact, 800V working, 25mOhm max, 500 mating cycles, -55 to +125C, "
        "100G shock, low outgassing. Contact holes 0.90mm on a 2.00mm pitch"
        + (f" with {M80_ROW_SPACING:.2f}mm row spacing" if rows == 2 else "")
        + f"; body {overall_x:.2f}mm long, {above:.2f}mm above the PCB, {tail:.2f}mm PC tails. "
        f"{fixing_text}, all above the seating plane, so no mounting holes are required. "
        "Contact numbering is row-wise per C005XX Appendix 1; those diagrams look onto the "
        "male contact face and so mirror in PCB top view - confirm which row carries contact 1 "
        "against the polarising key before wiring"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        attr="through_hole",
        model_name=f"Harwin_Datamate_{part}",
        reference_at=f"0 {body_y0 - 1.4:g} 0",
        value_at=f"0 {body_y1 + 1.4:g} 0",
        tag_name=f"harwin datamate m80 {family.lower()} 2.00mm connector tht vertical",
    )


# Schurter USF 1206 surface mount fuse, from datasheet typ_USF_1206. Body is
# 3.2 x 1.6 x 0.6 mm with a 2.2 mm gap between the end metallisations, so each
# terminal is 0.5 mm long.
#
# The "Reflow soldering pads" figure prints 1.5, 1.1 and 2, and the assignment
# was resolved by measuring the drawn rectangles on page 2 of the datasheet:
# the two pads sit at cx 390.2 and 417.3 drawing units, each 10.875 wide and
# 21.220 tall, so gap / pad length = (27.1 - 10.875) / 10.875 = 1.49. The gap
# is therefore the LARGER number. Calibrating on the 2.00 mm pad width gives
# 10.61 units/mm, i.e. pad length 1.03 and gap 1.53 - which rounds to the
# printed 1.1 and 1.5.
#
# So: pads 1.10 mm long x 2.00 mm wide on a 1.50 mm gap, 3.70 mm overall span.
# Each pad runs 0.75 to 1.85 mm off centre against a terminal that runs 1.10 to
# 1.60, giving 0.35 mm of fillet inboard and 0.25 mm outboard. This matters for
# a fuse specifically: pad area sets how much heat the land sinks away from the
# element, so an oversized pad shifts the time-current curve.
USF1206_BODY_X = 3.20
USF1206_BODY_Y = 1.60
USF1206_PAD_X = 1.10
USF1206_PAD_Y = 2.00
USF1206_PAD_GAP = 1.50


def schurter_1206_fuse_footprint(series: str) -> tuple[str, str]:
    """Return (name, footprint text) for a Schurter 1206 chip fuse.

    USF 1206 and MGA-A share one reflow land pattern - both datasheets give the
    same 1.1 / 1.5 / 2.0 figure - so a USF to MGA-A change is a BOM swap with no
    layout work. They are emitted as two footprints only so each carries its own
    datasheet, description and 3D model; the geometry below is generated once.
    """
    if series == "USF":
        name = "Schurter_USF-1206_Fuse_3.2x1.6mm"
        model = "Schurter_USF-1206_Fuse"
        description = (
            "Schurter USF 1206 surface mount fuse, 3.2 x 1.6 x 0.6mm, super-quick-acting FF, "
            "32-125 VAC / 63-125 VDC, 0.375-4A, 50A breaking capacity, -55 to +90C, "
            "fibre-reinforced housing UL94V-0, Ni/Au-plated copper terminals. Manufacturer "
            "reflow land pattern: 1.10 x 2.00mm pads on a 1.50mm gap. Series land pattern - "
            "the rating is set by the order number, e.g. 3413.0113.22 for 500mA at 125VDC"
        )
        tag = "schurter usf 1206 fuse smd"
    else:
        name = "Schurter_MGA-A_Fuse_3.2x1.6mm"
        model = "Schurter_MGA-A_Fuse"
        description = (
            "Schurter MGA-A COTS+ aviation surface mount fuse, 1206, super-quick-acting FF, "
            "125 VAC / 125 VDC across the whole 0.2-5A range, breaking capacity to 300A at "
            "125VDC, -55 to +125C, climatic category 55/125/56, hermetically sealed ceramic "
            "body with gold-plated nickel terminals, lead-free with no tin whiskers or "
            "dendrites, qualification similar to MIL-PRF-23419, ESA ESCC 4008 thermal vacuum, "
            "100G shock, 20G vibration, operational time 2000h at 0.63 x In at 125C. Shares "
            "the USF 1206 reflow land pattern (1.10 x 2.00mm pads on a 1.50mm gap), so it is "
            "a drop-in swap. Rating set by order number, e.g. 3-103-097 for 500mA"
        )
        tag = "schurter mga-a 1206 fuse smd aviation cots"

    pad_x = (USF1206_PAD_GAP + USF1206_PAD_X) / 2.0
    half_x = pad_x + USF1206_PAD_X / 2.0
    half_y = USF1206_PAD_Y / 2.0

    graphics = rect_outline(name, "fab", -USF1206_BODY_X / 2.0, -USF1206_BODY_Y / 2.0,
                            USF1206_BODY_X / 2.0, USF1206_BODY_Y / 2.0, "F.Fab", 0.1)
    graphics += [
        fp_line(name, "silk-top", (-USF1206_BODY_X / 2.0, -half_y - 0.21),
                (USF1206_BODY_X / 2.0, -half_y - 0.21), "F.SilkS", 0.12),
        fp_line(name, "silk-bot", (-USF1206_BODY_X / 2.0, half_y + 0.21),
                (USF1206_BODY_X / 2.0, half_y + 0.21), "F.SilkS", 0.12),
    ]
    graphics += courtyard(name, -(half_x + 0.25), -(half_y + 0.25),
                          half_x + 0.25, half_y + 0.25)

    pads = [
        smd_pad(name, "pad-1", "1", -pad_x, 0.0, USF1206_PAD_X, USF1206_PAD_Y, "roundrect"),
        smd_pad(name, "pad-2", "2", pad_x, 0.0, USF1206_PAD_X, USF1206_PAD_Y, "roundrect"),
    ]
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        model_name=model,
        reference_at="0 -2.3 0", value_at="0 2.3 0",
        tag_name=tag,
    )


# Littelfuse SZSMFxxA 200W TVS in SOD-123FL, from the SZSMFxxA datasheet
# (rev 10/25/24). Package: E 2.70 body length, D 1.65 body width, A 0.95
# height, HE 3.60 overall lead span, b 0.90 lead width, L 0.75 foot, c 0.15
# lead thickness.
#
# The Soldering Footprint figure on page 5 prints 1.6 (0.062), 1.3 (0.051) and
# 1.4 (0.055). The assignment follows from the package table on the same page:
# lead width b is 0.70/0.90/1.10 and foot length L is 0.55/0.75/0.95 on an
# HE 3.40/3.60/3.80 span, so the feet run about 1.15 to 1.90 mm off centre.
#   gap  1.60 -> pads start 0.80 off centre, just inboard of the toe at 0.75
#   pad  1.40 long  -> 0.80 to 2.20, so 0.35 inboard and 0.30 outboard fillet
#   pad  1.30 wide  -> 0.10 side fillet on the 1.10 max lead width
# No other assignment of the three numbers fits the feet. This also matches the
# published onsemi SOD-123FL land, which is the lineage of the SZ-prefix parts.
# Overall span 4.40 mm on 3.00 mm centres.
#
# An earlier revision of this file used 1.10 x 1.20 pads on a 1.70 gap, derived
# by measuring the drawn figure and calibrating against a generic SOD-123FL
# land. That scaling was wrong and the pads came out undersized.
SOD123FL_BODY_X = 2.70
SOD123FL_BODY_Y = 1.65
SOD123FL_PAD_X = 1.40
SOD123FL_PAD_Y = 1.30
SOD123FL_PITCH = 3.00


def szsmf_sod123fl_footprint() -> tuple[str, str]:
    """Return (name, footprint text) for the Littelfuse SZSMFxxA SOD-123FL TVS."""
    name = "Littelfuse_SZSMFxxA_SOD-123FL"
    pad_x = SOD123FL_PITCH / 2.0
    half_x = pad_x + SOD123FL_PAD_X / 2.0
    half_y = SOD123FL_PAD_Y / 2.0
    bx, by = SOD123FL_BODY_X / 2.0, SOD123FL_BODY_Y / 2.0

    graphics = rect_outline(name, "fab", -bx, -by, bx, by, "F.Fab", 0.1)
    # cathode bar on pin 1 (the datasheet marks pin 1 cathode, pin 2 anode)
    graphics.append(fp_line(name, "fab-cathode", (-bx + 0.45, -by),
                            (-bx + 0.45, by), "F.Fab", 0.1))
    graphics += [
        fp_line(name, "silk-top", (-bx, -half_y - 0.21), (bx, -half_y - 0.21), "F.SilkS", 0.12),
        fp_line(name, "silk-bot", (-bx, half_y + 0.21), (bx, half_y + 0.21), "F.SilkS", 0.12),
        fp_line(name, "silk-cathode", (-half_x - 0.3, -half_y - 0.21),
                (-half_x - 0.3, half_y + 0.21), "F.SilkS", 0.12),
    ]
    graphics += courtyard(name, -(half_x + 0.25), -(half_y + 0.25),
                          half_x + 0.25, half_y + 0.25)

    pads = [
        smd_pad(name, "pad-1", "1", -pad_x, 0.0, SOD123FL_PAD_X, SOD123FL_PAD_Y, "roundrect"),
        smd_pad(name, "pad-2", "2", pad_x, 0.0, SOD123FL_PAD_X, SOD123FL_PAD_Y, "roundrect"),
    ]
    description = (
        "Littelfuse SZSMFxxA 200W unidirectional TVS, SOD-123FL, 2.70 x 1.65 x 0.95mm, "
        "AEC-Q101, -55 to +150C TJ. Pin 1 = cathode, pin 2 = anode. Series land pattern - the "
        "standoff is set by the order number, e.g. SZSMF10AT1G for 10V standoff, 11.1V VBR, "
        "17V VC, 2.5uA reverse leakage at VRWM"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        model_name="Littelfuse_SZSMFxxA_SOD-123FL",
        reference_at="0 -1.8 0", value_at="0 1.8 0",
        tag_name="littelfuse szsmf tvs sod-123fl diode",
    )


# Littelfuse 470 Series thin-film chip fuse, 1206, from the 470 datasheet.
# Package outline 3.302 x 1.575 x 1.168 mm (drawing maxima; Digi-Key quotes
# 3.15 x 1.50 x 1.15 nominal). The Recommended Pad Layout figure gives 3.65,
# 2.05, 1.185 and 1.28, which resolve unambiguously because the pad, gap and
# pad add back to the span: 1.185 + 1.28 + 1.185 = 3.65.
#
# Note this is NOT the Schurter 1206 land: Littelfuse specify shorter pads on a
# wider gap (1.185/1.28 vs 1.50/1.10), so the two are not interchangeable
# without a layout change. Pad size sets how much heat the land sinks away from
# a fuse element, so the manufacturer land is the one the ratings assume.
LF470_BODY_X = 3.302
LF470_BODY_Y = 1.575
LF470_PAD_X = 1.185
LF470_PAD_Y = 2.05
LF470_PAD_GAP = 1.28


# Bourns SMBJ-Q series TVS in DO-214AA (SMB). Package dimensions from the Vishay
# SMB outline drawing (document 95401), which is the JEDEC DO-214AA registered
# outline and matches the Bourns/Littelfuse/onsemi package:
#   body 4.06-4.57 x 3.30-3.94, height 1.95-2.20, standoff 0-0.20,
#   overall lead span 5.21-5.59, foot 0.76-1.52 long x 2.13-2.44 wide,
#   terminal thickness 0.152-0.305.
# Vishay's Mounting Pad Layout gives four numbers: gap 2.159 MAX, pad length
# 1.52 MIN, pad width 2.18 MIN, span 5.59 REF.
#
# The pads here are deliberately LARGER than those minima (2.20 x 2.60 on a
# 2.16 gap, 6.56 span). An SMB TVS is rated 5.0W steady state only at TL = 75C,
# and Vishay's own note is that the rating assumes 5.0 x 5.0mm copper to each
# terminal. The larger lands provide additional heat-spreading area; sustained
# clamp performance still depends on the circuit and thermal design.
# Toe fillet is (6.56 - 5.59)/2 = 0.485mm per end.
SMB_BODY_X = 4.57
SMB_BODY_Y = 3.94
SMB_PAD_X = 2.20
SMB_PAD_Y = 2.60
SMB_PAD_GAP = 2.16


def smb_do214aa_footprint() -> tuple[str, str]:
    """Return (name, footprint text) for the DO-214AA (SMB) TVS land."""
    name = "Bourns_SMBJ-Q_DO-214AA"
    pad_x = (SMB_PAD_GAP + SMB_PAD_X) / 2.0
    half_x = pad_x + SMB_PAD_X / 2.0
    half_y = SMB_PAD_Y / 2.0
    bx, by = SMB_BODY_X / 2.0, SMB_BODY_Y / 2.0

    graphics = rect_outline(name, "fab", -bx, -by, bx, by, "F.Fab", 0.1)
    # cathode band inside the body outline, at the pin 1 end
    graphics.append(fp_line(name, "fab-cathode", (-bx + 0.85, -by),
                            (-bx + 0.85, by), "F.Fab", 0.1))
    # body edges in Y sit outside the pads, so the silk can run the full length
    graphics += [
        fp_line(name, "silk-top", (-bx, -by), (bx, -by), "F.SilkS", 0.12),
        fp_line(name, "silk-bot", (-bx, by), (bx, by), "F.SilkS", 0.12),
        fp_line(name, "silk-cathode", (-half_x - 0.22, -by),
                (-half_x - 0.22, by), "F.SilkS", 0.12),
    ]
    graphics += courtyard(name, -(half_x + 0.47), -(by + 0.25),
                          half_x + 0.25, by + 0.25)

    pads = [
        smd_pad(name, "pad-1", "1", -pad_x, 0.0, SMB_PAD_X, SMB_PAD_Y, "roundrect"),
        smd_pad(name, "pad-2", "2", pad_x, 0.0, SMB_PAD_X, SMB_PAD_Y, "roundrect"),
    ]
    description = (
        "Bourns SMBJ-Q 600W unidirectional TVS, DO-214AA (SMB), 4.57 x 3.94 x 2.20mm, "
        "AEC-Q101, -55 to +150C TJ. Pin 1 = cathode, pin 2 = anode. Series land pattern - "
        "the standoff is set by the order number, e.g. SMBJ12A-Q for 12V standoff, 13.3V "
        "VBR min, 19.9V VC at 30.2A. Pads are oversized against the datasheet minima for "
        "heat sinking; the 5.0W steady-state rating assumes large copper at each terminal"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        model_name="Bourns_SMBJ-Q_DO-214AA",
        reference_at="0 -3.1 0", value_at="0 3.1 0",
        tag_name="bourns smbj tvs do-214aa smb diode",
    )


# Vishay RCL1225 e3 long-side-termination thick film resistor, from datasheet
# document 20046 rev 20-Oct-2025.
#
# RCL is a REVERSE GEOMETRY part: the terminations run along the 6.3 mm side,
# not the 3.2 mm side. That short, wide current path is what lets a chip this
# size carry 2 W, and it means the land is wide in Y and short in X - the
# opposite proportion to an ordinary chip resistor.
#
#   Body      L 3.2 +/-0.20, W 6.3 +/-0.20, H 0.70 +/-0.10, mass 55 mg
#   Reflow    G 1.20 gap, Y 1.60 pad length, X 6.60 pad width, Z 4.40 span
#             self-consistent: Z = G + 2Y = 1.20 + 3.20 = 4.40
#
# Note W is 6.3, not the 6.4 the metric code 3264 implies.
#
# This deliberately does NOT match KiCad's Resistor_SMD:R_1225_3264Metric, whose
# own descr says "IPC-7351 nominal, body size source koaspeer.com/pdfs/WK73S.pdf"
# - a generic 1225 rather than this part. That land is 1.30 x 6.45 on a 1.35 gap,
# giving 8.39 mm2 per pad against Vishay's 10.56 mm2, 21% less. For a 2 W part
# that sheds its heat through the terminations, pad area is the rating, so the
# manufacturer land is the one to build to. KiCad also ships no 3D model for
# 1225 at all.
RCL1225_BODY_X = 3.20
RCL1225_BODY_Y = 6.30
RCL1225_PAD_X = 1.60
RCL1225_PAD_Y = 6.60
RCL1225_PAD_GAP = 1.20


def vishay_rcl1225_footprint() -> tuple[str, str]:
    """Return (name, footprint text) for the Vishay RCL1225 2W resistor."""
    name = "Vishay_RCL1225_2W_3.2x6.3mm"
    pad_x = (RCL1225_PAD_GAP + RCL1225_PAD_X) / 2.0
    half_x = pad_x + RCL1225_PAD_X / 2.0
    half_y = RCL1225_PAD_Y / 2.0
    bx, by = RCL1225_BODY_X / 2.0, RCL1225_BODY_Y / 2.0

    graphics = rect_outline(name, "fab", -bx, -by, bx, by, "F.Fab", 0.1)
    # The pads are wider than the body in both axes, so the only clear silk is
    # beyond the pads in Y. Draw two rules the width of the body.
    graphics += [
        fp_line(name, "silk-top", (-bx, -half_y - 0.21), (bx, -half_y - 0.21),
                "F.SilkS", 0.12),
        fp_line(name, "silk-bot", (-bx, half_y + 0.21), (bx, half_y + 0.21),
                "F.SilkS", 0.12),
    ]
    graphics += courtyard(name, -(half_x + 0.25), -(half_y + 0.25),
                          half_x + 0.25, half_y + 0.25)

    pads = [
        smd_pad(name, "pad-1", "1", -pad_x, 0.0,
                RCL1225_PAD_X, RCL1225_PAD_Y, "roundrect"),
        smd_pad(name, "pad-2", "2", pad_x, 0.0,
                RCL1225_PAD_X, RCL1225_PAD_Y, "roundrect"),
    ]
    description = (
        "Vishay RCL1225 e3 long-side-termination thick film chip resistor, 2W, "
        "3.2 x 6.3 x 0.70mm. Reverse geometry - the terminations run along the "
        "6.3mm side, which is what allows 2W in this size. Manufacturer reflow "
        "land: 1.60 x 6.60mm pads on a 1.20mm gap, 4.40mm span. This is NOT "
        "KiCad's R_1225_3264Metric, which is a generic IPC-7351 1225 with 21% "
        "less pad area and no 3D model; for a part rated on conduction through "
        "its terminations the manufacturer land is the one the rating assumes. "
        "Series land pattern - the value is set by the order number, e.g. "
        "RCL122520R0FKEG for 20R 1%"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        model_name="Vishay_RCL1225_2W",
        reference_at="0 -4.2 0", value_at="0 4.2 0",
        tag_name="vishay rcl1225 resistor 2w reverse geometry long side termination",
    )


def littelfuse_470_footprint() -> tuple[str, str]:
    """Return (name, footprint text) for the Littelfuse 470 Series 1206 chip fuse."""
    name = "Littelfuse_470-Series_Fuse_1206"
    pad_x = (LF470_PAD_GAP + LF470_PAD_X) / 2.0
    half_x = pad_x + LF470_PAD_X / 2.0
    half_y = LF470_PAD_Y / 2.0

    graphics = rect_outline(name, "fab", -LF470_BODY_X / 2.0, -LF470_BODY_Y / 2.0,
                            LF470_BODY_X / 2.0, LF470_BODY_Y / 2.0, "F.Fab", 0.1)
    graphics += [
        fp_line(name, "silk-top", (-LF470_BODY_X / 2.0, -half_y - 0.21),
                (LF470_BODY_X / 2.0, -half_y - 0.21), "F.SilkS", 0.12),
        fp_line(name, "silk-bot", (-LF470_BODY_X / 2.0, half_y + 0.21),
                (LF470_BODY_X / 2.0, half_y + 0.21), "F.SilkS", 0.12),
    ]
    graphics += courtyard(name, -(half_x + 0.25), -(half_y + 0.25),
                          half_x + 0.25, half_y + 0.25)

    pads = [
        smd_pad(name, "pad-1", "1", -pad_x, 0.0, LF470_PAD_X, LF470_PAD_Y, "roundrect"),
        smd_pad(name, "pad-2", "2", pad_x, 0.0, LF470_PAD_X, LF470_PAD_Y, "roundrect"),
    ]
    description = (
        "Littelfuse 470 Series thin-film chip fuse, 1206, 3.302 x 1.575 x 1.168mm, fast acting, "
        "125V AC and 125V DC, interrupting 50A at 125VDC / 50A at 125VAC / 300A at 32VDC, "
        "-55 to +125C, epoxy resin body with Cu/Ni/Sn terminations, Pb-free and halogen-free. "
        "Manufacturer recommended land: 1.185 x 2.05mm pads on a 1.28mm gap, 3.65mm overall. "
        "Series land pattern - the rating is set by the order number, e.g. 0470.500DRSNP for "
        "500mA with 0.5455 Ohm cold resistance and 0.0287 A2s nominal melting I2t"
    )
    return name, footprint(
        name, description, DATASHEET_URLS[name], graphics, pads,
        model_name="Littelfuse_470-Series_Fuse",
        reference_at="0 -2.3 0", value_at="0 2.3 0",
        tag_name="littelfuse 470 nano2 thin film chip fuse 1206 smd",
    )


def bourns_sod323_compact_footprint() -> tuple[str, str]:
    """Original voltage-independent CDSOD323-TxxC compact assembly variant.

    Bourns' package drawing gives body A=1.60..1.90, B=1.15..1.45 mm,
    overall lead span C=2.39..2.70 mm and lead width E=0.25..0.40 mm.
    Use a representative 1.80 x 1.40 mm body drawing. The separately chosen
    compact lands (0.60 x 0.45 mm at +/-1.05 mm, radius 0.1125 mm) preserve
    the existing compact land geometry. They are NOT the Bourns recommended
    0.80 x 0.50 mm lands with a 1.40 mm inner gap (+/-1.10 mm centres).
    All artwork and deterministic IDs below are authored here; no stock CAD
    blocks or IDs are imported. The fabrication end stripe denotes pad one,
    not a cathode requirement for this bidirectional family.
    """
    name = "Bourns_CDSOD323-TxxC_SOD-323_Compact"
    graphics = rect_outline(name, "fab-body", -0.90, -0.70, 0.90, 0.70, "F.Fab", 0.10)
    graphics.append(fp_line(name, "fab-pad-one", (-0.60, -0.70), (-0.60, 0.70), "F.Fab", 0.10))
    # Body maximum half-width 0.725 + 0.15 clearance = 0.875 mm.
    # Pad-one end line is 0.25 mm outside the compact copper extent.
    graphics += [
        fp_line(name, "silk-upper", (-1.60, -0.875), (0.95, -0.875), "F.SilkS", 0.12),
        fp_line(name, "silk-lower", (-1.60, 0.875), (0.95, 0.875), "F.SilkS", 0.12),
        fp_line(name, "silk-pad-one", (-1.60, -0.875), (-1.60, 0.875), "F.SilkS", 0.12),
        *courtyard(name, -1.60, -0.95, 1.60, 0.95),
    ]
    pads = [
        smd_pad(name, f"pad-{number}", str(number), x, 0, 0.60, 0.45,
                roundrect_rratio=0.25)
        for number, x in ((1, -1.05), (2, 1.05))
    ]
    return name, footprint(
        name,
        "Bourns CDSOD323-TxxC bidirectional TVS family; original compact SOD-323 variant, "
        "0.60x0.45mm lands at 2.10mm pitch; not the manufacturer recommended land pattern",
        DATASHEET_URLS[name], graphics, pads,
        model_name="Bourns_CDSOD323-TxxC_SOD-323",
        reference_at="0 -1.7 0", value_at="0 1.7 0",
        tag_name="Bourns CDSOD323 bidirectional TVS SOD-323 compact",
    )


MINIMAL_SILK_BASES = (
    "Harwin_Datamate_M80-5001642_2x08_P2.00mm_Vertical",
    "Harwin_Datamate_M80-5T10442MC_2x02_P2.00mm_Vertical",
    "L_Wuerth_WE-PD-Robust-7332",
    "LTC3639_MSE16-12",
    "Bourns_CDSOD323-TxxC_SOD-323_Compact",
)

# Numeric land/body/courtyard definitions, independently parameterized with
# explicit land geometry. These are generic land options, not a claim
# that every manufacturer recommends the same lands for a given chip size.
# (body half-x/y, courtyard half-x/y, pad centre x, pad width/height, corner ratio)
MINIMAL_PASSIVES = {
    "R_0603_1608Metric_NoSilkscreenBody": (0.8, 0.4125, 1.48, 0.73, 0.825, 0.8, 0.95, 0.25),
    "C_0603_1608Metric_NoSilkscreenBody": (0.8, 0.4, 1.48, 0.73, 0.775, 0.9, 0.95, 0.25),
    "C_0805_2012Metric_NoSilkscreenBody": (1.0, 0.625, 1.7, 0.98, 0.95, 1.0, 1.45, 0.25),
    "C_1206_3216Metric_OneSideSilkscreen": (1.6, 0.8, 2.3, 1.15, 1.475, 1.15, 1.8, 0.217391),
}


def generate_minimal_silkscreen_footprints(bases: dict[str, str]) -> dict[str, str]:
    """Reusable sparse artwork; no board coordinates or via cutouts are stored.

    Existing original packages retain their complete non-silk geometry. Chip
    passives are drawn afresh from the numeric definitions above, not imported
    CAD. Their optional external KiCad model links provide standard package
    visualization; no third-party model is redistributed.
    """
    result = {}
    for base in MINIMAL_SILK_BASES:
        name = base + "_MinimalSilkscreen"
        source = bases[base]
        edits = []
        for a, z, block in children(source):
            if not block.startswith('(fp_line ') or layer_of(block) != 'F.SilkS':
                continue
            start = tuple(map(float, re.search(r'\(start ([^()]+)\)', block).group(1).split()))
            end = tuple(map(float, re.search(r'\(end ([^()]+)\)', block).group(1).split()))
            width = float(re.search(r'\(width ([^()]+)\)', block).group(1))
            segments = [(start, end)]
            if base.startswith('Harwin_') and start[1] == end[1] and abs(end[0] - start[0]) > 10:
                # Half-millimetre corner arms on each long body side. Leave
                # the end walls, pin-one mark and lock guides unchanged.
                left, right = sorted((start[0], end[0]))
                y = start[1]
                segments = [((left, y), (left + 0.5, y)), ((right - 0.5, y), (right, y))]
            elif base == 'L_Wuerth_WE-PD-Robust-7332' and start[1] == end[1] == 3.8:
                segments = [((-3.8, 3.8), (-2.1, 3.8)), ((2.1, 3.8), (3.8, 3.8))]
            elif base == 'LTC3639_MSE16-12' and start[1] == end[1] == -2.13:
                segments = [((-1.5, -2.13), (-0.75, -2.13)), ((0.75, -2.13), (1.5, -2.13))]
            elif base == 'Bourns_CDSOD323-TxxC_SOD-323_Compact':
                # A central pad-one end tick, not a cathode mark: the TVS
                # family is bidirectional. Keep the full body on F.Fab.
                segments = [((-1.6, -0.2), (-1.6, 0.2))] if start[0] == end[0] == -1.6 else []
            if segments != [(start, end)]:
                replacement = '\n'.join(fp_line(name, f'minimal-{a}-{i}', p, q, 'F.SilkS', width).lstrip()
                                        for i, (p, q) in enumerate(segments))
                edits.append((a, z, replacement))
        for a, z, replacement in sorted(edits, reverse=True):
            source = source[:a] + replacement + source[z:]
        source = source.replace(f'(footprint "{base}"', f'(footprint "{name}"', 1)
        source = source.replace(f'(property "Value" "{base}"', f'(property "Value" "{name}"', 1)
        source = re.sub(r'\(descr "([^"]*)"\)', lambda m: '(descr "' + m.group(1) + '; minimal silkscreen variant")', source, count=1)
        source = re.sub(r'\(uuid "([^"]+)"\)', lambda m: '(uuid "' + uid(name, m.group(1)) + '")', source)
        result[name] = source

    for name, dimensions in MINIMAL_PASSIVES.items():
        bx, by, cx, cy, px, sx, sy, ratio = dimensions
        # Rectangles express generic physical dimensions without inheriting
        # another library's graphic blocks, identifiers, or metadata.
        def rectangle(label: str, hx: float, hy: float, layer: str, width: float) -> str:
            return (f'\t(fp_rect (start {-hx:g} {-hy:g}) (end {hx:g} {hy:g})\n'
                    f'\t\t(stroke (width {width:g}) (type solid)) (fill none) (layer "{layer}")\n'
                    f'\t\t(uuid "{uid(name, label)}"))')
        graphics = [rectangle('fab-body', bx, by, 'F.Fab', 0.1),
                    rectangle('courtyard', cx, cy, 'F.CrtYd', 0.05)]
        if name.endswith('_OneSideSilkscreen'):
            graphics.append(fp_line(name, 'single-side', (-0.7, 0.91), (0.7, 0.91), 'F.SilkS', 0.12))
        pads = [smd_pad(name, 'pad-' + str(n), str(n), x, 0, sx, sy, roundrect_rratio=ratio)
                for n, x in [(1, -px), (2, px)]]
        desc = 'Generic chip land pattern with sparse silkscreen; verify land suitability for the selected component and assembly process'
        content = footprint(name, desc, '', graphics, pads,
                            reference_at=f'0 {-cy - 0.8:g} 0', value_at=f'0 {cy + 0.8:g} 0')
        package = name.rsplit('_', 1)[0]
        category = 'Resistor_SMD' if name.startswith('R_') else 'Capacitor_SMD'
        content = content.replace(
            f'${{KIPRJMOD}}/kicad-libraries/3d_models/custom_3dmodels.3dshapes/{name}.step',
            f'${{KICAD10_3DMODEL_DIR}}/{category}.3dshapes/{package}.step')
        result[name] = content
    return result


def generate_connector_footprints() -> dict[str, str]:
    """Cell-tap and daisy-chain connector footprints."""
    generated: dict[str, str] = {}
    for circuits in (6, 20):
        name, text = gecko_footprint(circuits)
        generated[name] = text
    name, text = jst_xh_footprint(20)
    generated[name] = text
    for circuits in (16, 20):
        name, text = mini50_footprint(circuits)
        generated[name] = text
    name, text = mini50_single_row_footprint(4)
    generated[name] = text
    for part in M80_PARTS:
        name, text = datamate_m80_footprint(part)
        generated[name] = text
    for series in ("USF", "MGA-A"):
        name, text = schurter_1206_fuse_footprint(series)
        generated[name] = text
    name, text = vishay_rcl1225_footprint()
    generated[name] = text
    name, text = littelfuse_470_footprint()
    generated[name] = text
    name, text = smb_do214aa_footprint()
    generated[name] = text
    name, text = szsmf_sod123fl_footprint()
    generated[name] = text
    name, text = bourns_sod323_compact_footprint()
    generated[name] = text
    return generated


Pin = tuple[str, str, str, float, float, int]

GRID_NORMALIZED_SYMBOLS = {
    "+8V8",
    "7460305",
    "ACS781LLRTR-100U-T",
    "BVN-M-R001-1.0",
    "BQ79600-Q1",
    "BQ79606A-Q1",
    "BQ79616-Q1",
    "INA286",
    "STB45N65M5",
    "CSS2H-3920R-L200F",
    "1N6263W-7-F",
    "D_ALT-Device",
    "INA190A3IDDFR",
    "IRS2186(4)(S)PBF",
    "LFXTAL016178REEL",
    "L_Wuerth_WE-PD-Robust-7332",
    "LTC3639",
    "LM2576HVS-ADJ_NOPB_NOPB_TO_263_TAB3GND",
    "LM2596SX-5.0_NOPB",
    "NCS213RSQT2G",
    "SM91502AL",
}


def sym_effects(hidden: bool = False, justify: str | None = None) -> str:
    justification = f" (justify {justify})" if justify else ""
    hide = " (hide yes)" if hidden else ""
    return f'(effects (font (size 1.27 1.27)){justification}{hide})'


def sym_property(name: str, value: str, x: float, y: float, hidden: bool = False,
                 justify: str | None = None) -> str:
    return f'\t\t(property "{name}" "{value}" (at {x:g} {y:g} 0) {sym_effects(hidden, justify)})'


def pin(pin_type: str, name: str, number: str, x: float, y: float, angle: int,
        length: float = 2.54) -> str:
    return (
        f'\t\t\t(pin {pin_type} line (at {x:g} {y:g} {angle}) (length {length:g})\n'
        f'\t\t\t\t(name "{name}" {sym_effects()})\n'
        f'\t\t\t\t(number "{number}" {sym_effects()}))'
    )


def symbol(name: str, reference: str, footprint_name: str, datasheet: str, description: str,
           pins: Sequence[Pin], body: tuple[float, float] = (6.35, 6.35), extra_graphics: Sequence[str] = (),
           property_positions: tuple[float, float] | None = None,
           visible_property_positions: tuple[tuple[float, float], tuple[float, float]] | None = None,
           visible_property_justifications: tuple[str | None, str | None] | None = None,
           pin_length: float = 2.54,
           body_bounds: tuple[float, float, float, float] | None = None) -> str:
    hx, hy = body
    left, top, right, bottom = body_bounds or (-hx, hy, hx, -hy)
    if visible_property_positions is None:
        reference_x = value_x = 0
        reference_y, value_y = property_positions or (hy + 3.81, hy + 2.54)
    else:
        (reference_x, reference_y), (value_x, value_y) = visible_property_positions
    reference_justify, value_justify = visible_property_justifications or (None, None)
    footprint_value = (
        footprint_name if ":" in footprint_name
        else f"custom_footprints:{footprint_name}" if footprint_name
        else ""
    )
    source = datasheet or "Original generic electrical convention"
    lines = [
        f'\t(symbol "{name}"',
        '\t\t(pin_names (offset 0.508))',
        '\t\t(exclude_from_sim no)',
        '\t\t(in_bom yes)',
        '\t\t(on_board yes)',
        sym_property("Reference", reference, reference_x, reference_y, justify=reference_justify),
        sym_property("Value", name, value_x, value_y, justify=value_justify),
        sym_property("Footprint", footprint_value, 0, 0, True),
        sym_property("Datasheet", datasheet, 0, 0, True),
        sym_property("Description", description, 0, 0, True),
        f'\t\t(symbol "{name}_1_1"',
        f'\t\t\t(rectangle (start {left:g} {top:g}) (end {right:g} {bottom:g}) '
        f'(stroke (width 0.254) (type default)) (fill (type background)))',
        *extra_graphics,
        *(pin(*p, length=pin_length) for p in pins),
        '\t\t)',
        '\t)',
    ]
    return "\n".join(lines)


def power_symbol(name: str, description: str) -> str:
    """Original power-flag symbol drawn from ordinary schematic convention.

    A 2.54 mm stem rising from the connection point with a chevron at the top -
    the shape every schematic uses for a supply rail, so these read the same as
    any other power symbol on the sheet.  The chevron is drawn at +/-1.27 mm
    rather than a finer offset so that every graphic point, the pin anchor and
    the visible Value origin all land on the 50 mil grid this library enforces.
    """
    return "\n".join([
        f'\t(symbol "{name}"',
        '\t\t(power)',
        '\t\t(pin_numbers (hide yes))',
        '\t\t(pin_names (offset 0) (hide yes))',
        '\t\t(exclude_from_sim no)',
        '\t\t(in_bom no)',
        '\t\t(on_board no)',
        sym_property("Reference", "#PWR", 0, -3.81, True),
        sym_property("Value", name, 0, 3.81),
        sym_property("Footprint", "", 0, 0, True),
        sym_property("Datasheet", "", 0, 0, True),
        sym_property("Description", description, 0, 0, True),
        f'\t\t(symbol "{name}_0_1"',
        '\t\t\t(polyline (pts (xy 0 0) (xy 0 2.54)) '
        '(stroke (width 0) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy -1.27 1.27) (xy 0 2.54) (xy 1.27 1.27)) '
        '(stroke (width 0) (type default)) (fill (type none)))',
        '\t\t)',
        f'\t\t(symbol "{name}_1_1"',
        '\t\t\t(pin power_in line (at 0 0 90) (length 0)',
        f'\t\t\t\t(name "" {sym_effects()})',
        f'\t\t\t\t(number "1" {sym_effects()}))',
        '\t\t)',
        '\t)',
    ])


def generate_symbols() -> str:
    blocks = []

    blocks.append(power_symbol("+18V", "Original +18 V power symbol"))
    blocks.append(power_symbol("+8V8", "Original +8.8 V power symbol"))

    blocks.append(symbol(
        "7460305", "H", "WE_7460305", DATASHEET_URLS["WE_7460305"],
        "Wurth REDCUBE M5 press-fit high-current terminal",
        [("passive", "TERMINAL", "1", 0, -6.35, 90)], (3.81, 3.81),
        visible_property_positions=((0, 11.43), (0, 10.16)),
        body_bounds=(-3.81, 8.89, 3.81, -3.81),
    ))

    transformer_graphics = [
        # Primary winding and center tap.
        '\t\t\t(arc (start -5.08 5.08) (mid -6.35 3.81) (end -5.08 2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start -5.08 2.54) (mid -6.35 1.27) (end -5.08 0) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start -5.08 0) (mid -6.35 -1.27) (end -5.08 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start -5.08 -2.54) (mid -6.35 -3.81) (end -5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy -13.97 5.08) (xy -5.08 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy -13.97 0) (xy -5.08 0)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy -13.97 -5.08) (xy -5.08 -5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        # Transformer core and secondary winding.
        '\t\t\t(polyline (pts (xy -2.54 5.08) (xy -2.54 -5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy -1.27 5.08) (xy -1.27 -5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 1.27 5.08) (mid 2.54 3.81) (end 1.27 2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 1.27 2.54) (mid 2.54 1.27) (end 1.27 0) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 1.27 0) (mid 2.54 -1.27) (end 1.27 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 1.27 -2.54) (mid 2.54 -3.81) (end 1.27 -5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        # Two coupled common-mode-choke windings on the line side.
        '\t\t\t(polyline (pts (xy 1.27 5.08) (xy 3.81 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 3.81 5.08) (mid 5.08 3.81) (end 6.35 5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 6.35 5.08) (mid 7.62 3.81) (end 8.89 5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 1.27 -5.08) (xy 3.81 -5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 3.81 -5.08) (mid 5.08 -3.81) (end 6.35 -5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(arc (start 6.35 -5.08) (mid 7.62 -3.81) (end 8.89 -5.08) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 3.81 1.27) (xy 8.89 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 3.81 -1.27) (xy 8.89 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 8.89 5.08) (xy 13.97 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 1.27 0) (xy 13.97 0)) (stroke (width 0.254) (type default)) (fill (type none)))',
        '\t\t\t(polyline (pts (xy 8.89 -5.08) (xy 13.97 -5.08)) (stroke (width 0.254) (type default)) (fill (type none)))',
    ]
    blocks.append(symbol(
        "SM91502AL", "T", "SM91502AL", DATASHEET_URLS["SM91502AL"],
        "Bourns SM91502AL 1CT:1CT BMS isolation transformer with integrated common-mode choke",
        [
            ("passive", "PRI+", "1", -20.32, 5.08, 0),
            ("passive", "PR_CT", "2", -20.32, 0, 0),
            ("passive", "PRI-", "3", -20.32, -5.08, 0),
            ("passive", "LINE-", "4", 20.32, -5.08, 180),
            ("passive", "SC_CT", "5", 20.32, 0, 180),
            ("passive", "LINE+", "6", 20.32, 5.08, 180),
        ],
        (13.97, 7.62),
        transformer_graphics,
        visible_property_positions=((-13.97, 10.16), (13.97, 10.16)),
        visible_property_justifications=("left", "right"),
        pin_length=6.35,
    ))

    blocks.append(symbol(
        "ACS781LLRTR-100U-T", "U", "ACS781LLRTR-100U-T",
        DATASHEET_URLS["ACS781LLRTR-100U-T"],
        "Allegro 100 A unidirectional Hall-effect current sensor",
        [
            ("passive", "IP-", "6", -7.62, 5.08, 0),
            ("no_connect", "NC", "7", -7.62, 1.27, 0),
            ("power_in", "VCC", "1", -2.54, -8.89, 90),
            ("power_in", "GND", "2", 0, -8.89, 90),
            ("output", "VOUT", "3", 2.54, -8.89, 90),
            ("passive", "IP+", "5", 7.62, 5.08, 180),
            ("no_connect", "NC", "4", 7.62, 1.27, 180),
        ],
        (5.08, 6.35),
        property_positions=(10.16, 7.62),
    ))

    blocks.append(symbol(
        "BVN-M-R001-1.0", "R", "BVN-M-R001-1.0",
        DATASHEET_URLS["BVN-M-R001-1.0"],
        "Isabellenhuette BVN-M-R001 1 mOhm four-terminal current-sense resistor",
        [
            ("passive", "CURRENT+", "1", -13.97, 2.54, 0),
            ("passive", "SENSE+", "2", -13.97, -2.54, 0),
            ("passive", "SENSE-", "3", 13.97, -2.54, 180),
            ("passive", "CURRENT-", "4", 13.97, 2.54, 180),
        ],
        (11.43, 5.08),
        [
            '\t\t\t(polyline (pts (xy -6.35 2.54) (xy -3.81 2.54) (xy -2.54 1.27) (xy 0 3.81) (xy 2.54 1.27) (xy 3.81 2.54) (xy 6.35 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(polyline (pts (xy -3.81 -2.54) (xy -3.81 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(polyline (pts (xy 3.81 -2.54) (xy 3.81 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))',
        ],
        visible_property_positions=((0, 8.89), (0, 6.35)),
    ))

    bq79600_pin_names = [
        "DVDD", "NFAULT", "VIO", "RX/MOSI", "TX/MISO", "SCLK", "nCS",
        "nUART/SPI_(SPI_RDY)", "GND", "COMLP", "COMLN", "COMHN", "COMHP",
        "CVDD", "BAT", "INH",
    ]
    bq79600_types_by_number = {
        **{number: "power_in" for number in (3, 9, 15)},
        **{number: "power_out" for number in (1, 14)},
        **{number: "input" for number in (4, 6, 7)},
        **{number: "output" for number in (5, 16)},
        **{number: "bidirectional" for number in (8, 10, 11, 12, 13)},
        2: "open_collector",
    }
    bq79600_pins = []
    for number, pin_name in enumerate(bq79600_pin_names, 1):
        if number <= 8:
            position = (-20.32, 8.89 - (number - 1) * 2.54, 0)
        else:
            position = (20.32, -8.89 + (number - 9) * 2.54, 180)
        bq79600_pins.append((
            bq79600_types_by_number[number], pin_name, str(number), *position,
        ))
    blocks.append(symbol(
        "BQ79600-Q1", "U", "BQ79600-Q1", DATASHEET_URLS["BQ79600-Q1"],
        "Texas Instruments BQ79600-Q1 automotive SPI/UART daisy-chain communication bridge, PW-16 TSSOP",
        bq79600_pins, (15.24, 10.16),
        visible_property_positions=((-15.24, 11.43), (15.24, 11.43)),
        visible_property_justifications=("left", "right"),
        pin_length=5.08,
    ))

    bq_pin_names = [
        "CB6", "VC6", "CB5", "VC5", "CB4", "VC4", "CB3", "VC3", "CB2", "VC2", "CB1", "VC1",
        "CB0", "VC0", "AVSS_1", "WAKEUP", "FAULTLP", "FAULTLN", "COMLP", "COMLN", "COMHN", "COMHP",
        "FAULTHN", "FAULTHP", "CVDD", "CVSS", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6",
        "VIO", "VPROG", "DVSS", "DVDD", "LDOIN", "N.C._1", "VLDO", "TX", "RX", "NFAULT", "TSREF",
        "AVDD", "AVSS_2", "REF1", "N.C._2", "BAT", "EP",
    ]
    bq_types_by_number = {
        **{number: "bidirectional" for number in (1, 3, 5, 7, 9, 11, 13, 19, 20, 21, 22, 27, 28, 29, 30, 31, 32)},
        **{number: "input" for number in (2, 4, 6, 8, 10, 12, 14, 16, 23, 24, 33, 34, 37, 41, 48)},
        **{number: "output" for number in (17, 18, 40, 43)},
        **{number: "power_in" for number in (15, 25, 26, 35, 45, 49)},
        **{number: "power_out" for number in (36, 39, 44, 46)},
        38: "no_connect", 42: "open_collector", 47: "no_connect",
    }
    bq_pins = []
    for number, pin_name in enumerate(bq_pin_names, 1):
        if number <= 12:
            position = (-22.86, 15.24 - (number - 1) * 2.54, 0)
        elif number <= 24:
            position = (-15.24 + (number - 13) * 2.54, -33.02, 90)
        elif number <= 36:
            position = (22.86, -12.7 + (number - 25) * 2.54, 180)
        else:
            position = (15.24 - (number - 37) * 2.54, 33.02, 270)
        bq_pins.append((bq_types_by_number[number], pin_name, str(number), *position))
    blocks.append(symbol(
        "BQ79606A-Q1", "U", "BQ79606A-Q1", DATASHEET_URLS["BQ79606A-Q1"],
        "Texas Instruments BQ79606A-Q1 six-cell automotive battery monitor, PHP-48 PowerPAD package",
        bq_pins, (17.78, 27.94),
        visible_property_positions=((13.97, -29.21), (20.32, -31.75)),
        pin_length=5.08,
    ))

    bq79616_pin_names = [
        "BAT", "CB16", "VC16", "CB15", "VC15", "CB14", "VC14", "CB13",
        "VC13", "CB12", "VC12", "CB11", "VC11", "CB10", "VC10", "CB9",
        "VC9", "CB8", "VC8", "CB7", "VC7", "CB6", "VC6", "CB5",
        "VC5", "CB4", "VC4", "CB3", "VC3", "CB2", "VC2", "CB1",
        "VC1", "CB0", "VC0", "REFHM", "REFHP", "AVDD", "AVSS", "COMLP",
        "COMLN", "COMHN", "COMHP", "NEG5V", "CVDD", "CVSS", "LDOIN", "NPNB",
        "DVDD", "DVSS", "TSREF", "RX", "TX", "GPIO8", "GPIO7", "GPIO6",
        "GPIO5", "GPIO4", "GPIO3", "GPIO2", "GPIO1", "NFAULT", "BBN", "BBP",
        "EP",
    ]
    bq79616_types_by_number = {
        **{number: "bidirectional" for number in range(2, 35, 2)},
        **{number: "input" for number in range(3, 36, 2)},
        **{number: "bidirectional" for number in (40, 41, 42, 43, 54, 55, 56, 57, 58, 59, 60, 61)},
        **{number: "power_in" for number in (1, 36, 39, 46, 47, 50, 65)},
        **{number: "power_out" for number in (37, 38, 44, 45, 49, 51)},
        **{number: "input" for number in (52, 63, 64)},
        **{number: "output" for number in (48, 53)},
        62: "open_collector",
    }
    bq79616_pins = []
    for number, pin_name in enumerate(bq79616_pin_names, 1):
        if number <= 16:
            position = (-30.48, 19.05 - (number - 1) * 2.54, 0)
        elif number <= 32:
            position = (-19.05 + (number - 17) * 2.54, -29.21, 90)
        elif number <= 48:
            position = (30.48, -19.05 + (number - 33) * 2.54, 180)
        elif number <= 64:
            position = (19.05 - (number - 49) * 2.54, 29.21, 270)
        else:
            position = (24.13, -29.21, 90)
        bq79616_pins.append((
            bq79616_types_by_number[number], pin_name, str(number), *position,
        ))
    blocks.append(symbol(
        "BQ79616-Q1", "U", "BQ79616-Q1", DATASHEET_URLS["BQ79616-Q1"],
        "Texas Instruments BQ79616-Q1 16-cell automotive battery monitor, PAP-64 PowerPAD package",
        bq79616_pins, (25.4, 24.13),
        visible_property_positions=((-25.4, 25.4), (33.02, 25.4)),
        visible_property_justifications=("left", "right"),
        pin_length=5.08,
    ))

    blocks.append(symbol(
        "INA286", "U", "INA286_SOIC-8", DATASHEET_URLS["INA286_SOIC-8"],
        "Texas Instruments INA286 bidirectional current-shunt monitor, gain 100 V/V, SOIC-8",
        [
            ("input", "-IN", "1", -8.89, 2.54, 0),
            ("power_in", "GND", "2", 0, -11.43, 90),
            ("input", "REF2", "3", -3.81, -11.43, 90),
            ("no_connect", "NC", "4", 8.89, -2.54, 180),
            ("output", "OUT", "5", 8.89, 2.54, 180),
            ("power_in", "V+", "6", 0, 8.89, 270),
            ("input", "REF1", "7", 3.81, -11.43, 90),
            ("input", "+IN", "8", -8.89, -2.54, 0),
        ], (6.35, 6.35),
        visible_property_positions=((-6.35, 7.62), (3.81, 7.62)),
        body_bounds=(-6.35, 6.35, 6.35, -8.89),
    ))

    blocks.append(symbol(
        "STB45N65M5", "Q", "STB45N65M5_D2PAK", DATASHEET_URLS["STB45N65M5_D2PAK"],
        "STMicroelectronics STB45N65M5 650 V N-channel power MOSFET in D2PAK",
        [
            ("input", "G", "1", -7.62, 0, 0),
            ("passive", "D", "2", 0, 7.62, 270),
            ("passive", "S", "3", 0, -7.62, 90),
        ], (5.08, 5.08),
        visible_property_positions=((-5.08, 6.35), (7.62, 6.35)),
    ))

    blocks.append(symbol(
        "CSS2H-3920R-L200F", "R", "CSS2H-3920R-L200F", DATASHEET_URLS["CSS2H-3920R-L200F"],
        "Bourns CSS2H-3920R-L200F 0.2 mOhm four-terminal current-sense resistor",
        [("passive", "I1", "1", -7.62, 0, 0), ("passive", "I2", "2", 7.62, 0, 180)],
        (5.08, 2.54),
        ['\t\t\t(polyline (pts (xy -5.08 0) (xy -3.81 0) (xy -2.54 1.27) (xy -1.27 -1.27) (xy 0 1.27) (xy 1.27 -1.27) (xy 2.54 1.27) (xy 3.81 0) (xy 5.08 0)) (stroke (width 0.254) (type default)) (fill (type none)))'],
        visible_property_positions=((0, 6.35), (0, 3.81)),
    ))

    blocks.append(symbol(
        "L_Wuerth_WE-PD-Robust-7332", "L", "L_Wuerth_WE-PD-Robust-7332",
        DATASHEET_URLS["L_Wuerth_WE-PD-Robust-7332"],
        "Wurth Elektronik 7447789222 WE-PD Robust 220 uH shielded power inductor, size 7332",
        [("passive", "1", "1", -7.62, 0, 0), ("passive", "2", "2", 7.62, 0, 180)],
        (5.08, 2.54),
        [
            '\t\t\t(arc (start -5.08 0) (mid -3.81 1.27) (end -2.54 0) '
            '(stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(arc (start -2.54 0) (mid -1.27 1.27) (end 0 0) '
            '(stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(arc (start 0 0) (mid 1.27 1.27) (end 2.54 0) '
            '(stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(arc (start 2.54 0) (mid 3.81 1.27) (end 5.08 0) '
            '(stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(polyline (pts (xy -5.08 -1.27) (xy 5.08 -1.27)) '
            '(stroke (width 0.254) (type default)) (fill (type none)))',
        ],
        visible_property_positions=((0, 6.35), (0, 3.81)),
    ))

    # Supply, enable and configuration inputs on the left; switch node and the
    # feedback/monitor pins on the right; all three grounds along the bottom.
    blocks.append(symbol(
        "LTC3639", "U", "LTC3639_MSE16-12", DATASHEET_URLS["LTC3639_MSE16-12"],
        "Analog Devices LTC3639 150 V 100 mA synchronous step-down regulator, MSE16(12)",
        [
            ("power_in", "VIN", "3", -12.7, 8.89, 0),
            ("input", "RUN", "14", -12.7, 6.35, 0),
            ("input", "OVLO", "12", -12.7, 3.81, 0),
            ("input", "SS", "10", -12.7, 1.27, 0),
            ("input", "VPRG1", "7", -12.7, -1.27, 0),
            ("input", "VPRG2", "6", -12.7, -3.81, 0),
            ("output", "SW", "1", 12.7, 8.89, 180),
            ("input", "VFB", "9", 12.7, -3.81, 180),
            ("input", "ISET", "11", 12.7, -6.35, 180),
            ("output", "FBO", "5", 12.7, -8.89, 180),
            ("power_in", "GND", "8", -2.54, -13.97, 90),
            ("power_in", "GND", "16", 0, -13.97, 90),
            ("power_in", "GND", "17", 2.54, -13.97, 90),
        ], (10.16, 11.43),
        visible_property_positions=((-7.62, 12.7), (2.54, 12.7)),
    ))

    blocks.append(symbol(
        "1N6263W-7-F", "D", "1N6263W_SOD-123", DATASHEET_URLS["1N6263W_SOD-123"],
        "Diodes Incorporated 1N6263W-7-F surface-mount Schottky barrier diode, SOD-123",
        [("passive", "K", "1", -6.35, 0, 0), ("passive", "A", "2", 6.35, 0, 180)],
        (3.81, 2.54),
        [
            '\t\t\t(polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
            '\t\t\t(polyline (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))',
        ],
        visible_property_positions=((0, 5.08), (0, 3.81)),
    ))

    blocks.append(symbol(
        "D_ALT-Device", "D", "", "", "Original generic diode symbol",
        [("passive", "K", "1", -5.08, 0, 0), ("passive", "A", "2", 5.08, 0, 180)],
        (2.54, 2.54),
        visible_property_positions=((0, 5.08), (0, 3.81)),
    ))

    blocks.append(symbol(
        "INA190A3IDDFR", "U", "INA190A3IDDFR_DDF", DATASHEET_URLS["INA190A3IDDFR_DDF"],
        "Texas Instruments INA190A3 current-sense amplifier, DDF package",
        [
            ("power_in", "VS", "1", 0, 8.89, 270),
            ("input", "ENABLE", "2", -11.43, -2.54, 0),
            ("input", "REF", "3", -11.43, -5.08, 0),
            ("power_in", "GND", "4", 0, -8.89, 90),
            ("output", "OUT", "5", 11.43, 0, 180),
            ("no_connect", "NC", "6", 11.43, -5.08, 180),
            ("input", "IN+", "7", -11.43, 2.54, 0),
            ("input", "IN-", "8", -11.43, 0, 0),
        ], (8.89, 6.35),
        visible_property_positions=((-8.89, 7.62), (7.62, 7.62)),
    ))

    blocks.append(symbol(
        "IRS2186(4)(S)PBF", "U", "IRS2186S_SOIC-8", DATASHEET_URLS["IRS2186S_SOIC-8"],
        "Infineon IRS2186 high- and low-side gate driver, 8-lead SOIC variant",
        [
            ("input", "HIN", "1", -10.16, 1.27, 0),
            ("input", "LIN", "2", -10.16, -1.27, 0),
            ("power_in", "COM", "3", -3.81, -8.89, 90),
            ("output", "LO", "4", 10.16, -1.27, 180),
            ("power_in", "VCC", "5", -3.81, 8.89, 270),
            ("power_in", "VS", "6", 3.81, -8.89, 90),
            ("output", "HO", "7", 10.16, 1.27, 180),
            ("power_in", "VB", "8", 3.81, 8.89, 270),
        ], (7.62, 6.35),
        visible_property_positions=((-8.89, 7.62), (13.97, 7.62)),
    ))

    blocks.append(symbol(
        "LFXTAL016178REEL", "Y", "LFXTAL016178REEL", DATASHEET_URLS["LFXTAL016178REEL"],
        "IQD 85SMX watch crystal",
        [
            ("passive", "X1", "1", -7.62, 2.54, 0),
            ("power_in", "GND", "2", -7.62, -2.54, 0),
            ("power_in", "GND", "3", 7.62, -2.54, 180),
            ("passive", "X2", "4", 7.62, 2.54, 180),
        ], (5.08, 3.81),
        visible_property_positions=((0, 7.62), (0, 5.08)),
    ))

    for name, footprint_name, description, visible_positions in (
        ("LM2576HVS-ADJ_NOPB_NOPB_TO_263_TAB3GND", "LM2576HV_TO-263-5", "TI LM2576HV adjustable buck regulator", ((0, 11.43), (0, 8.89))),
        ("LM2596SX-5.0_NOPB", "LM2596S_TO-263-5", "TI LM2596 5 V buck regulator", ((0, 11.43), (0, 8.89))),
    ):
        blocks.append(symbol(
            name, "U", footprint_name, DATASHEET_URLS[footprint_name], description,
            [
                ("power_in", "VIN", "1", -8.89, 2.54, 0),
                ("output", "OUTPUT", "2", 8.89, 2.54, 180),
                ("power_in", "GND", "3", 0, -10.16, 90),
                ("input", "FEEDBACK", "4", 8.89, 0, 180),
                ("input", "ON/OFF", "5", -8.89, -2.54, 0),
            ], (6.35, 7.62),
            visible_property_positions=visible_positions,
        ))

    blocks.append(symbol(
        "NCS213RSQT2G", "U", "NCS213R_SC70-6", DATASHEET_URLS["NCS213R_SC70-6"],
        "onsemi NCS213R bidirectional current-shunt monitor, gain 50",
        [
            ("power_in", "VS", "3", -8.89, -2.54, 0),
            ("power_in", "GND", "2", -1.27, -8.89, 90),
            ("input", "REF", "1", 1.27, -8.89, 90),
            ("output", "OUT", "6", 8.89, 2.54, 180),
            ("input", "IN-", "5", 8.89, 0, 180),
            ("input", "IN+", "4", 8.89, -2.54, 180),
        ],
        visible_property_positions=((0, 10.16), (0, 7.62)),
    ))

    blocks.append(symbol(
        "STM32L071KBTx_Custom", "U", "Package_QFP:LQFP-32_7x7mm_P0.8mm",
        DATASHEET_URLS["STM32L071KBTx_Custom"],
        "STMicroelectronics STM32L071KBTx ultra-low-power Arm Cortex-M0+ MCU, LQFP-32",
        [
            ("input", "NRST", "4", -15.24, 17.78, 0),
            ("input", "BOOT0", "31", -15.24, 12.7, 0),
            ("bidirectional", "PC14", "2", -15.24, 2.54, 0),
            ("bidirectional", "PC15", "3", -15.24, 0, 0),
            ("bidirectional", "PB0", "14", -15.24, -5.08, 0),
            ("bidirectional", "PB1", "15", -15.24, -7.62, 0),
            ("bidirectional", "PB3", "26", -15.24, -10.16, 0),
            ("bidirectional", "PB4", "27", -15.24, -12.7, 0),
            ("bidirectional", "PB5", "28", -15.24, -15.24, 0),
            ("bidirectional", "PB6", "29", -15.24, -17.78, 0),
            ("bidirectional", "PB7", "30", -15.24, -20.32, 0),
            ("power_in", "VDD", "1", -2.54, 22.86, 270),
            ("power_in", "VDD", "17", 0, 22.86, 270),
            ("power_in", "VDDA", "5", 2.54, 22.86, 270),
            ("power_in", "VSS", "16", -2.54, -25.4, 90),
            ("power_in", "VSS", "32", 0, -25.4, 90),
            *[
                ("bidirectional", f"PA{port}", str(number), 12.7, 17.78 - index * 2.54, 180)
                for index, (port, number) in enumerate([
                    (0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11), (6, 12), (7, 13),
                    (8, 18), (9, 19), (10, 20), (11, 21), (12, 22), (13, 23), (14, 24), (15, 25),
                ])
            ],
        ],
        body=(11.43, 21.59),
        visible_property_positions=((-12.7, 21.59), (5.08, 21.59)),
        visible_property_justifications=("left", "left"),
        body_bounds=(-12.7, 20.32, 10.16, -22.86),
    ))

    stm32_pin_names = [
        "VBAT", "PC13-TAMPER-RTC", "PC14-OSC32_IN", "PC15-OSC32_OUT",
        "PD0-OSC_IN", "PD1-OSC_OUT", "NRST", "VSSA", "VDDA", "PA0-WKUP",
        "PA1", "PA2", "PA3", "PA4", "PA5", "PA6", "PA7", "PB0", "PB1",
        "PB2-BOOT1", "PB10", "PB11", "VSS_1", "VDD_1", "PB12", "PB13",
        "PB14", "PB15", "PA8", "PA9", "PA10", "PA11", "PA12",
        "PA13-JTMS-SWDIO", "VSS_2", "VDD_2", "PA14-JTCK-SWCLK",
        "PA15-JTDI", "PB3-JTDO-TRACESWO", "PB4-JNTRST", "PB5", "PB6",
        "PB7", "BOOT0", "PB8", "PB9", "VSS_3", "VDD_3",
    ]
    stm32_power_pins = {1, 8, 9, 23, 24, 35, 36, 47, 48}
    stm32_input_pins = {7, 44}

    return "\n".join([
        '(kicad_symbol_lib',
        '\t(version 20231120)',
        '\t(generator "kicad_symbol_editor")',
        '\t(generator_version "9.0")',
        *blocks,
        ')',
        '',
    ])


def extract_top_level_symbol(content: str, name: str) -> str:
    """Return one complete top-level symbol block without changing its text."""
    marker = f'\t(symbol "{name}"'
    start = content.index(marker)
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(content)):
        character = content[index]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return content[start:index + 1]
    raise ValueError(f"Unbalanced symbol block: {name}")


def preserve_symbol_block(generated: str, existing: str, name: str) -> str:
    """Keep a user-edited symbol's geometry and pins byte-for-byte."""
    generated_block = extract_top_level_symbol(generated, name)
    existing_block = extract_top_level_symbol(existing, name)
    return generated.replace(generated_block, existing_block, 1)


def symbol_library_name(symbol_name: str) -> str:
    """KiCad library nickname for a symbol that lives in its own file.

    The symbol name lowercased, with every run of non-alphanumeric characters
    collapsed to "_": LTC3639 becomes ltc3639, so the lib_id is ltc3639:LTC3639.

    One symbol per library file is what gives each part its own git history:
    a merged library is a single blob, so a change to any symbol changes the
    hash of every symbol in it, and the per-block workarounds (log -S, -G, -L)
    do not work on S-expressions.
    """
    return re.sub(r"[^a-z0-9]+", "_", symbol_name.lower()).strip("_")


def symbol_library_path(symbol_name: str) -> Path:
    return SYMBOL_DIR / f"{symbol_library_name(symbol_name)}.kicad_sym"


def split_symbol_library(combined: str) -> dict[str, str]:
    """Split the generated library into one single-symbol library per part.

    The symbol block itself is copied without a byte changed, so a block that
    is later imported into a project library stays comparable with the file
    it came from.
    """
    header = "\n".join([
        "(kicad_symbol_lib",
        '\t(version 20231120)',
        '\t(generator "kicad_symbol_editor")',
        '\t(generator_version "9.0")',
        "",
    ])
    names = re.findall(r'^\t\(symbol "([^"]*)"', combined, re.M)
    return {
        name: header + extract_top_level_symbol(combined, name) + "\n)\n"
        for name in names
    }


def sync_provenance(generated_footprints: Iterable[str]) -> None:
    """Synchronize symbol/footprint provenance while preserving other assets."""
    path = ROOT / "ASSET_PROVENANCE.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, existing = rows[0], rows[1:]

    kept = [
        row for row in existing
        if row[2] not in {"symbol", "footprint", "datasheet"}
    ]
    kept = [row for row in kept if row[0] not in {
        "tools/generate_original_kicad_assets.py", "tools/fabrication_standard.py",
    }]

    symbol_sources = {
        "+18V": ("NOASSERTION", "Original power symbol from electrical convention"),
        "+8V8": ("NOASSERTION", "Original power symbol from electrical convention"),
        "BQ79600-Q1": (
            DATASHEET_URLS["BQ79600-Q1"],
            "Manufacturer PW-16 pin-function facts; independently recreated physical pin arrangement",
        ),
        "BQ79606A-Q1": (
            DATASHEET_URLS["BQ79606A-Q1"],
            "Manufacturer PHP-48 pin-function facts; independently recreated physical pin arrangement",
        ),
        "BQ79616-Q1": (
            DATASHEET_URLS["BQ79616-Q1"],
            "Manufacturer PAP-64 pin-function facts and EVM exposed-pad grounding; independently recreated physical pin arrangement with enlarged symbol outline",
        ),
        "INA286": (DATASHEET_URLS["INA286_SOIC-8"], "Manufacturer SOIC-8 pin-function facts"),
        "STB45N65M5": (DATASHEET_URLS["STB45N65M5_D2PAK"], "Manufacturer D2PAK pin-function facts"),
        "CSS2H-3920R-L200F": (DATASHEET_URLS["CSS2H-3920R-L200F"], "Manufacturer resistor terminal facts"),
        "1N6263W-7-F": (DATASHEET_URLS["1N6263W_SOD-123"], "Manufacturer diode polarity facts"),
        "7460305": (DATASHEET_URLS["WE_7460305"], "Manufacturer terminal and mechanical facts"),
        "ACS781LLRTR-100U-T": (DATASHEET_URLS["ACS781LLRTR-100U-T"], "Manufacturer pin-function facts"),
        "BVN-M-R001-1.0": (DATASHEET_URLS["BVN-M-R001-1.0"], "Manufacturer four-terminal connection facts"),
        "D_ALT-Device": ("NOASSERTION", "Original generic diode symbol from electrical convention"),
        "INA190A3IDDFR": (DATASHEET_URLS["INA190A3IDDFR_DDF"], "Manufacturer DDF pin-function facts"),
        "IRS2186(4)(S)PBF": (DATASHEET_URLS["IRS2186S_SOIC-8"], "Manufacturer IRS2186S pin-function facts"),
        "LFXTAL016178REEL": (DATASHEET_URLS["LFXTAL016178REEL"], "Manufacturer terminal-function facts"),
        "LM2576HVS-ADJ_NOPB_NOPB_TO_263_TAB3GND": (DATASHEET_URLS["LM2576HV_TO-263-5"], "Manufacturer pin-function facts"),
        "LM2596SX-5.0_NOPB": (DATASHEET_URLS["LM2596S_TO-263-5"], "Manufacturer pin-function facts"),
        "L_Wuerth_WE-PD-Robust-7332": (
            DATASHEET_URLS["L_Wuerth_WE-PD-Robust-7332"],
            "Manufacturer two-terminal inductor facts; independently drawn coil symbol from electrical convention",
        ),
        "LTC3639": (
            DATASHEET_URLS["LTC3639_MSE16-12"],
            "Manufacturer MSE16(12) pin-function facts, including the removed pins 2, 4, 13 and 15 "
            "and exposed-pad ground pin 17; independently recreated functional pin arrangement",
        ),
        "NCS213RSQT2G": (DATASHEET_URLS["NCS213R_SC70-6"], "Manufacturer SC70 pin-function facts"),
        "SM91502AL": (
            DATASHEET_URLS["SM91502AL"],
            "Manufacturer six-pin 1CT:1CT transformer and integrated common-mode-choke connection facts",
        ),
        "STM32L071KBTx_Custom": (
            DATASHEET_URLS["STM32L071KBTx_Custom"],
            "Manufacturer LQFP-32 pin-function facts; independently recreated logical pin arrangement",
        ),
    }
    symbol_rows = []
    for name, (source, origin) in symbol_sources.items():
        if True:
            author = "Gerhard Malberg"
            license_name = LICENSE
            if name == "BQ79606A-Q1":
                modification = (
                    "Independently redrawn KiCad 9 symbol in physical package arrangement; "
                    "datasheet ERC types retained; no third-party UUIDs or distributor metadata imported"
                )
            elif name == "STM32L071KBTx_Custom":
                modification = (
                    "Independently redrawn KiCad 9 symbol using the functional arrangement and "
                    "manufacturer pin facts; no third-party geometry, UUIDs, or metadata imported"
                )
            elif name in {"ACS781LLRTR-100U-T", "NCS213RSQT2G"}:
                modification = "Independently generated KiCad 9 symbol with existing pin placement retained"
            elif name == "SM91502AL":
                modification = (
                    "Independently generated KiCad 10-compatible symbol from the manufacturer connection "
                    "diagram; no third-party geometry or distributor metadata retained"
                )
            else:
                modification = "Independently generated KiCad 9 symbol; no third-party geometry or distributor metadata retained"
            if name in GRID_NORMALIZED_SYMBOLS:
                modification += "; placement coordinates normalized to a 50 mil (1.27 mm) grid"
            status = "cleared_original"
            notes = COPYRIGHT
        symbol_rows.append([
            f"symbols/{symbol_library_name(name)}.kicad_sym", name, "symbol",
            author, source, origin, license_name, modification, status, notes,
        ])

    footprint_sources = {
        **DATASHEET_URLS,
        "Power_Pad_6x6mm": "NOASSERTION",
        **{base + "_MinimalSilkscreen": DATASHEET_URLS[base] for base in MINIMAL_SILK_BASES},
        **{name: "NOASSERTION" for name in MINIMAL_PASSIVES},
    }
    footprint_rows = [
        [
            f"footprints/custom_footprints.pretty/{name}.kicad_mod", name, "footprint",
            "Gerhard Malberg", footprint_sources[name],
            "Original footprint generated from manufacturer dimensions" if footprint_sources[name] != "NOASSERTION" else "Original generic footprint",
            LICENSE,
            "Independently generated KiCad 9 footprint linked to its original CERN-OHL-P-2.0 STEP model; existing pad, courtyard and display settings retained",
            "cleared_original", COPYRIGHT,
        ]
        for name in generated_footprints
    ]
    for row in footprint_rows:
        if row[1] in MINIMAL_PASSIVES:
            row[5] = "Independent numeric definition of generic chip body, lands and courtyard; existing land dimensions retained"
            row[7] = "Original parametric footprint and UUIDs; minimal silkscreen; external stock KiCad STEP reference only, with no third-party CAD copied or redistributed"
        elif row[1].endswith("_MinimalSilkscreen"):
            row[5] = "Variant of this library's original footprint with generic sparse silkscreen; no board-specific via coordinates"
            row[7] = "Retains original lands, fabrication body, courtyard, mechanical guides and original STEP link; shortened outlines retain orientation marks"
            if row[1].startswith("Bourns_CDSOD323"):
                row[7] += "; compact 0.60x0.45mm lands at 2.10mm pitch, NOT the manufacturer's recommended land pattern"
        elif row[1] == "BQ79600-Q1":
            row[7] = (
                "Independently generated KiCad 9 PW0016A footprint using the manufacturer 5.8 mm "
                "opposite-pad centre spacing, 1.5 x 0.45 mm lands, and 0.65 mm pitch; "
                "linked to the original color-preserving CadQuery STEP model"
            )
        elif row[1] == "BQ79606A-Q1":
            row[7] = (
                "Independently generated KiCad 9 footprint with the retained 8.5 mm "
                "opposite-pad centre spacing and 5.17 mm pad 49 copper size; "
                "the existing local mask/paste margins are retained"
            )
        elif row[1] == "BQ79616-Q1":
            row[7] = (
                "Independently generated KiCad 9 PAP0064F footprint using the manufacturer 11.4 mm "
                "opposite-pad centre spacing, 1.5 x 0.3 mm perimeter lands, and 6.5 mm exposed pad 65; "
                "linked to the original color-preserving CadQuery STEP model with the retained "
                "+90 degree Z rotation"
            )
        elif row[1] == "SM91502AL":
            row[7] = (
                "Independently generated KiCad 10-compatible footprint using the manufacturer 0.76 x 1.27 mm "
                "lands, 2.54 mm pitch, 9.65 mm outside span, and 7.11 mm inside gap; linked directly "
                "to the original CadQuery STEP model at the PCB seating plane"
            )
        elif row[1] == "BVN-M-R001-1.0":
            row[7] = "Independently generated KiCad 9 footprint; 180 degree STEP Z rotation retained"
        elif row[1] == "PG-HSOG-8-1_INF_gsd":
            row[7] = "Independently generated KiCad 9 footprint; GSD naming and gate/source/drain pad numbering retained"
        elif row[1] == "Power_Pad_6x6mm":
            row[7] = "Independently generated KiCad 9 footprint; -90 degree STEP Z rotation retained"
        elif row[1] == "WE_7460305":
            row[7] = (
                "Independently generated KiCad 9 footprint linked to its original CERN-OHL-P-2.0 STEP model; "
                "horizontal silkscreen placement retained"
            )
        elif row[1] == "Bourns_CDSOD323-TxxC_SOD-323_Compact":
            row[5] = "Manufacturer package dimensions; independently specified compact land geometry preserving existing pad locations and dimensions"
            row[7] = (
                "Original voltage-independent bidirectional SOD-323 artwork and IDs; 1.80x1.40mm "
                "representative body, 0.60x0.45mm roundrect lands at 2.10mm pitch, radius 0.1125mm; "
                "NOT the Bourns recommended 0.80x0.50mm lands at 2.20mm pitch; links to an original STEP model"
            )
    footprint_rows.append([
        "footprints/custom_footprints.pretty/ACS781LLRTR-100U-T.kicad_mod",
        "ACS781LLRTR-100U-T", "footprint", "Gerhard Malberg",
        DATASHEET_URLS["ACS781LLRTR-100U-T"],
        "Original footprint authored only from manufacturer package and reference land-pattern dimensions in DWG-0000428",
        LICENSE,
        "Independently drawn KiCad 9 footprint linked to its original CERN-OHL-P-2.0 STEP model; signal pads 1 through 3 use the retained 2.0 mm length",
        "cleared_original",
        f"{COPYRIGHT}; no third-party UUIDs metadata or geometry retained",
    ])

    for row in footprint_rows:
        row[7] += (
            "; reference-only fabrication display: hidden value/description, "
            "body-fitted reference and preserved orientation markings; electrical geometry unchanged"
        )

    datasheet_rows = []
    for filename, logical_name, author, source in (
        ("BVN.pdf", "BVN manufacturer datasheet", "Isabellenhuette Heusler GmbH & Co. KG", DATASHEET_URLS["BVN-M-R001-1.0"]),
        ("7447709271.pdf", "7447709271 manufacturer datasheet", "Wurth Elektronik eiSos GmbH & Co. KG", DATASHEET_URLS["L_Wuerth_WE-PD-Typ-LS-1210"]),
        ("bq79600-q1.pdf", "BQ79600-Q1 manufacturer datasheet", "Texas Instruments Incorporated", DATASHEET_URLS["BQ79600-Q1"]),
        ("bq79606a-q1.pdf", "BQ79606A-Q1 manufacturer datasheet", "Texas Instruments Incorporated", DATASHEET_URLS["BQ79606A-Q1"]),
        ("bq79616-q1.pdf", "BQ79616-Q1 manufacturer datasheet", "Texas Instruments Incorporated", DATASHEET_URLS["BQ79616-Q1"]),
        ("sluuc37d.pdf", "BQ79616-Q1 evaluation module user guide", "Texas Instruments Incorporated", "https://www.ti.com/lit/pdf/sluuc37"),
        ("slvae87b.pdf", "BQ7961x-Q1 high-voltage BMS design recommendations", "Texas Instruments Incorporated", "https://www.ti.com/lit/pdf/slvae87"),
        ("ina286.pdf", "INA286 manufacturer datasheet", "Texas Instruments Incorporated", DATASHEET_URLS["INA286_SOIC-8"]),
        ("stb45n65m5.pdf", "STB45N65M5 manufacturer datasheet", "STMicroelectronics", DATASHEET_URLS["STB45N65M5_D2PAK"]),
        ("css2h-3920.pdf", "CSS2H-3920 manufacturer datasheet", "Bourns, Inc.", DATASHEET_URLS["CSS2H-3920R-L200F"]),
        ("1N6263W.pdf", "1N6263W manufacturer datasheet", "Diodes Incorporated", DATASHEET_URLS["1N6263W_SOD-123"]),
        ("sm91502al.pdf", "SM91502AL manufacturer datasheet", "Bourns, Inc.", DATASHEET_URLS["SM91502AL"]),
        ("7447789222.pdf", "7447789222 manufacturer datasheet", "Wurth Elektronik eiSos GmbH & Co. KG", DATASHEET_URLS["L_Wuerth_WE-PD-Robust-7332"]),
        ("3639fd.pdf", "LTC3639 manufacturer datasheet", "Analog Devices, Inc.", DATASHEET_URLS["LTC3639_MSE16-12"]),
    ):
        if (ROOT / filename).exists():
            datasheet_rows.append([
                filename, logical_name, "datasheet", author, source,
                "Manufacturer PDF retained as a factual reference", "NOASSERTION",
                "Unmodified third-party document; excluded from repository CAD licence grants",
                "not_cleared_for_redistribution",
                "Remove before a CERN-only/public release unless separate redistribution permission is documented",
            ])

    tool_row = [
        "tools/generate_original_kicad_assets.py", "Original KiCad asset generator", "source",
        "Gerhard Malberg", "NOASSERTION", "Original generator source", LICENSE,
        "Generates the cleared symbol library and datasheet-backed footprints; applies the documented fabrication display standard", "cleared_original",
        f"{COPYRIGHT}; SPDX notice embedded",
    ]
    fabrication_tool_row = [
        "tools/fabrication_standard.py", "Fabrication display standard and checker", "source",
        "Gerhard Malberg", "NOASSERTION", "Original formatting and validation source", LICENSE,
        "Applies reference-only fabrication display and verifies front/back text fit; includes a project-copy SOD-323 display rule without distributing third-party CAD",
        "cleared_original", f"{COPYRIGHT}; SPDX notice embedded",
    ]

    ordered = (
        symbol_rows
        + sorted(footprint_rows, key=lambda row: row[0].lower())
        + datasheet_rows
        + kept
        + [tool_row, fabrication_tool_row]
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(ordered)


def ensure_acs781_properties() -> None:
    """Keep the separately authored ACS781 footprint pointing at the right model.

    Its provenance lives in ASSET_PROVENANCE.csv like every other asset; the
    fields this used to inject are stripped again by strip_provenance_fields().
    """
    path = FOOTPRINT_DIR / "ACS781LLRTR-100U-T.kicad_mod"
    content = path.read_text(encoding="utf-8")
    legacy_model_path = (
        "${KIPRJMOD}/libraries/kicad-libraries/3d_models/"
        "custom_3dmodels.3dshapes/ACS781LLRTR-100U-T.stp"
    )
    model_path = (
        "${KIPRJMOD}/kicad-libraries/3d_models/"
        "custom_3dmodels.3dshapes/ACS781LLRTR-100U-T.step"
    )
    content = content.replace(legacy_model_path, model_path)
    content = content.replace("ACS781LLRTR-100U-T.stp", "ACS781LLRTR-100U-T.step")
    content = re.sub(
        r'(\(property "Datasheet" ")[^"]*(")',
        lambda match: match.group(1) + DATASHEET_URLS["ACS781LLRTR-100U-T"] + match.group(2),
        content,
        count=1,
    )
    path.write_text(apply_standard(content, path.stem), encoding="utf-8", newline="\n")


PROVENANCE_FIELDS = ("Source", "Copyright", "License", "ModificationLicense")


def strip_provenance_fields() -> None:
    """Remove provenance properties from every symbol and footprint.

    Library assets carry KiCad's own fields only. Licence, copyright and source
    are recorded once, in ASSET_PROVENANCE.csv, rather than duplicated into every
    asset and from there into every schematic that places one.

    Runs after generation so it also reaches the preserved symbol blocks and the
    separately authored ACS781 footprint, neither of which is emitted by the
    generators above.
    """
    def drop(text: str) -> tuple[str, int]:
        removed = 0
        for field in PROVENANCE_FIELDS:
            token = f'(property "{field}"'
            while token in text:
                i = text.index(token)
                depth, j, in_string = 0, i, False
                while j < len(text):
                    ch = text[j]
                    if in_string:
                        if ch == "\\":
                            j += 2
                            continue
                        if ch == '"':
                            in_string = False
                    elif ch == '"':
                        in_string = True
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                start = i
                while start > 0 and text[start - 1] in "\t ":
                    start -= 1
                end = j + 1
                if end < len(text) and text[end] == "\n":
                    end += 1
                text = text[:start] + text[end:]
                removed += 1
        return text, removed

    total = 0
    for path in sorted(SYMBOL_DIR.glob("*.kicad_sym")):
        content, n = drop(path.read_text(encoding="utf-8"))
        if n:
            path.write_text(content, encoding="utf-8", newline="\n")
        total += n
    for path in sorted(FOOTPRINT_DIR.glob("*.kicad_mod")):
        content, n = drop(path.read_text(encoding="utf-8"))
        if n:
            path.write_text(content, encoding="utf-8", newline="\n")
        total += n
    if total:
        print(f"Stripped {total} provenance properties from library assets.")

def main() -> None:
    FOOTPRINT_DIR.mkdir(parents=True, exist_ok=True)
    SYMBOL_DIR.mkdir(parents=True, exist_ok=True)
    generated = generate_footprints()
    for name, content in generated.items():
        (FOOTPRINT_DIR / f"{name}.kicad_mod").write_text(content, encoding="utf-8", newline="\n")
    legacy_gsd = FOOTPRINT_DIR / "PG-HSOG-8-1_INF.kicad_mod"
    if legacy_gsd.exists():
        legacy_gsd.unlink()
    legacy_wuerth = FOOTPRINT_DIR / "L_Wuerth_WE-PD-Typ-LS.kicad_mod"
    if legacy_wuerth.exists():
        legacy_wuerth.unlink()
    ensure_acs781_properties()
    generated_symbols = generate_symbols()
    # These existing symbol files are authoritative for their hand-maintained
    # geometry. Preserve their blocks rather than replacing their pin
    # arrangements with the generated defaults.
    for preserved_name in ("BQ79616-Q1", "SM91502AL"):
        existing_library = symbol_library_path(preserved_name)
        if not existing_library.exists():
            # Silently skipping this would overwrite the hand-maintained pin
            # arrangement with the generated one, which is smaller and wrong,
            # and the loss would only surface at the next library update.
            raise SystemExit(
                f"{existing_library} is missing, so {preserved_name} cannot be "
                f"preserved. Restore it from git before regenerating."
            )
        generated_symbols = preserve_symbol_block(
            generated_symbols,
            existing_library.read_text(encoding="utf-8"),
            preserved_name,
        )
    symbol_libraries = split_symbol_library(generated_symbols)
    for symbol_name, content in symbol_libraries.items():
        symbol_library_path(symbol_name).write_text(
            content, encoding="utf-8", newline="\n"
        )
    strip_provenance_fields()
    sync_provenance(generated)
    print(
        f"Generated {len(symbol_libraries)} single-symbol libraries "
        f"and {len(generated) + 1} original footprints."
    )


if __name__ == "__main__":
    main()
