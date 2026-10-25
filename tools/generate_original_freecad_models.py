"""Generate original FreeCAD projects and STEP models for authored footprints.

Copyright 2026 Gerhard Malberg
SPDX-License-Identifier: CERN-OHL-P-2.0

Covered Source under CERN-OHL-P-2.0. Package dimensions and terminal layouts
are transcribed from the official manufacturer datasheets linked in SOURCES.
No geometry from downloaded or retained third-party CAD files is used.

Run this file with FreeCAD 1.1.1's GUI executable to preserve per-object colors
in FCStd and STEP. Every generated FCStd document has an editable design tree
and licensing/provenance properties. The STEP header also carries the author,
copyright, source, and SPDX licence.
"""

from __future__ import annotations

import csv
import math
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import FreeCAD as App
import Import
import Part

if App.GuiUp:
    import FreeCADGui as Gui


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "3d_models" / "custom_3dmodels.3dshapes"
SOURCE_DIR = ROOT / "3d_models" / "sources"
LICENSE = "CERN-OHL-P-2.0"
COPYRIGHT = "Copyright 2026 Gerhard Malberg"
AUTHOR = "Gerhard Malberg"
GENERATOR = "FreeCAD 1.1.1 / generate_original_freecad_models.py"

HARWIN_GECKO_M2P_DRAWING = (
    "https://content.harwin.com/asset/9080e3a3-bca3-45d8-8fc9-6c172eec098d/"
    "DRG-02638-Technical-Drawing-Datasheet-G125-MV1XX05M2P-pdf.pdf"
)

MOLEX_MINI50_DUAL_BASIS = (
    "Molex sales drawing SD-348250200 (MINI50 12-24CKT VERT HDR): 2.00 pitch, 1.00 contact "
    "holes, 0.40 x 0.50 blades, DIM E post holes 2.15 press fit / 2.55 drop in, body width "
    "12.17 and 15.60 above the PCB. Row spacing 2.20 and the aligned (not staggered) rows were "
    "measured from the drawn hole centres in the PCB layout views and cross-checked against the "
    "sheet's 4.75 and 2.55 transverse callouts, whose difference is that row spacing. Shroud "
    "depth 6.44 carried over from SD-34792-001, the mating interface being common to the series"
)

M80_BASIS = (
    "Harwin Datamate M80 2.00mm pitch. Pitch, 2.00 row spacing, contact positions, body "
    "envelope, above-board height and 3.30 PC tails were measured from the manufacturer "
    "reference solid for the part (dimensional facts only; this model shares no geometry with "
    "it). The 0.90 contact hole comes from the PCB layout view on Harwin drawing M80-511, "
    "measured against the known 2.00 pitch. Catalogue ratings: 3.3A per contact, 800V working, "
    "25mOhm max, 500 mating cycles, -55 to +125C, 100G shock"
)

SOURCES = {
    "Bourns_CDSOD323-TxxC_SOD-323": (
        "https://www.bourns.com/docs/Product-Datasheets/CDSOD323-TxxC.pdf",
        "Bourns CDSOD323-TxxC package drawing: body A 1.60-1.90 x B 1.15-1.45, "
        "lead span C 2.39-2.70, overall height D 0.92-1.14, lead width E 0.25-0.40, "
        "thickness F 0.08-0.20, standoff H <=0.13, foot J 0.30-0.45 mm. "
        "Representative model: body 1.80x1.40, height 1.05, standoff 0.06, span 2.60, "
        "lead width/foot 0.35 and thickness 0.14 mm. No polarity band for bidirectional parts; "
        "formed lead bends are an original approximation within the package envelope",
        ".step",
    ),
    "Littelfuse_SZSMFxxA_SOD-123FL": (
        "https://www.littelfuse.com/products/overvoltage-protection/tvs-diodes/surface-mount/smf",
        "Littelfuse SZSMFxxA datasheet rev 10/25/24, SOD-123FL package table: E 2.70 body "
        "length, D 1.65 body width, A 0.95 overall height on A1 0.05 standoff, HE 3.60 overall "
        "lead span, b 0.90 lead width, L 0.75 foot length, c 0.15 lead thickness",
        ".step",
    ),
    "Bourns_SMBJ-Q_DO-214AA": (
        "https://www.bourns.com/docs/product-datasheets/smbj-q.pdf",
        "DO-214AA (SMB) JEDEC registered outline, dimensions from the Vishay SMB outline "
        "drawing document 95401: body 4.06-4.57 x 3.30-3.94, height 1.95-2.20 on a 0-0.20 "
        "standoff, overall lead span 5.21-5.59, foot 0.76-1.52 long x 2.13-2.44 wide, "
        "terminal thickness 0.152-0.305. Modelled at the drawing maxima, the conservative "
        "choice for clearance. Moulded epoxy body with tin-plated leads, cathode band at "
        "the pin 1 end",
        ".step",
    ),
    "Vishay_RCL1225_2W": (
        "https://www.vishay.com/docs/20046/rcle3.pdf",
        "Vishay RCL e3 datasheet document 20046 rev 20-Oct-2025, DIMENSIONS AND MASS table: "
        "RCL1225 e3 L 3.2 +/-0.20, W 6.3 +/-0.20, H 0.70 +/-0.10, T1 0.8 +/-0.20, "
        "T2 0.4 +/-0.20, mass 55 mg. Long-side termination reverse geometry, so the "
        "terminations run along the 6.3 mm side. Modelled at the drawing nominal",
        ".step",
    ),
    "Littelfuse_470-Series_Fuse": (
        "https://www.littelfuse.com/products/fuses-overcurrent-protection/fuses/surface-mount-fuses/thin-film-chip-fuses/470",
        "Littelfuse 470 Series datasheet dimensions figure: 3.302 x 1.575 x 1.168 mm (drawing "
        "maxima; Digi-Key quotes 3.15 x 1.50 x 1.15 nominal). Epoxy resin body with Cu/Ni/Sn "
        "terminations. Modelled at the drawing maxima, the conservative choice for clearance",
        ".step",
    ),
    "Schurter_MGA-A_Fuse": (
        "https://www.schurter.com/en/datasheet/typ_MGA-A.pdf",
        "Schurter MGA-A datasheet dimension figure: 3.20 body length, 1.55 body width, 0.50 end "
        "metallisations. The figure's height label was not machine readable, so the 1.55 height "
        "is taken from the Digi-Key package dimensions for 3-103-099 (0.126 x 0.061 x 0.061 in), "
        "which also matches the 1.55 width - the hermetic ceramic body is markedly taller than "
        "the 0.60 plastic USF 1206 of the same outline",
        ".step",
    ),
    "Schurter_USF-1206_Fuse": (
        "https://www.schurter.com/en/datasheet/typ_USF_1206.pdf",
        "Schurter USF 1206 datasheet: 3.20 x 1.60 x 0.60 mm body with a 2.20 mm gap between the "
        "end metallisations, giving 0.50 mm terminals; fibre-reinforced housing UL94V-0 with "
        "Ni/Au-plated copper terminals",
        ".step",
    ),
    **{
        f"Harwin_Datamate_{p}": (
            f"https://www.harwin.com/products/{p}",
            M80_BASIS + f"; {p} has {v[0]} contacts in {v[1]} row(s), a {v[2]:.2f}mm housing and "
            f"{v[7]} fixings at x +/-{v[8]:.2f}mm which sit above the seating plane",
            ".step",
        )
        for p, v in {
            "M80-5001642": (16, 2, 26.00, -2.775, 3.275, 5.55, 3.30, "jackscrew", 10.50),
            "M80-5002042": (20, 2, 30.00, -2.775, 3.275, 5.55, 3.30, "jackscrew", 12.50),
            "M80-5T10442MC": (4, 2, 14.00, -2.775, 3.275, 5.55, 3.30, "101-Lok retainer", 4.50),
            "M80-8531642": (16, 2, 19.50, -3.075, 2.775, 5.40, 3.30, "latch", 9.35),
            "M80-8672022": (20, 2, 23.50, -3.075, 2.775, 5.40, 3.30, "latch", 11.35),
            "M80-8770222": (2, 1, 7.50, -2.075, 1.775, 5.40, 3.30, "latch", 3.35),
        }.items()
    },
    "Molex_Mini50_34825-0160_2x08_P2.00mm_Vertical": (
        "https://www.molex.com/en-us/products/part-detail/348250160",
        MOLEX_MINI50_DUAL_BASIS + "; body length 24.40 and post spacing 23.70 for the 16-way",
        ".step",
    ),
    "Molex_Mini50_34825-0200_2x10_P2.00mm_Vertical": (
        "https://www.molex.com/en-us/products/part-detail/348250200",
        MOLEX_MINI50_DUAL_BASIS + "; body length 28.40 and post spacing 27.70 for the 20-way",
        ".step",
    ),
    "Molex_Mini50_34792_1x04": (
        "https://www.molex.com/en-us/products/part-detail/347920041",
        "Molex sales drawing SD-34792-001 (MINI50 4-8CKT VERTICAL HDR): 2.00 pitch, 1.00 "
        "contact holes, 0.40 x 0.50 blades, DIM E post holes 2.15 press fit / 2.55 drop in, "
        "11.70 post spacing, posts 2.55 to -Y of the contact row, 9.94 body width and a "
        "height above PCB dimensioned as 8.16 + 6.44 = 14.60; body length 14.62 taken as the "
        "toleranced overall length on that sheet",
        ".step",
    ),
    "Harwin_Gecko_G125-MV12005M2P": (
        HARWIN_GECKO_M2P_DRAWING,
        "Harwin customer information sheet DRG-02638 issue 3, Table 1 row G125-MV12005M2P: "
        "DIM 'A' 19.05 stud spacing, DIM 'B' 11.25 contact span, DIM 'C' 23.95 body length, "
        "with the 4.90 body width, 1.25 pitch and row spacing, 0.40 contact section, "
        "3.0 PCB termination and 5.0 board mount stud from the same sheet",
        ".step",
    ),
    "Harwin_Gecko_G125-MV10605M2P": (
        HARWIN_GECKO_M2P_DRAWING,
        "Harwin customer information sheet DRG-02638 issue 3, Table 1 row G125-MV10605M2P: "
        "DIM 'A' 10.30 stud spacing, DIM 'B' 2.50 contact span, DIM 'C' 15.20 body length, "
        "sharing the 4.90 x 4.30 cross-section of the 20-way",
        ".step",
    ),
    "JST_XH_B20B-XH-A_1x20_P2.50mm_Vertical": (
        "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
        "JST XH series dimensions: 2.50 pitch, contact span A = (n - 1) x 2.50 = 47.50, "
        "moulded body B = A + 4.90 = 52.40 x 5.75 offset 2.35 / 3.40 about the contact row, "
        "7.00 shroud above the PCB and 3.40 tails below. The published PDF stores its "
        "dimension digits in a font subset that does not extract as text, so these come from "
        "the series relations and were cross-checked numerically against an independent "
        "public footprint",
        ".step",
    ),
    "BQ79606A-Q1": (
        "https://www.ti.com/lit/gpn/bq79606a-q1",
        "Texas Instruments PHP0048N 48-pin PowerPAD HTQFP package dimensions",
        ".step",
    ),
    "INA286_SOIC-8": (
        "https://www.ti.com/lit/gpn/ina286",
        "Texas Instruments D0008A SOIC-8 package dimensions",
        ".step",
    ),
    "STB45N65M5_D2PAK": (
        "https://www.st.com/resource/en/datasheet/stb45n65m5.pdf",
        "STMicroelectronics D2PAK TO-263 type A2 package dimensions",
        ".step",
    ),
    "CSS2H-3920R-L200F": (
        "https://www.bourns.com/products/resistors/details/metal-strip/css2h-3920",
        "Bourns CSS2H-3920R-L200F product dimensions and four-terminal construction",
        ".step",
    ),
    "1N6263W_SOD-123": (
        "https://www.diodes.com/part/view/1N6263W",
        "Diodes Incorporated 1N6263W SOD-123 package dimensions",
        ".step",
    ),
    "ACS781LLRTR-100U-T": (
        "https://www.allegromicro.com/-/media/files/datasheets/acs781-datasheet.pdf",
        "Allegro DWG-0000428 LR package dimensions",
        ".step",
    ),
    "BVN-M-R001-1.0": (
        "https://www.isabellenhuette.com/hubfs/Files/Data-sheets/BVN.pdf",
        "Isabellenhuette BVN size 1216 dimensions and illustrated Kelvin terminals, with user-clarified formed legs; issue 2024-10-09",
        ".step",
    ),
    "WE_7460305": (
        "https://www.we-online.com/components/products/datasheet/7460305.pdf",
        "Wurth 7460305 mechanical and press-fit dimensions",
        ".step",
    ),
    "INA190A3IDDFR_DDF": (
        "https://www.ti.com/lit/gpn/ina190",
        "Texas Instruments DDF 8-pin package dimensions",
        ".step",
    ),
    "PG-HSOG-8-1_INF": (
        "https://www.infineon.com/dgdl/Infineon-IPTG054N15NM5-DataSheet-v02_00-EN.pdf?fileId=8ac78c8c81ae03fc0181d36b00225f6f",
        "Infineon PG-HSOG-8-1 package dimensions",
        ".step",
    ),
    "IRS2186S_SOIC-8": (
        "https://www.infineon.com/dgdl/irs2186pbf.pdf?fileId=5546d462533600a40153567716c427ed",
        "Infineon IRS2186S 8-lead SOIC package dimensions",
        ".step",
    ),
    "L_Wuerth_WE-PD-Typ-LS": (
        "https://www.we-online.com/components/products/datasheet/7447709271.pdf",
        "Wurth 7447709271 WE-PD size 1210 package dimensions, revision 003.001 dated 2024-05-08",
        ".step",
    ),
    "L_Wuerth_WE-PD-Robust-7332": (
        "https://www.we-online.com/components/products/datasheet/7447789222.pdf",
        "Wurth 7447789222 WE-PD Robust size 7332 package dimensions, revision 006.000 dated 2023-05-30",
        ".step",
    ),
    "LTC3639_MSE16-12": (
        "https://www.analog.com/media/en/technical-documentation/data-sheets/3639fd.pdf",
        "Analog Devices MSE Package variation MSE16(12) dimensions, LTC DWG 05-08-1871 Rev D",
        ".step",
    ),
    "LFXTAL016178REEL": (
        "https://www.iqdfrequencyproducts.com/products/pn/LFXTAL016178.pdf",
        "IQD 85SMX package dimensions",
        ".step",
    ),
    "LM2576HV_TO-263-5": (
        "https://www.ti.com/lit/gpn/lm2576hv",
        "Texas Instruments KTT / DDPAK TO-263-5 dimensions",
        ".step",
    ),
    "LM2596S_TO-263-5": (
        "https://www.ti.com/lit/gpn/lm2596",
        "Texas Instruments KTT / DDPAK TO-263-5 dimensions",
        ".step",
    ),
    "NCS213R_SC70-6": (
        "https://www.onsemi.com/pdf/datasheet/ncs210r-d.pdf",
        "onsemi SC-88 / SC70-6 case 419B dimensions",
        ".step",
    ),
    "Power_Pad_6x6mm": (
        "NOASSERTION",
        "Original generic 6 x 6 mm copper contact definition",
        ".step",
    ),
}

BLACK = (0.10, 0.10, 0.11)
DARK_GREY = (0.20, 0.20, 0.22)
METAL = (0.76, 0.76, 0.72)
TIN = (0.82, 0.82, 0.78)
COPPER = (0.78, 0.42, 0.18)
GOLD = (0.88, 0.68, 0.18)
WHITE = (0.92, 0.92, 0.88)


def safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if result and result[0].isdigit():
        result = "Model_" + result
    return result


def carve(body, *cutters):
    """Subtract the terminals and markings from the body solid.

    Each model below builds a full-size body and then places terminals and
    markings that occupy the same space. Overlapping volumes put two surfaces
    at the same point, which renders as z-fighting: the colours flicker and
    smear as the model is rotated. Cutting the body so that every solid is
    mutually exclusive fixes that without moving a single outer dimension -
    the bounding box and every feature position are unchanged, only the hidden
    interior of the body is removed.
    """
    return body.cut(Part.makeCompound(list(cutters)))


def centered_box(width: float, depth: float, height: float, z: float = 0.0) -> Part.Shape:
    return Part.makeBox(width, depth, height, App.Vector(-width / 2, -depth / 2, z))


def box_at(x: float, y: float, width: float, depth: float, height: float, z: float = 0.0) -> Part.Shape:
    return Part.makeBox(width, depth, height, App.Vector(x - width / 2, y - depth / 2, z))


def gull_wing_lead(sign: float, y: float, span: float, foot: float, thickness: float,
                   shoulder_z: float, body_edge: float, width: float) -> Part.Shape:
    """One formed gull-wing lead, extruded from a constant-thickness outline.

    The outline is built from the package drawing alone: the flat foot of length
    `foot` sits on the seating plane and reaches out to `span`, a 45 degree bend
    lifts the lead to `shoulder_z`, and the shoulder runs back past `body_edge`
    so the terminal stays fused to the moulded body.  Both bend faces are the
    same line offset by `thickness` measured perpendicular, which keeps the lead
    a true constant thickness rather than a stack of boxes.
    """
    heel = span - foot
    lower = heel                                   # lower bend face:  x + z = heel
    upper = heel + thickness * math.sqrt(2.0)      # upper bend face, offset by t
    shoulder_bottom = shoulder_z - thickness
    outline = [
        (span, 0.0),
        (heel, 0.0),
        (lower - shoulder_bottom, shoulder_bottom),
        (body_edge, shoulder_bottom),
        (body_edge, shoulder_z),
        (upper - shoulder_z, shoulder_z),
        (upper - thickness, thickness),
        (span, thickness),
    ]
    points = [App.Vector(sign * x, y - width / 2, z) for x, z in outline]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, width, 0))


def rounded_box(width: float, depth: float, height: float, radius: float, z: float = 0.0) -> Part.Shape:
    """Make a robust rounded rectangle prism without relying on edge ordering."""
    radius = min(radius, width / 2, depth / 2)
    shape = Part.makeBox(width - 2 * radius, depth, height, App.Vector(-width / 2 + radius, -depth / 2, z))
    shape = shape.fuse(Part.makeBox(width, depth - 2 * radius, height, App.Vector(-width / 2, -depth / 2 + radius, z)))
    for x in (-width / 2 + radius, width / 2 - radius):
        for y in (-depth / 2 + radius, depth / 2 - radius):
            shape = shape.fuse(Part.makeCylinder(radius, height, App.Vector(x, y, z)))
    return shape


def add_properties(obj: App.DocumentObject, source: str, dimensional_basis: str) -> None:
    properties = {
        "Author": AUTHOR,
        "Copyright": COPYRIGHT,
        "SPDX_License": LICENSE,
        "License_File": "LICENSES/CERN-OHL-P-2.0.txt",
        "Source": source,
        "Dimensional_Basis": dimensional_basis,
        "Generator": GENERATOR,
        "Units": "millimetres",
        "Notice": "Original model; no third-party CAD geometry was used.",
    }
    for name, value in properties.items():
        if name not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", name, "Licensing and Provenance")
        setattr(obj, name, value)


class ModelDocument:
    def __init__(self, name: str):
        self.name = name
        self.source, self.dimensional_basis, self.extension = SOURCES[name]
        self.doc = App.newDocument(safe_name(name))
        self.root = self.doc.addObject("App::Part", "Component")
        self.root.Label = name
        add_properties(self.root, self.source, self.dimensional_basis)

        # FreeCAD's own document properties, which default to "All rights
        # reserved" and otherwise contradict the repository licence
        self.doc.License = LICENSE
        self.doc.LicenseURL = "https://ohwr.org/cern_ohl_p_v2.txt"

        self.metadata = self.doc.addObject("App::FeaturePython", "License_Metadata")
        self.metadata.Label = f"License Metadata ({LICENSE})"
        add_properties(self.metadata, self.source, self.dimensional_basis)
        self.root.addObject(self.metadata)

        self.groups = {}
        for internal, label in (
            ("Package", "Package"),
            ("Terminals", "Terminals"),
            ("Markings", "Markings"),
        ):
            group = self.doc.addObject("App::Part", internal)
            group.Label = label
            self.root.addObject(group)
            self.groups[internal] = group
        self.export_objects = []
        self.export_colors: dict[str, tuple[float, float, float]] = {}

    def feature(self, group: str, name: str, label: str, shape: Part.Shape, color) -> App.DocumentObject:
        obj = self.doc.addObject("Part::Feature", safe_name(name))
        obj.Label = label
        obj.Shape = shape
        obj.addProperty("App::PropertyString", "Function", "Model")
        obj.Function = group
        obj.addProperty("App::PropertyString", "Model_License", "Licensing and Provenance")
        obj.Model_License = LICENSE
        # ViewObject is unavailable in some headless FreeCADCmd builds. The
        # geometry and model tree remain complete; GUI runs additionally store
        # the intended display colours in the FCStd document. The colour is
        # recorded here either way so a headless export can still write STEP
        # presentation styles (see apply_step_colors).
        display_color = BLACK if group == "Package" else color
        self.export_colors[safe_name(name)] = display_color
        if obj.ViewObject is not None:
            obj.ViewObject.ShapeColor = display_color
            obj.ViewObject.LineColor = tuple(min(1.0, channel + 0.12) for channel in display_color)
        self.groups[group].addObject(obj)
        self.export_objects.append(obj)
        return obj

    def finish(self) -> tuple[Path, Path, tuple[float, float, float], int]:
        self.doc.recompute()
        for obj in self.export_objects:
            if obj.Shape.isNull() or not obj.Shape.isValid():
                raise RuntimeError(f"Invalid shape in {self.name}: {obj.Label}")

        fcstd = SOURCE_DIR / f"{self.name}.FCStd"
        step = MODEL_DIR / f"{self.name}{self.extension}"
        # Removing the prior generated project prevents FreeCAD from creating
        # timestamped FCBak files on a reproducible regeneration run.
        if fcstd.exists():
            fcstd.unlink()
        self.doc.saveAs(str(fcstd))
        if App.GuiUp:
            import ImportGui
            ImportGui.export(self.export_objects, str(step))
        else:
            Import.export(self.export_objects, str(step))
            apply_step_colors(step, self.export_objects, self.export_colors)
        add_step_license_header(step, self.name, self.source, self.dimensional_basis)

        compound = Part.makeCompound([obj.Shape for obj in self.export_objects])
        bounds = compound.BoundBox
        dimensions = (bounds.XLength, bounds.YLength, bounds.ZLength)
        solids = sum(len(obj.Shape.Solids) for obj in self.export_objects)
        App.closeDocument(self.doc.Name)
        return fcstd, step, dimensions, solids


def apply_step_colors(path: Path, objects: Sequence[App.DocumentObject],
                      colors: dict[str, tuple[float, float, float]]) -> None:
    """Write AP214 presentation styles into a headless STEP export.

    Only ImportGui writes colours, and it reads them from ViewObject, which the
    bundled FreeCADCmd interpreter never creates. Rather than leaving headless
    runs colourless, the style entities are appended here.

    Solids are matched to objects by export order using each object's own solid
    count, and the total is checked against the breps actually written, so a
    model change that reorders solids fails loudly instead of mis-colouring.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    brep_order = re.findall(r"#(\d+) = MANIFOLD_SOLID_BREP", text)

    expected: list[str] = []
    for obj in objects:
        expected.extend([obj.Name] * len(obj.Shape.Solids))
    if len(expected) != len(brep_order):
        raise RuntimeError(
            f"{path.name}: {len(brep_order)} breps in STEP but {len(expected)} solids "
            "in the model; refusing to guess colours"
        )
    if not expected:
        return

    # A single-solid object exports as ADVANCED_BREP_SHAPE_REPRESENTATION, a
    # compound as SHAPE_REPRESENTATION with every brep in one item list wrapped
    # over many lines, so whole statements are parsed rather than lines.
    data = text.split("DATA;", 1)[1].split("ENDSEC;", 1)[0]
    rep_types = {
        "ADVANCED_BREP_SHAPE_REPRESENTATION",
        "SHAPE_REPRESENTATION",
        "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
    }
    context_of: dict[str, str] = {}
    for statement in data.split(";"):
        head = re.match(r"\s*#\d+\s*=\s*(\w+)\s*\((.*)\)\s*$", statement, re.DOTALL)
        if not head or head.group(1) not in rep_types:
            continue
        args = re.match(r"\s*'[^']*'\s*,\s*\((.*)\)\s*,\s*#(\d+)\s*$", head.group(2), re.DOTALL)
        if not args:
            continue
        for item in re.findall(r"#(\d+)", args.group(1)):
            context_of[item] = args.group(2)

    next_id = max(int(n) for n in re.findall(r"^#(\d+) =", text, re.MULTILINE)) + 1
    colour_ids: dict[str, int] = {}
    lines: list[str] = []
    for name in dict.fromkeys(expected):
        red, green, blue = colors.get(name, METAL)
        colour_ids[name] = next_id
        lines.append(f"#{next_id} = COLOUR_RGB('',{red:.12g},{green:.12g},{blue:.12g});")
        next_id += 1

    for brep, owner in zip(brep_order, expected):
        context = context_of.get(brep)
        if context is None:
            raise RuntimeError(f"{path.name}: no representation context for brep #{brep}")
        rep, styled, assignment, usage, side, fill, style, colour = range(next_id, next_id + 8)
        next_id += 8
        lines += [
            f"#{rep} = MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(",
            f"    #{styled}),#{context});",
            f"#{styled} = STYLED_ITEM('color',(#{assignment}),#{brep});",
            f"#{assignment} = PRESENTATION_STYLE_ASSIGNMENT((#{usage}));",
            f"#{usage} = SURFACE_STYLE_USAGE(.BOTH.,#{side});",
            f"#{side} = SURFACE_SIDE_STYLE('',(#{fill}));",
            f"#{fill} = SURFACE_STYLE_FILL_AREA(#{style});",
            f"#{style} = FILL_AREA_STYLE('',(#{colour}));",
            f"#{colour} = FILL_AREA_STYLE_COLOUR('',#{colour_ids[owner]});",
        ]

    trailer = "\nENDSEC;\nEND-ISO-10303-21;"
    if trailer not in text:
        raise RuntimeError(f"{path.name}: unexpected STEP trailer; cannot append styles")
    path.write_text(text.replace(trailer, "\n" + "\n".join(lines) + trailer, 1),
                    encoding="utf-8", newline="\n")


def add_step_license_header(path: Path, name: str, source: str, dimensional_basis: str) -> None:
    """Put machine-readable licensing and provenance in the ISO-10303 header."""
    content = path.read_text(encoding="utf-8", errors="replace")
    description = (
        f"Original {name} model | SPDX-License-Identifier: {LICENSE} | "
        f"{COPYRIGHT} | Source: {source} | {dimensional_basis}"
    ).replace("'", "")
    file_description = f"FILE_DESCRIPTION(('{description}'),'2;1');"
    file_name = (
        f"FILE_NAME('{path.name}','2026-07-11T00:00:00',('{AUTHOR}'),"
        f"('{AUTHOR}'),'FreeCAD 1.1.1','{GENERATOR}','{LICENSE}');"
    )
    content = re.sub(r"FILE_DESCRIPTION\s*\(.*?\);", file_description, content, count=1, flags=re.DOTALL)
    content = re.sub(r"FILE_NAME\s*\(.*?\);", file_name, content, count=1, flags=re.DOTALL)
    if LICENSE not in content or COPYRIGHT not in content:
        raise RuntimeError(f"Could not embed licensing in {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def make_acs781(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "Moulded body", rounded_box(6.40, 4.80, 1.32, 0.38, 0.18), BLACK)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.16, 0.025, App.Vector(2.30, 1.45, 1.49)), DARK_GREY)
    terminals = {
        "Pin_1_VCC": (-1.60, 2.40, 0.38, 1.60),
        "Pin_2_GND": (0.00, 2.40, 0.38, 1.60),
        "Pin_3_VOUT": (1.60, 2.40, 0.38, 1.60),
        "Pin_4_NC": (2.80, 0.00, 0.90, 0.38),
        "Pin_5_IP_Plus": (1.50, -2.40, 1.79, 1.70),
        "Pin_6_IP_Minus": (-1.50, -2.40, 1.79, 1.70),
        "Pin_7_NC": (-2.80, 0.00, 0.90, 0.38),
    }
    for label, (x, y, width, depth) in terminals.items():
        model.feature("Terminals", label, label.replace("_", " "), box_at(x, y, width, depth, 0.38), METAL)


def make_bvn(model: ModelDocument) -> None:
    """BVN 1216 four-terminal shunt, aligned to the recommended land pattern."""
    # The landing faces are kept within the 4.1 x 3.1 mm component envelope;
    # the larger copper lands themselves belong to the footprint.
    model.feature("Terminals", "Current_1", "Current terminal 1", box_at(-1.05, -0.70, 1.00, 2.70, 0.18), COPPER)
    model.feature("Terminals", "Current_4", "Current terminal 4", box_at(1.05, -0.70, 1.00, 2.70, 0.18), COPPER)
    model.feature("Terminals", "Current_Post_1", "Current terminal 1 formed post", box_at(-1.05, -0.70, 0.90, 2.35, 1.45, 0.18), COPPER)
    model.feature("Terminals", "Current_Post_4", "Current terminal 4 formed post", box_at(1.05, -0.70, 0.90, 2.35, 1.45, 0.18), COPPER)
    for pin, x in ((2, -1.05), (3, 1.05)):
        sense_pad = box_at(x, 1.75, 0.50, 0.60, 0.18)
        upper_arm = box_at(x, 0.99, 0.25, 1.08, 0.18, 1.20)
        down_leg = box_at(x, 1.50, 0.25, 0.18, 1.20, 0.18)
        formed_leg = sense_pad.fuse(upper_arm).fuse(down_leg)
        model.feature(
            "Terminals", f"Kelvin_Leg_{pin}", f"Kelvin sense terminal {pin} with formed leg",
            formed_leg, COPPER,
        )
    model.feature("Package", "Manganin_Element", "MANGANIN resistive element", rounded_box(3.10, 0.80, 0.27, 0.08, 1.63), DARK_GREY)


def make_we_7460305(model: ModelDocument) -> None:
    body = rounded_box(9.0, 9.0, 8.0, 0.45, 0.15)
    boss = Part.makeCylinder(4.0, 2.0, App.Vector(0, 0, 8.15))
    thread_hole = Part.makeCylinder(2.5, 7.0, App.Vector(0, 0, 4.0))
    model.feature("Package", "Copper_Terminal_Body", "Copper terminal body", body.fuse(boss).cut(thread_hole), COPPER)
    for row, y in enumerate((-3.81, 3.81), 1):
        for col, x in enumerate((-3.81, -1.27, 1.27, 3.81), 1):
            pin = Part.makeCylinder(0.61, 3.2, App.Vector(x, y, -3.05))
            model.feature("Terminals", f"PressFit_{row}_{col}", f"Press-fit peg {row}.{col}", pin, TIN)
    model.feature("Markings", "M5_Thread_Reference", "M5 threaded opening", Part.makeCylinder(2.48, 0.04, App.Vector(0, 0, 9.98)), DARK_GREY)


def make_ina190(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "DDF moulded body", rounded_box(1.60, 2.90, 0.90, 0.15, 0.15), BLACK)
    ys = (-0.975, -0.325, 0.325, 0.975)
    for pin, y in enumerate(ys, 1):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(-1.30, y, 1.05, 0.30, 0.15), METAL)
    for pin, y in zip(range(5, 9), reversed(ys)):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(1.30, y, 1.05, 0.30, 0.15), METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.11, 0.025, App.Vector(0.48, -1.02, 1.05)), WHITE)


def make_toll(model: ModelDocument) -> None:
    # PG-HSOG-8-U01 nominal package values: E1=8.60, D=9.90,
    # E2=6.81 minimum, D1=9.46, A=2.30, A1=0.05, b=0.70 and e=1.20 mm.
    # E=11.70 mm is the overall body-plus-lead length, not the moulded body.
    model.feature(
        "Terminals", "Drain_9", "Exposed drain pad 9",
        box_at(2.0305, 0, 6.81, 9.46, 0.10), COPPER,
    )
    model.feature(
        "Package", "Moulded_Body", "PG-HSOG-8-1 moulded body",
        rounded_box(8.60, 9.90, 2.20, 0.35, 0.10).translated(App.Vector(1.1355, 0, 0)), BLACK,
    )
    for pin in range(1, 9):
        y = 4.2 - (pin - 1) * 1.2
        contact = box_at(-5.00, y, 2.80, 0.70, 0.10)
        formed_inner = box_at(-3.38225, y, 0.4355, 0.70, 0.20, 0.10)
        model.feature(
            "Terminals", f"Pin_{pin}", f"Pin {pin}",
            contact.fuse(formed_inner), METAL,
        )
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.20, 0.03, App.Vector(-2.4, 4.15, 2.30)), WHITE)


def make_soic8(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "SOIC-8 moulded body", rounded_box(3.90, 4.90, 1.45, 0.20, 0.22), BLACK)
    ys = (-1.905, -0.635, 0.635, 1.905)
    for pin, y in enumerate(ys, 1):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(-2.50, y, 1.10, 0.48, 0.20), METAL)
    for pin, y in zip(range(5, 9), reversed(ys)):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(2.50, y, 1.10, 0.48, 0.20), METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.18, 0.03, App.Vector(1.20, -1.60, 1.67)), WHITE)


def make_we_pd_typ_ls(model: ModelDocument) -> None:
    """WE-PD 1210 shielded inductor built only from datasheet dimensions."""
    model.feature("Terminals", "Terminal_1", "Terminal 1 (start of winding)", box_at(-5.00, 0, 2.00, 5.00, 0.25), TIN)
    model.feature("Terminals", "Terminal_2", "Terminal 2", box_at(5.00, 0, 2.00, 5.00, 0.25), TIN)
    model.feature("Terminals", "Wrap_1", "Terminal 1 side wrap", box_at(-5.90, 0, 0.20, 5.00, 1.20, 0.25), TIN)
    model.feature("Terminals", "Wrap_2", "Terminal 2 side wrap", box_at(5.90, 0, 0.20, 5.00, 1.20, 0.25), TIN)
    model.feature("Package", "Shielded_Core", "Shielded ferrite core", rounded_box(12.00, 12.00, 9.20, 1.10, 0.25), DARK_GREY)
    model.feature("Package", "Top_Cap", "Ferrite top cap", rounded_box(10.80, 10.80, 0.35, 1.00, 9.45), BLACK)
    model.feature("Package", "Top_Centre", "Circular top centre", Part.makeCylinder(4.70, 0.20, App.Vector(0, 0, 9.80)), DARK_GREY)
    model.feature("Markings", "Start_Of_Winding", "Start-of-winding dot", Part.makeCylinder(0.22, 0.02, App.Vector(-4.20, 4.20, 9.98)), WHITE)


def make_we_pd_robust_7332(model: ModelDocument) -> None:
    """WE-PD Robust 7332 shielded inductor built only from datasheet dimensions.

    Body 7.30 x 7.30 x 3.20 mm; the bottom terminations match the manufacturer
    land pattern of two 1.70 x 2.00 mm pads separated by a 4.00 mm gap.
    """
    model.feature("Terminals", "Terminal_1", "Terminal 1 (start of winding)", box_at(-2.85, 0, 1.70, 2.00, 0.25), TIN)
    model.feature("Terminals", "Terminal_2", "Terminal 2", box_at(2.85, 0, 1.70, 2.00, 0.25), TIN)
    model.feature("Terminals", "Wrap_1", "Terminal 1 side wrap", box_at(-3.55, 0, 0.20, 2.00, 0.70, 0.25), TIN)
    model.feature("Terminals", "Wrap_2", "Terminal 2 side wrap", box_at(3.55, 0, 0.20, 2.00, 0.70, 0.25), TIN)
    model.feature("Package", "Shielded_Core", "Shielded ferrite core", rounded_box(7.30, 7.30, 2.65, 0.70, 0.25), DARK_GREY)
    model.feature("Package", "Top_Cap", "Ferrite top cap", rounded_box(6.60, 6.60, 0.25, 0.60, 2.90), BLACK)
    model.feature("Package", "Top_Centre", "Circular top centre", Part.makeCylinder(2.80, 0.05, App.Vector(0, 0, 3.15)), DARK_GREY)
    model.feature("Markings", "Start_Of_Winding", "Start-of-winding dot", Part.makeCylinder(0.20, 0.02, App.Vector(-2.60, 2.60, 3.18)), WHITE)


def make_ltc3639(model: ModelDocument) -> None:
    """LTC3639 in the MSE16(12) package, from the LTC DWG 05-08-1871 Rev D outline.

    Body 3.00 x 4.039 mm with A1 = 0.10 mm standoff and A2 = 0.86 mm moulded
    thickness, 0.50 mm lead pitch and 4.90 mm lead span, with pins 2, 4, 13 and
    15 removed and a 1.651 x 2.845 mm exposed die pad.  Leads use b = 0.22 mm
    width (drawing 0.17 - 0.27 typical), c = 0.18 mm thickness and L = 0.53 mm
    foot length, formed up to a 0.52 mm shoulder so they meet the body.
    """
    model.feature("Package", "Body", "Moulded body", rounded_box(3.00, 4.039, 0.86, 0.15, 0.10), BLACK)
    # The exposed pad is coplanar with the lead feet and fills the A1 standoff.
    model.feature("Terminals", "Exposed_Pad", "Exposed die pad", box_at(0, 0, 1.651, 2.845, 0.10), TIN)
    # Eight lead sites on a 0.50 mm pitch; pins 2, 4, 13 and 15 are absent.
    # KiCad renders a STEP model with its Y axis mirrored relative to the
    # footprint, so the model is built at -Y to line the leads up with the pads.
    sites = [-(-1.75 + index * 0.50) for index in range(8)]
    left_pins = {0: 1, 2: 3, 4: 5, 5: 6, 6: 7, 7: 8}
    right_pins = {7: 9, 6: 10, 5: 11, 4: 12, 2: 14, 0: 16}
    for sign, mapping in ((-1.0, left_pins), (1.0, right_pins)):
        for index, number in sorted(mapping.items()):
            model.feature(
                "Terminals", f"Lead_{number}", f"Lead {number}",
                gull_wing_lead(
                    sign, sites[index],
                    span=2.45,          # half of the 4.90 mm lead span
                    foot=0.53,          # L, flat contact length on the seating plane
                    thickness=0.18,     # c, lead frame thickness
                    shoulder_z=0.52,    # top of the lead where it meets the body
                    body_edge=1.45,     # just inside the 1.50 mm body wall
                    width=0.22,         # b, mid of the 0.17 - 0.27 mm drawing range
                ),
                TIN,
            )
    model.feature(
        "Markings", "Pin_1_Marker", "Pin 1 marker",
        Part.makeCylinder(0.16, 0.02, App.Vector(-1.00, 1.50, 0.95)), DARK_GREY,
    )


def make_crystal(model: ModelDocument) -> None:
    model.feature("Package", "Ceramic_Base", "Ceramic base", rounded_box(7.90, 3.80, 0.45, 0.25, 0.15), DARK_GREY)
    model.feature("Package", "Metal_Can", "85SMX metal can", rounded_box(7.45, 3.35, 2.10, 0.55, 0.55), METAL)
    terminals = {1: (-2.75, 1.60), 2: (2.75, 1.60), 3: (2.75, -1.60), 4: (-2.75, -1.60)}
    for pin, (x, y) in terminals.items():
        model.feature("Terminals", f"Pad_{pin}", f"Terminal {pin}", box_at(x, y, 1.30, 1.25, 0.15), GOLD)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.16, 0.025, App.Vector(-3.05, -1.00, 2.65)), DARK_GREY)


def make_to263(model: ModelDocument) -> None:
    model.feature("Terminals", "Thermal_Tab_3", "Thermal tab (pin 3)", box_at(-3.495, 0, 6.99, 10.80, 0.24), METAL)
    model.feature("Package", "Moulded_Body", "TO-263-5 moulded body", rounded_box(8.64, 10.16, 4.00, 0.28, 0.24), BLACK)
    for pin in range(1, 6):
        y = 3.4 - (pin - 1) * 1.7
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(5.75, y, 3.10, 0.80, 0.24), METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.23, 0.03, App.Vector(2.85, -3.55, 4.24)), WHITE)


def make_sc70(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "SC70-6 moulded body", rounded_box(2.00, 1.25, 0.85, 0.12, 0.15), BLACK)
    coordinates = {1: (-0.65, 0.92), 2: (0, 0.92), 3: (0.65, 0.92), 4: (0.65, -0.92), 5: (0, -0.92), 6: (-0.65, -0.92)}
    for pin, (x, y) in coordinates.items():
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(x, y, 0.30, 0.66, 0.15), METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.10, 0.025, App.Vector(-0.62, -0.33, 1.0)), WHITE)


def make_power_pad(model: ModelDocument) -> None:
    model.feature("Terminals", "Copper_Contact", "6 x 6 mm copper contact", rounded_box(6.0, 6.0, 0.25, 0.18, 0.0), COPPER)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 corner mark", box_at(-2.55, 2.55, 0.35, 0.35, 0.03, 0.25), GOLD)


def make_bq79606(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "PHP0048N moulded body", rounded_box(7.0, 7.0, 1.02, 0.25, 0.18), BLACK)
    positions = [-2.75 + index * 0.5 for index in range(12)]
    for pin, y in enumerate(positions, 1):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(-3.75, y, 1.50, 0.27, 0.16), METAL)
    for pin, x in zip(range(13, 25), positions):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(x, 3.75, 0.27, 1.50, 0.16), METAL)
    for pin, y in zip(range(25, 37), reversed(positions)):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(3.75, y, 1.50, 0.27, 0.16), METAL)
    for pin, x in zip(range(37, 49), reversed(positions)):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(x, -3.75, 0.27, 1.50, 0.16), METAL)
    model.feature("Terminals", "PowerPAD_49", "Exposed PowerPAD 49", box_at(0, 0, 5.17, 5.17, 0.18), COPPER)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.18, 0.025, App.Vector(-2.65, -2.65, 1.20)), WHITE)


def make_ina286(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "D0008A SOIC-8 moulded body", rounded_box(3.90, 4.90, 1.45, 0.20, 0.20), BLACK)
    ys = (-1.905, -0.635, 0.635, 1.905)
    for pin, y in enumerate(ys, 1):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(-2.50, y, 1.10, 0.45, 0.20), METAL)
    for pin, y in zip(range(5, 9), reversed(ys)):
        model.feature("Terminals", f"Pin_{pin}", f"Pin {pin}", box_at(2.50, y, 1.10, 0.45, 0.20), METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.18, 0.03, App.Vector(1.20, -1.60, 1.65)), WHITE)


def make_stb45n65(model: ModelDocument) -> None:
    model.feature("Terminals", "Drain_Tab_2", "Drain tab pin 2", box_at(0, -3.575, 10.20, 9.10, 0.22), METAL)
    model.feature("Package", "Moulded_Body", "D2PAK moulded body", rounded_box(10.20, 9.10, 4.18, 0.25, 0.22), BLACK)
    for pin, x, label in ((1, -2.54, "Gate"), (3, 2.54, "Source")):
        lead = box_at(x, 5.775, 1.10, 4.00, 0.22)
        model.feature("Terminals", f"Pin_{pin}_{label}", f"Pin {pin} {label.lower()}", lead, METAL)
    model.feature("Markings", "Pin_1_Marker", "Pin 1 marker", Part.makeCylinder(0.25, 0.03, App.Vector(3.65, 1.0, 4.40)), WHITE)


def make_css2h(model: ModelDocument) -> None:
    model.feature("Terminals", "Current_Terminal_1", "Current terminal 1", box_at(-4.40, 0, 1.20, 5.20, 0.22), COPPER)
    model.feature("Terminals", "Current_Terminal_2", "Current terminal 2", box_at(4.40, 0, 1.20, 5.20, 0.22), COPPER)
    model.feature("Terminals", "Sense_Terminal_1", "Kelvin sense terminal 1", box_at(-0.45, 0, 0.45, 5.20, 0.22), COPPER)
    model.feature("Terminals", "Sense_Terminal_2", "Kelvin sense terminal 2", box_at(0.45, 0, 0.45, 5.20, 0.22), COPPER)
    model.feature("Package", "Copper_Base", "Copper alloy base", rounded_box(8.80, 5.20, 0.22, 0.12, 0.22), COPPER)
    model.feature("Package", "Resistive_Strip", "Cu-Mn resistive strip", rounded_box(5.60, 4.60, 2.07, 0.30, 0.44), DARK_GREY)
    model.feature("Markings", "Part_Marking", "Part marking plate", box_at(0, 0, 3.80, 1.50, 0.025, 2.485), WHITE)


def make_bourns_sod323(model: ModelDocument) -> None:
    """Original three-solid, unbanded, bidirectional SOD-323 package."""
    leads = [gull_wing_lead(sign, 0, 1.30, 0.35, 0.14, 0.45, 0.60, 0.35)
             for sign in (-1.0, 1.0)]
    body = carve(rounded_box(1.80, 1.40, 0.99, 0.06, 0.06), *leads)
    model.feature("Package", "Body", "Bidirectional SOD-323 moulded body", body, BLACK)
    for number, lead in enumerate(leads, 1):
        model.feature("Terminals", f"Terminal_{number}", f"Terminal {number}", lead, TIN)


def make_1n6263w(model: ModelDocument) -> None:
    model.feature("Package", "Moulded_Body", "SOD-123 moulded body", rounded_box(2.65, 1.55, 1.05, 0.10, 0.10), BLACK)
    model.feature("Terminals", "Cathode_1", "Cathode pin 1", box_at(-1.54, 0, 0.57, 0.57, 0.10), METAL)
    model.feature("Terminals", "Anode_2", "Anode pin 2", box_at(1.54, 0, 0.57, 0.57, 0.10), METAL)
    model.feature("Markings", "Cathode_Band", "Cathode band", box_at(-0.85, 0, 0.22, 1.20, 0.025, 1.15), WHITE)


def make_szsmf_sod123fl(model: ModelDocument) -> None:
    """Littelfuse SZSMFxxA 200W TVS in SOD-123FL.

    Symmetric about the footprint Y axis, so the KiCad footprint/model Y mirror
    does not apply. Pin 1 is the cathode, marked with a band at that end.
    """
    body_x, body_y = 2.70, 1.65
    stand_off, height = 0.05, 0.95
    span, lead_w, foot, lead_t = 3.60, 0.90, 0.75, 0.15

    leads = []
    for sign in (-1.0, 1.0):
        outer = sign * span / 2.0
        x0 = min(outer, sign * (span / 2.0 - foot))
        leads.append(Part.makeBox(foot, lead_w, lead_t,
                                  App.Vector(x0, -lead_w / 2.0, 0.0)))
    leads = Part.makeCompound(leads)
    # cathode band at the pin 1 end
    band = Part.makeBox(0.35, body_y, 0.02,
                        App.Vector(-body_x / 2.0 + 0.10, -body_y / 2.0, height - 0.02))

    body = Part.makeBox(body_x, body_y, height - stand_off,
                        App.Vector(-body_x / 2.0, -body_y / 2.0, stand_off))
    body = carve(body, leads, band)
    model.feature("Package", "Body", "Moulded body", body, BLACK)
    model.feature("Terminals", "Leads", "Tin-plated flat leads", leads, TIN)
    model.feature("Markings", "Cathode_Band", "Cathode band", band, WHITE)


def make_schurter_1206_fuse(model: ModelDocument, width: float, height: float,
                            body_colour) -> None:
    """Schurter 1206 chip fuse body, shared by USF 1206 and MGA-A.

    Both are the same 3.20 mm long 1206 outline with 0.50 mm end metallisations
    and the same reflow land pattern; they differ in body width and material
    (fibre-reinforced plastic for USF, hermetic ceramic for MGA-A). The part is
    symmetric about both footprint axes, so the KiCad footprint/model Y mirror
    does not apply.
    """
    length = 3.20
    terminal = 0.50

    caps = []
    for sign in (-1.0, 1.0):
        caps.append(box_at(sign * (length - terminal) / 2.0, 0.0,
                           terminal, width, height))
    caps = Part.makeCompound(caps)
    # rating letter is printed on the top face
    marker = Part.makeCylinder(0.22, 0.02, App.Vector(0.0, 0.0, height - 0.02),
                               App.Vector(0, 0, 1))

    body = carve(centered_box(length, width, height), caps, marker)
    model.feature("Package", "Housing", "Fuse body", body, body_colour)
    model.feature("Terminals", "End_Caps", "Ni/Au-plated terminals", caps, GOLD)
    model.feature("Markings", "Rating_Mark", "Rating marking", marker, WHITE)


def make_smbj_do214aa(model: ModelDocument) -> None:
    """Bourns SMBJ-Q 600W TVS in DO-214AA (SMB).

    Symmetric about the footprint Y axis, so the KiCad footprint/model Y mirror
    does not apply. Pin 1 is the cathode, marked with a band at that end.
    """
    body_x, body_y = 4.57, 3.94
    stand_off, height = 0.20, 2.20
    span, lead_w, foot, lead_t = 5.59, 2.44, 1.52, 0.305

    leads = []
    for sign in (-1.0, 1.0):
        x0 = min(sign * span / 2.0, sign * (span / 2.0 - foot))
        # flat foot on the board
        heel = Part.makeBox(foot, lead_w, lead_t,
                            App.Vector(x0, -lead_w / 2.0, 0.0))
        # vertical wrap up the body end face - fused to the foot rather than
        # merely stacked on it, because the two overlap where they meet and
        # coincident volumes inside one compound z-fight just as badly as a
        # terminal buried in the body does
        wrap_x = sign * body_x / 2.0 - (lead_t if sign > 0 else 0.0)
        wrap = Part.makeBox(lead_t, lead_w, height * 0.6,
                            App.Vector(wrap_x, -lead_w / 2.0, 0.0))
        leads.append(heel.fuse(wrap).removeSplitter())
    leads = Part.makeCompound(leads)
    band = Part.makeBox(0.60, body_y, 0.02,
                        App.Vector(-body_x / 2.0 + 0.25, -body_y / 2.0, height - 0.02))

    body = Part.makeBox(body_x, body_y, height - stand_off,
                        App.Vector(-body_x / 2.0, -body_y / 2.0, stand_off))
    body = carve(body, leads, band)
    model.feature("Package", "Body", "Moulded epoxy body", body, BLACK)
    model.feature("Terminals", "Leads", "Tin-plated leads", leads, TIN)
    model.feature("Markings", "Cathode_Band", "Cathode band", band, WHITE)


def make_rcl1225_resistor(model: ModelDocument) -> None:
    """Vishay RCL1225 e3 long-side-termination 2W thick film resistor.

    Reverse geometry: the terminations run along the 6.3 mm side, so the
    current path is the short 3.2 mm dimension and the termination is wide.
    Symmetric about both footprint axes, so the KiCad footprint/model Y mirror
    does not apply.

    The drawing gives two termination figures, T1 0.8 and T2 0.4, without
    labelling which face each belongs to. T1 is taken as the band width on the
    solder side and T2 as the wrap on the top, which is the usual convention
    for a chip resistor and the conservative reading for clearance.
    """
    length, width, height = 3.20, 6.30, 0.70
    terminal = 0.80

    caps = []
    for sign in (-1.0, 1.0):
        caps.append(box_at(sign * (length - terminal) / 2.0, 0.0,
                           terminal, width, height))
    caps = Part.makeCompound(caps)

    # value code printed on the top face, between the terminations
    marker = Part.makeBox(length - 2.0 * terminal - 0.40, width * 0.45, 0.02,
                          App.Vector(-(length - 2.0 * terminal - 0.40) / 2.0,
                                     -width * 0.225, height - 0.02))

    body = carve(centered_box(length, width, height), caps, marker)
    model.feature("Package", "Body", "Alumina substrate with resistive film",
                  body, DARK_GREY)
    model.feature("Terminals", "End_Caps", "Tin-plated terminations", caps, TIN)
    model.feature("Markings", "Value_Code", "Printed value code", marker, WHITE)


def make_littelfuse_470(model: ModelDocument) -> None:
    """Littelfuse 470 Series 1206 thin-film chip fuse."""
    length, width, height = 3.302, 1.575, 1.168
    terminal = 0.50

    caps = []
    for sign in (-1.0, 1.0):
        caps.append(box_at(sign * (length - terminal) / 2.0, 0.0,
                           terminal, width, height))
    caps = Part.makeCompound(caps)
    marker = Part.makeCylinder(0.22, 0.02, App.Vector(0.0, 0.0, height - 0.02),
                               App.Vector(0, 0, 1))

    body = carve(centered_box(length, width, height), caps, marker)
    model.feature("Package", "Housing", "Epoxy resin body", body, BLACK)
    model.feature("Terminals", "End_Caps", "Cu/Ni/Sn terminations", caps, TIN)
    model.feature("Markings", "Rating_Mark", "Rating marking", marker, WHITE)


def make_usf1206_fuse(model: ModelDocument) -> None:
    make_schurter_1206_fuse(model, 1.60, 0.60, BLACK)


def make_mga_a_fuse(model: ModelDocument) -> None:
    # 3.20 x 1.55 x 1.55 per the Digi-Key package dimensions for 3-103-099;
    # the datasheet figure's height label was not machine readable.
    make_schurter_1206_fuse(model, 1.55, 1.55, WHITE)


def make_gecko(model: ModelDocument, circuits: int) -> None:
    """Harwin Gecko-SL vertical THT Screw-Lok plug, per DRG-02638.

    Table 1 of that sheet lists DIM 'A' (stud spacing), DIM 'B' (contact span)
    and DIM 'C' (body length) per circuit count. Every listed row satisfies
    B = (circuits/2 - 1) x 1.25, A = B + 7.80 and C = A + 4.90, so those
    relations are used here instead of transcribed per-size numbers.

    The part is symmetric about both footprint axes, so no orientation flip is
    needed between the KiCad footprint frame and the STEP frame.
    """
    per_row = circuits // 2
    pitch = row_spacing = 1.25
    span = (per_row - 1) * pitch
    stud_x = span / 2.0 + 3.90
    body_length = 2.0 * (stud_x + 2.45)
    body_width, body_height = 4.90, 4.30
    wall, shroud_depth = 0.60, 2.40
    section, tail, post = 0.40, 3.00, 2.20

    body = centered_box(body_length, body_width, body_height)
    cavity = centered_box(body_length - 2 * wall, body_width - 2 * wall,
                          shroud_depth, body_height - shroud_depth)
    model.feature("Package", "Insulator", "Moulded insulator", body.cut(cavity), BLACK)

    contacts = []
    for i in range(per_row):
        x = -span / 2.0 + i * pitch
        for y in (row_spacing / 2.0, -row_spacing / 2.0):
            contacts.append(box_at(x, y, section, section, post, body_height - shroud_depth))
            contacts.append(box_at(x, y, section, section, tail, -tail))
    model.feature("Terminals", "Contacts", "Gold contacts", Part.makeCompound(contacts), GOLD)

    studs = []
    for x in (-stud_x, stud_x):
        studs.append(Part.makeCylinder(1.60, 1.20, App.Vector(x, 0.0, 0.0), App.Vector(0, 0, 1)))
        studs.append(Part.makeCylinder(1.00, 5.00, App.Vector(x, 0.0, -5.00), App.Vector(0, 0, 1)))
    model.feature("Terminals", "ScrewLok_Studs", "Screw-Lok board mount studs",
                  Part.makeCompound(studs), METAL)

    # "Contact number one indicated on the outside of the housings" -
    # Gecko component specification C125XX, section 1.
    #
    # Footprint pad 1 is on the +Y row, and KiCad mirrors Y between the
    # footprint and model frames, so the marker belongs on -Y here.
    marker = Part.makeCylinder(
        0.30, 0.06,
        App.Vector(-body_length / 2.0 + 0.90, -row_spacing / 2.0, body_height - 0.06),
        App.Vector(0, 0, 1),
    )
    model.feature("Markings", "Contact_1_Ident", "Contact 1 identifier", marker, DARK_GREY)


def make_gecko_20(model: ModelDocument) -> None:
    make_gecko(model, 20)


def make_gecko_06(model: ModelDocument) -> None:
    make_gecko(model, 6)


def make_jst_xh_b20b(model: ModelDocument) -> None:
    """JST XH B20B-XH-A vertical THT shrouded header.

    Contact span A = (n - 1) x 2.50 and moulded body B = A + 4.90, with a
    5.75 mm body offset 2.35 mm ahead of and 3.40 mm behind the contact row.

    KiCad mirrors Y between the footprint frame and the model frame, and this
    body is not symmetric about the contact row, so the body is built spanning
    Y = -3.40 .. +2.35 to match a footprint whose body spans -2.35 .. +3.40.
    """
    circuits, pitch = 20, 2.50
    span = (circuits - 1) * pitch
    body_length = span + 4.90
    y_min, y_max = -3.40, 2.35
    body_height, wall, floor = 7.00, 0.85, 1.60
    section, tail, top = 0.64, 3.40, 6.00

    width = y_max - y_min
    outer = Part.makeBox(body_length, width, body_height,
                         App.Vector(-body_length / 2.0, y_min, 0.0))
    cavity = Part.makeBox(body_length - 2 * wall, width - 2 * wall, body_height - floor,
                          App.Vector(-body_length / 2.0 + wall, y_min + wall, floor))
    model.feature("Package", "Housing", "Moulded shroud", outer.cut(cavity), BLACK)

    contacts = [
        box_at(-span / 2.0 + i * pitch, 0.0, section, section, tail + top, -tail)
        for i in range(circuits)
    ]
    model.feature("Terminals", "Contacts", "Tin-plated contacts",
                  Part.makeCompound(contacts), TIN)

    # Circuit 1 is identified on the outside of the XH shroud.
    marker = Part.makeCylinder(
        0.35, 0.06,
        App.Vector(-body_length / 2.0 + 1.20, y_min + 0.42, body_height - 0.06),
        App.Vector(0, 0, 1),
    )
    model.feature("Markings", "Circuit_1_Ident", "Circuit 1 identifier", marker, DARK_GREY)


def make_mini50_sr_04(model: ModelDocument) -> None:
    """Molex Mini50 34792 4-circuit single-row vertical THT header.

    Per SD-34792-001: 2.00 mm pitch, 1.00 mm contact holes, 0.40 x 0.50 blades,
    11.70 mm post spacing with the posts 2.55 mm to -Y of the contact row, and
    a 9.94 mm body width. The drawing dimensions the height above the PCB as
    8.16 + 6.44 = 14.60 mm, which is modelled as a solid 8.16 mm base carrying
    a 6.44 mm shrouded mating section.

    The header is flush mount, so the body sits on the seating plane at Z = 0.
    Body Y is centred on the contact row; the drawing's body-to-hole offset was
    not resolved, and the 9.94 mm width comfortably encloses both the contacts
    and the posts either way.
    """
    circuits, pitch = 4, 2.00
    span = (circuits - 1) * pitch
    length, width = 14.62, 9.94
    base_h, shroud_h = 8.16, 6.44
    height = base_h + shroud_h
    wall = 1.20
    blade_x, blade_y = 0.40, 0.50
    tail = 3.00
    post_x, post_y, post_d, post_len = 11.70 / 2.0, -2.55, 2.05, 3.00

    outer = centered_box(length, width, height)
    cavity = centered_box(length - 2 * wall, width - 2 * wall, shroud_h, base_h)
    model.feature("Package", "Housing", "Moulded housing", outer.cut(cavity), BLACK)

    contacts = []
    for i in range(circuits):
        x = -span / 2.0 + i * pitch
        contacts.append(box_at(x, 0.0, blade_x, blade_y, shroud_h - 1.0, base_h))
        contacts.append(box_at(x, 0.0, blade_x, blade_y, tail, -tail))
    model.feature("Terminals", "Contacts", "Tin-plated blades",
                  Part.makeCompound(contacts), TIN)

    posts = [
        Part.makeCylinder(post_d / 2.0, post_len, App.Vector(x, post_y, -post_len),
                          App.Vector(0, 0, 1))
        for x in (-post_x, post_x)
    ]
    model.feature("Terminals", "Board_Posts", "Board mount posts",
                  Part.makeCompound(posts), BLACK)

    # Circuit 1 is identified on the outside of the housing.
    marker = Part.makeCylinder(
        0.35, 0.06,
        App.Vector(-length / 2.0 + 1.20, width / 2.0 - 0.90, height - 0.06),
        App.Vector(0, 0, 1),
    )
    model.feature("Markings", "Circuit_1_Ident", "Circuit 1 identifier", marker, DARK_GREY)


def make_mini50_dual(model: ModelDocument, circuits: int) -> None:
    """Molex Mini50 34825 dual-row vertical THT header.

    Per SD-348250200: 2.00 mm pitch, 2.20 mm row spacing, 1.00 mm contact
    holes, 0.40 x 0.50 blades, DIM E post holes 2.15 press fit / 2.55 drop in
    sitting 2.55 mm to -Y of the second contact row, body length 24.40 (16-way)
    or 28.40 (20-way), body width 12.17 and 15.60 mm above the PCB.

    The sheet dimensions the height as a single figure, so the 6.44 mm shroud
    depth is carried over from the single-row 34792 sheet - the mating
    receptacle is common to the series, so the mating cavity is the same depth.

    Body Y is centred on the contact array; the sheet's body-to-hole offset was
    not resolved, and 12.17 encloses both rows and the posts either way.
    """
    per_row = circuits // 2
    pitch, row_spacing = 2.00, 2.20
    span = (per_row - 1) * pitch
    # The sheet carries two length series; the posts sit outside DIM C once
    # their diameter counts, so DIM C is the shroud and the larger is the body.
    length = {16: 26.63, 20: 30.63}[circuits]
    shroud_len = {16: 24.40, 20: 28.40}[circuits]
    post_spacing = {16: 23.70, 20: 27.70}[circuits]
    width, height, shroud_h = 12.17, 15.60, 6.44
    base_h = height - shroud_h
    wall = 1.20
    blade_x, blade_y, tail = 0.40, 0.50, 3.00
    post_y, post_d, post_len = -(row_spacing / 2.0 + 2.55), 2.05, 3.00

    base = centered_box(length, width, base_h)
    shroud = centered_box(shroud_len, width, shroud_h, base_h)
    cavity = centered_box(shroud_len - 2 * wall, width - 2 * wall, shroud_h, base_h)
    model.feature("Package", "Housing", "Moulded housing",
                  base.fuse(shroud).cut(cavity), BLACK)

    contacts = []
    for i in range(per_row):
        x = -span / 2.0 + i * pitch
        for y in (row_spacing / 2.0, -row_spacing / 2.0):
            contacts.append(box_at(x, y, blade_x, blade_y, shroud_h - 1.0, base_h))
            contacts.append(box_at(x, y, blade_x, blade_y, tail, -tail))
    model.feature("Terminals", "Contacts", "Tin-plated blades",
                  Part.makeCompound(contacts), TIN)

    posts = [
        Part.makeCylinder(post_d / 2.0, post_len, App.Vector(x, post_y, -post_len),
                          App.Vector(0, 0, 1))
        for x in (-post_spacing / 2.0, post_spacing / 2.0)
    ]
    model.feature("Terminals", "Board_Posts", "Board mount posts",
                  Part.makeCompound(posts), BLACK)

    # Footprint pad 1 sits on the +Y row and KiCad mirrors Y between the
    # footprint and model frames, so the marker belongs on the -Y side here.
    marker = Part.makeCylinder(
        0.35, 0.06,
        App.Vector(-length / 2.0 + 1.20, -(width / 2.0 - 0.90), height - 0.06),
        App.Vector(0, 0, 1),
    )
    model.feature("Markings", "Circuit_1_Ident", "Circuit 1 identifier", marker, DARK_GREY)


def make_mini50_dual_16(model: ModelDocument) -> None:
    make_mini50_dual(model, 16)


def make_mini50_dual_20(model: ModelDocument) -> None:
    make_mini50_dual(model, 20)


# Harwin Datamate M80 vertical throughboard headers. Every dimension here was
# measured off the manufacturer reference solid for that part (facts only - the
# geometry below is drawn from scratch and shares nothing with it).
#
# KiCad mirrors Y between the footprint frame and the model frame, and these
# bodies are NOT symmetric about the contact rows, so the housing Y range below
# is the negated footprint range.
#
#   part: (contacts, rows, housing_x, y_min, y_max, housing_h, tail,
#          fixing, fixing_x, fixing_w, fixing_d, fixing_z0, fixing_z1)
M80_MODELS = {
    "M80-5001642": (16, 2, 26.00, -2.775, 3.275, 5.55, 3.30, "jackscrew", 10.50, 3.10, 3.10, 0.00, 4.50),
    "M80-5002042": (20, 2, 30.00, -2.775, 3.275, 5.55, 3.30, "jackscrew", 12.50, 3.10, 3.10, 0.00, 4.50),
    "M80-5T10442MC": (4, 2, 14.00, -2.775, 3.275, 5.55, 3.30, "retainer", 4.50, 3.10, 3.10, 0.00, 4.50),
    "M80-8531642": (16, 2, 19.50, -3.075, 2.775, 5.40, 3.30, "latch", 9.35, 1.20, 3.45, 0.40, 8.35),
    "M80-8672022": (20, 2, 23.50, -3.075, 2.775, 5.40, 3.30, "latch", 11.35, 1.20, 3.45, 0.40, 8.35),
    "M80-8770222": (2, 1, 7.50, -2.075, 1.775, 5.40, 3.30, "latch", 3.35, 1.20, 3.45, 0.40, 8.35),
}

STAINLESS = (0.68, 0.69, 0.71)


def make_datamate_m80(model: ModelDocument, part: str) -> None:
    """Harwin Datamate M80 2.00mm vertical throughboard header."""
    (contacts, rows, housing_x, y_min, y_max, housing_h, tail,
     fixing, fix_x, fix_w, fix_d, fix_z0, fix_z1) = M80_MODELS[part]
    per_row = contacts // rows
    pitch = 2.00
    span = (per_row - 1) * pitch
    row_ys = [1.00, -1.00] if rows == 2 else [0.0]
    width = y_max - y_min
    y_mid = (y_max + y_min) / 2.0
    wall, section = 1.00, 0.50
    shroud_h = housing_h - 1.60

    outer = Part.makeBox(housing_x, width, housing_h,
                         App.Vector(-housing_x / 2.0, y_min, 0.0))
    cavity = Part.makeBox(housing_x - 2 * wall, width - 2 * wall, shroud_h,
                          App.Vector(-housing_x / 2.0 + wall, y_min + wall,
                                     housing_h - shroud_h))
    model.feature("Package", "Housing", "Moulded housing", outer.cut(cavity), BLACK)

    posts = []
    for y in row_ys:
        for i in range(per_row):
            x = -span / 2.0 + i * pitch
            posts.append(box_at(x, y, section, section, shroud_h - 0.8,
                                housing_h - shroud_h))
            posts.append(box_at(x, y, section, section, tail, -tail))
    model.feature("Terminals", "Contacts", "Gold-finished contacts",
                  Part.makeCompound(posts), GOLD)

    fixings = []
    for x in (-fix_x, fix_x):
        fixings.append(box_at(x, y_mid, fix_w, fix_d, fix_z1 - fix_z0, fix_z0))
    colour = STAINLESS if fixing == "jackscrew" else METAL
    label = {"jackscrew": "Stainless steel jackscrews",
             "retainer": "101-Lok retainers",
             "latch": "Locking latches"}[fixing]
    model.feature("Terminals", "Fixings", label, Part.makeCompound(fixings), colour)

    # Footprint pad 1 sits on the +Y row and KiCad mirrors Y between the
    # footprint and model frames, so the marker belongs on the -Y side here.
    marker = Part.makeCylinder(
        0.35, 0.06,
        App.Vector(-housing_x / 2.0 + 1.20, y_min + 0.80, housing_h - 0.06),
        App.Vector(0, 0, 1),
    )
    model.feature("Markings", "Contact_1_Ident", "Contact 1 identifier", marker, DARK_GREY)


def _m80_builder(part):
    def build(model: ModelDocument) -> None:
        make_datamate_m80(model, part)
    return build


BUILDERS = {
    "Bourns_CDSOD323-TxxC_SOD-323": make_bourns_sod323,
    "Littelfuse_SZSMFxxA_SOD-123FL": make_szsmf_sod123fl,
    "Schurter_USF-1206_Fuse": make_usf1206_fuse,
    "Schurter_MGA-A_Fuse": make_mga_a_fuse,
    "Littelfuse_470-Series_Fuse": make_littelfuse_470,
    "Vishay_RCL1225_2W": make_rcl1225_resistor,
    "Bourns_SMBJ-Q_DO-214AA": make_smbj_do214aa,
    "Molex_Mini50_34792_1x04": make_mini50_sr_04,
    "Molex_Mini50_34825-0160_2x08_P2.00mm_Vertical": make_mini50_dual_16,
    "Molex_Mini50_34825-0200_2x10_P2.00mm_Vertical": make_mini50_dual_20,
    "Harwin_Gecko_G125-MV12005M2P": make_gecko_20,
    "Harwin_Gecko_G125-MV10605M2P": make_gecko_06,
    "JST_XH_B20B-XH-A_1x20_P2.50mm_Vertical": make_jst_xh_b20b,
    "BQ79606A-Q1": make_bq79606,
    "INA286_SOIC-8": make_ina286,
    "STB45N65M5_D2PAK": make_stb45n65,
    "CSS2H-3920R-L200F": make_css2h,
    "1N6263W_SOD-123": make_1n6263w,
    "ACS781LLRTR-100U-T": make_acs781,
    "BVN-M-R001-1.0": make_bvn,
    "WE_7460305": make_we_7460305,
    "INA190A3IDDFR_DDF": make_ina190,
    "PG-HSOG-8-1_INF": make_toll,
    "IRS2186S_SOIC-8": make_soic8,
    "L_Wuerth_WE-PD-Typ-LS": make_we_pd_typ_ls,
    "L_Wuerth_WE-PD-Robust-7332": make_we_pd_robust_7332,
    "LTC3639_MSE16-12": make_ltc3639,
    "LFXTAL016178REEL": make_crystal,
    "LM2576HV_TO-263-5": make_to263,
    "LM2596S_TO-263-5": make_to263,
    "NCS213R_SC70-6": make_sc70,
    "Power_Pad_6x6mm": make_power_pad,
    **{f"Harwin_Datamate_{p}": _m80_builder(p) for p in M80_MODELS},
}


def sync_provenance() -> None:
    path = ROOT / "ASSET_PROVENANCE.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, existing = rows[0], rows[1:]
    managed = {f"3d_models/sources/{name}.FCStd" for name in SOURCES}
    managed |= {f"3d_models/custom_3dmodels.3dshapes/{name}{extension}" for name, (_, _, extension) in SOURCES.items()}
    managed.add("tools/generate_original_freecad_models.py")
    managed.add("tools/generate_original_freecad_models.FCMacro")
    kept = [
        row for row in existing
        if row[0] not in managed
        and not (
            row[0].startswith("3d_models/")
            and row[2] in {"3d_model", "source"}
            and not (ROOT / row[0]).exists()
        )
    ]

    model_rows = []
    source_rows = []
    for name, (source, basis, extension) in SOURCES.items():
        model_rows.append([
            f"3d_models/custom_3dmodels.3dshapes/{name}{extension}", f"{name}{extension}", "3d_model",
            AUTHOR, source, basis, LICENSE,
            "Independently generated STEP with embedded author source copyright and SPDX licence metadata",
            "cleared_original", f"{COPYRIGHT}; aligned to the matching footprint at the PCB seating plane",
        ])
        source_rows.append([
            f"3d_models/sources/{name}.FCStd", f"{name} FreeCAD project", "source", AUTHOR, source, basis,
            LICENSE, "Editable FreeCAD project with hierarchical design tree and embedded licensing properties",
            "cleared_original", f"{COPYRIGHT}; generated with FreeCAD 1.1.1",
        ])

    generator_row = [
        "tools/generate_original_freecad_models.py", "Original FreeCAD model generator", "source", AUTHOR,
        "NOASSERTION", "Original generator source", LICENSE,
        "Generates editable FCStd projects and their STEP exports without third-party CAD geometry",
        "cleared_original", f"{COPYRIGHT}; SPDX notice embedded",
    ]
    macro_row = [
        "tools/generate_original_freecad_models.FCMacro", "Color-aware FreeCAD generator launcher", "source", AUTHOR,
        "NOASSERTION", "Original GUI launcher source", LICENSE,
        "Runs the original generator through FreeCAD's color-preserving GUI exporter",
        "cleared_original", f"{COPYRIGHT}; SPDX notice embedded",
    ]
    ordered = kept + sorted(model_rows + source_rows, key=lambda row: row[0].lower()) + [generator_row, macro_row]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(ordered)


def validate_outputs(results) -> None:
    """Reopen every FCStd and STEP and verify tree, metadata, and solids."""
    for name, fcstd, step, _, _ in results:
        source, dimensional_basis, _ = SOURCES[name]
        project = App.openDocument(str(fcstd))
        try:
            root = project.getObject("Component")
            metadata = project.getObject("License_Metadata")
            if root is None or metadata is None:
                raise RuntimeError(f"Missing design tree or metadata in {fcstd}")
            root_children = {obj.Name for obj in root.Group}
            required_children = {"License_Metadata", "Package", "Terminals", "Markings"}
            if not required_children.issubset(root_children):
                raise RuntimeError(f"Incomplete hierarchical design tree in {fcstd}")
            for group_name in ("Package", "Terminals", "Markings"):
                group = project.getObject(group_name)
                intentionally_empty = (
                    (name == "Power_Pad_6x6mm" and group_name == "Package")
                    or (name == "BVN-M-R001-1.0" and group_name == "Markings")
                    or (name == "Bourns_CDSOD323-TxxC_SOD-323" and group_name == "Markings")
                )
                if group is None or (not group.Group and not intentionally_empty):
                    raise RuntimeError(f"Missing {group_name} group in {fcstd}")
            if root.SPDX_License != LICENSE or metadata.Copyright != COPYRIGHT:
                raise RuntimeError(f"Incorrect embedded licence properties in {fcstd}")
            if metadata.Source != source or metadata.Dimensional_Basis != dimensional_basis:
                raise RuntimeError(f"Incorrect embedded source properties in {fcstd}")
            if App.GuiUp:
                package = project.getObject("Package")
                for obj in package.Group:
                    actual = tuple(round(channel, 2) for channel in obj.ViewObject.ShapeColor[:3])
                    if actual != BLACK:
                        raise RuntimeError(f"Package body is not black in {fcstd}: {obj.Label}={actual}")
        finally:
            App.closeDocument(project.Name)

        check = App.newDocument("STEP_Validation")
        try:
            Import.insert(str(step), check.Name)
            check.recompute()
            shapes = [obj.Shape for obj in check.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()]
            solid_count = sum(len(shape.Solids) for shape in shapes)
            if not shapes or solid_count < 1:
                raise RuntimeError(f"STEP did not reopen as solid geometry: {step}")
            header = step.read_text(encoding="utf-8", errors="replace")[:3000]
            for required in (LICENSE, COPYRIGHT, AUTHOR, source):
                if required not in header:
                    raise RuntimeError(f"Missing {required!r} in STEP metadata: {step}")
            if App.GuiUp and "COLOUR_RGB" not in step.read_text(encoding="utf-8", errors="replace"):
                raise RuntimeError(f"STEP has no exported presentation colours: {step}")
        finally:
            App.closeDocument(check.Name)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for backup in SOURCE_DIR.glob("*.FCBak"):
        backup.unlink()
    requested = sys.argv[1:]
    unknown = sorted(set(requested) - set(BUILDERS))
    if unknown:
        raise SystemExit(f"Unknown model name(s): {', '.join(unknown)}")
    selected = requested or list(BUILDERS)
    results = []
    for name in selected:
        builder = BUILDERS[name]
        model = ModelDocument(name)
        builder(model)
        fcstd, step, bounds, solids = model.finish()
        results.append((name, fcstd, step, bounds, solids))
    validate_outputs(results)
    sync_provenance()
    for name, _, step, bounds, solids in results:
        print(
            f"Generated {name}: {step.name}, {solids} solids, "
            f"{bounds[0]:.3f} x {bounds[1]:.3f} x {bounds[2]:.3f} mm"
        )
    print(f"Generated and reopened {len(results)} original FreeCAD projects and {len(results)} licensed STEP models.")
    if os.environ.get("FREECAD_AUTOCLOSE") == "1" and App.GuiUp:
        Gui.getMainWindow().close()


if __name__ == "__main__":
    main()
