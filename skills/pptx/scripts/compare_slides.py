"""
compare_slides.py — Visual PPTX Comparison + Interactive Alignment

Compares slides between two PPTX files using PowerPoint COM for visual
rendering and python-pptx for structural analysis. Optionally runs an
interactive alignment session to bring a target slide in line with a source.

COMPARE MODE (default):
    python scripts/compare_slides.py <file_a> <file_b>                    # All slides
    python scripts/compare_slides.py <file_a> <file_b> --slides 5         # Slide 5
    python scripts/compare_slides.py <file_a> <file_b> --map 14:9,15:10   # Cross-map

ALIGN MODE:
    python scripts/compare_slides.py <file_a> <file_b> --map 8:19 --align
    → Visual comparison opens in browser
    → Structural analysis runs
    → Interactive prompt: choose source, approve/modify/skip each diff
    → Approved changes applied via unpack → XML edit → clean → pack

Options:
    --slides    Slide numbers (e.g. 5 or 5,8,12 or 5:10)
    --map       Cross-map slides (e.g. 14:9,15:10) — A_num:B_num
    --align     Enable interactive alignment after comparison
    --out       Output HTML report path
    --width     Export width in pixels (default: 1920)
    --no-diff   Skip pixel-diff overlay in HTML report
    --no-visual Skip PowerPoint COM visual export (structural only)

Dependencies:
    pip install pywin32 Pillow python-pptx
"""

import argparse
import base64
import html
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- Optional imports with graceful fallback ---

try:
    import win32com.client
    import pythoncom
    HAS_COM = True
except ImportError:
    HAS_COM = False

try:
    from PIL import Image, ImageChops, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.enum.text import PP_ALIGN
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ShapeInfo:
    """Extracted properties of a single shape on a slide."""
    name: str
    shape_type: str
    left: int = 0          # EMU
    top: int = 0           # EMU
    width: int = 0         # EMU
    height: int = 0        # EMU
    text: str = ""
    font_names: list = field(default_factory=list)
    font_sizes: list = field(default_factory=list)
    font_bolds: list = field(default_factory=list)
    font_colors: list = field(default_factory=list)
    fill_color: str = ""   # hex or "none"
    image_hash: str = ""   # md5 of image blob
    srgb_colors: list = field(default_factory=list)  # all hardcoded colors from raw XML
    # Text frame properties
    auto_size: str = ""    # NONE, SHAPE_TO_FIT_TEXT, TEXT_TO_FIT_SHAPE
    margin_left: int = -1  # EMU, -1 = not set
    margin_right: int = -1
    margin_top: int = -1
    margin_bottom: int = -1
    has_inherited_font: bool = False  # True if text runs have no explicit typeface


@dataclass
class SlideDiff:
    """A single detected difference between two slides."""
    category: str        # text, color, position, size, font, image, fill
    shape_name: str
    description: str
    source_value: str
    target_value: str
    confidence: str      # HIGH, MEDIUM, LOW
    action: str          # what the fix would do
    xml_fix: dict = field(default_factory=dict)  # {old_str: new_str} or operation details


# ============================================================
# Argument Parsing
# ============================================================

def parse_slides_arg(arg: str) -> list[int]:
    slides = []
    for part in arg.split(","):
        part = part.strip()
        if ":" in part:
            start, end = part.split(":", 1)
            slides.extend(range(int(start), int(end) + 1))
        else:
            slides.append(int(part))
    return slides


def parse_map_arg(arg: str) -> list[tuple[int, int]]:
    pairs = []
    for part in arg.split(","):
        a, b = part.strip().split(":")
        pairs.append((int(a), int(b)))
    return pairs


# ============================================================
# Visual Comparison (PowerPoint COM)
# ============================================================

def export_slides_com(pptx_path: str, output_dir: str, slide_numbers: list[int] | None,
                      width: int, ppt_app=None) -> dict[int, str]:
    """Export slides as PNG via PowerPoint COM. Returns {slide_num: image_path}.
    Optionally accepts an existing PowerPoint Application COM object to reuse.
    Falls back to asking user to open the file manually if COM open fails."""
    if not HAS_COM:
        print("ERROR: pywin32 required for visual export. Install: pip install pywin32")
        return {}

    pptx_path = os.path.abspath(pptx_path)
    if not os.path.exists(pptx_path):
        print(f"ERROR: File not found: {pptx_path}")
        return {}

    own_com = ppt_app is None
    if own_com:
        pythoncom.CoInitialize()

    pres = None
    try:
        if ppt_app is None:
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            ppt_app.Visible = True
            ppt_app.WindowState = 2  # minimized

        # Try opening directly first
        try:
            pres = ppt_app.Presentations.Open(pptx_path, ReadOnly=True, WithWindow=False)
        except Exception:
            # COM open failed — check if file is already open in PowerPoint
            pres = _find_open_presentation(ppt_app, pptx_path)
            if pres is None:
                # Ask user to open manually
                fname = os.path.basename(pptx_path)
                print(f"\n  ⚠️  Cannot open '{fname}' via COM (file may need repair).")
                print(f"  Please open it manually in PowerPoint, then press Enter to continue.")
                print(f"  Path: {pptx_path}")
                input("  Press Enter when ready... ")

                # Reconnect to PowerPoint — user may have opened file in a different instance
                try:
                    ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
                except Exception:
                    ppt_app = win32com.client.Dispatch("PowerPoint.Application")

                pres = _find_open_presentation(ppt_app, pptx_path)
                if pres is None:
                    print(f"  ERROR: Still cannot find '{fname}' in open presentations.")
                    return {}
                print(f"  ✅ Found open presentation: {fname}")

        total = pres.Slides.Count

        if slide_numbers is None:
            slide_numbers = list(range(1, total + 1))

        valid = [s for s in slide_numbers if 1 <= s <= total]
        for s in slide_numbers:
            if s < 1 or s > total:
                print(f"  WARNING: Slide {s} out of range (1-{total}), skipping.")

        exported = {}
        sw = pres.PageSetup.SlideWidth
        sh = pres.PageSetup.SlideHeight
        height = int(width * (sh / sw))

        for num in valid:
            img_path = os.path.join(output_dir, f"slide_{num}.png")
            pres.Slides(num).Export(img_path, "PNG", width, height)
            exported[num] = img_path
            print(f"  Exported slide {num}/{total}")

        return exported
    finally:
        # Only close if WE opened it (not if user had it open)
        if pres and not _is_user_opened(pres):
            try:
                pres.Close()
            except Exception:
                pass
        if own_com:
            pythoncom.CoUninitialize()


def _find_open_presentation(ppt_app, pptx_path: str):
    """Search PowerPoint's open presentations for a matching file."""
    target = os.path.normcase(os.path.abspath(pptx_path))
    target_name = os.path.splitext(os.path.basename(target))[0].lower()
    try:
        count = ppt_app.Presentations.Count
        for i in range(1, count + 1):
            p = ppt_app.Presentations(i)
            try:
                pres_name = os.path.splitext(p.Name)[0].lower()
                # Exact path match
                full = os.path.normcase(os.path.join(p.Path, p.Name))
                if full == target:
                    return p
                # Name match (handles OneDrive URL paths, repaired files)
                if pres_name == target_name or target_name.startswith(pres_name):
                    return p
            except Exception:
                try:
                    if os.path.splitext(p.Name)[0].lower() == target_name:
                        return p
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _is_user_opened(pres) -> bool:
    """Check if the presentation was opened by the user (has a window) vs by us."""
    try:
        return pres.Windows.Count > 0
    except Exception:
        return False


def generate_diff_image(img_a_path: str, img_b_path: str, output_path: str) -> str | None:
    if not HAS_PIL:
        return None
    try:
        img_a = Image.open(img_a_path).convert("RGB")
        img_b = Image.open(img_b_path).convert("RGB")
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size, Image.LANCZOS)

        diff = ImageChops.difference(img_a, img_b)
        threshold = 30
        pixels = diff.load()
        highlight = Image.new("RGBA", img_a.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(highlight)

        w, h = diff.size
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r, g, b = pixels[x, y]
                if r + g + b > threshold:
                    draw.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(255, 0, 0, 128))

        base = Image.blend(img_a, Image.new("RGB", img_a.size, (128, 128, 128)), 0.5).convert("RGBA")
        result = Image.alpha_composite(base, highlight)
        result.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"  WARNING: Diff generation failed: {e}")
        return None


def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('ascii')}"


def generate_html_report(file_a, file_b, comparisons, output_path):
    name_a = os.path.basename(file_a)
    name_b = os.path.basename(file_b)

    rows = []
    for c in comparisons:
        sa, sb = c["slide_a"], c["slide_b"]
        img_a = image_to_base64(c["img_a"])
        img_b = image_to_base64(c["img_b"])
        diff = ""
        if c.get("img_diff"):
            diff = f'<div class="slide-card"><div class="slide-label">Differences</div><img src="{image_to_base64(c["img_diff"])}" /></div>'

        rows.append(f"""
        <div class="comparison-row" id="slide-{sa}-{sb}">
            <h2>Slide {sa} (A) vs Slide {sb} (B)</h2>
            <div class="slides-container">
                <div class="slide-card"><div class="slide-label">A — Slide {sa}</div><img src="{img_a}" /></div>
                <div class="slide-card"><div class="slide-label">B — Slide {sb}</div><img src="{img_b}" /></div>
                {diff}
            </div>
        </div>""")

    page = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<title>Slide Comparison — {html.escape(name_a)} vs {html.escape(name_b)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#1e1e1e;color:#d4d4d4;padding:24px}}
h1{{color:#fff;margin-bottom:8px;font-size:1.4em}}
.meta{{color:#888;font-size:.85em;margin-bottom:24px}} .meta span{{color:#569cd6}}
.nav{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:24px}}
.nav a{{background:#333;color:#9cdcfe;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:.8em}}
.comparison-row{{margin-bottom:40px;border-bottom:1px solid #333;padding-bottom:24px}}
.comparison-row h2{{color:#dcdcaa;font-size:1.1em;margin-bottom:12px}}
.slides-container{{display:flex;gap:16px;flex-wrap:wrap}}
.slide-card{{flex:1;min-width:300px}}
.slide-label{{background:#333;color:#ce9178;padding:6px 12px;border-radius:4px 4px 0 0;font-size:.85em;font-weight:600}}
.slide-card img{{width:100%;border:1px solid #444;border-radius:0 0 4px 4px;display:block}}
</style></head><body>
<h1>Slide Comparison Report</h1>
<div class="meta">
<div><b>File A:</b> <span>{html.escape(name_a)}</span></div>
<div><b>File B:</b> <span>{html.escape(name_b)}</span></div>
<div><b>Generated:</b> {time.strftime("%Y-%m-%d %H:%M:%S")}</div></div>
<div class="nav">{"".join(f'<a href="#slide-{c["slide_a"]}-{c["slide_b"]}">S{c["slide_a"]}↔S{c["slide_b"]}</a>' for c in comparisons)}</div>
{"".join(rows)}
</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    return output_path


# ============================================================
# Structural Analysis (python-pptx)
# ============================================================

def _extract_srgb_colors(slide_xml: str) -> list[str]:
    """Extract all hardcoded srgbClr values from raw slide XML."""
    return re.findall(r'<a:srgbClr val="([A-Fa-f0-9]{6})"', slide_xml)


def _get_theme_colors(pptx_path: str, slide_number: int) -> tuple[str, dict[str, str]]:
    """Extract the resolved theme color scheme for a given slide.
    Returns (theme_name, {color_role: hex_value})."""
    from lxml import etree
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_number - 1]
    master = slide.slide_layout.slide_master
    for rel_key, rel in master.part.rels.items():
        if 'theme' in rel.reltype.lower():
            part = master.part.related_part(rel_key)
            root = etree.fromstring(part.blob)
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            scheme = root.find('.//a:themeElements/a:clrScheme', ns)
            if scheme is not None:
                colors = {}
                for child in scheme:
                    tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
                    for sub in child:
                        colors[tag] = sub.get('val', sub.get('lastClr', ''))
                        break
                return scheme.get('name', 'unknown'), colors
    return 'unknown', {}


def _get_theme_fonts(pptx_path: str, slide_number: int) -> dict[str, str]:
    """Extract the theme font scheme for a given slide.
    Returns {major: typeface, minor: typeface, scheme_name: name}."""
    from lxml import etree
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_number - 1]
    master = slide.slide_layout.slide_master
    for rel_key, rel in master.part.rels.items():
        if 'theme' in rel.reltype.lower():
            part = master.part.related_part(rel_key)
            root = etree.fromstring(part.blob)
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            fonts = {}
            for fs in root.findall('.//a:themeElements/a:fontScheme', ns):
                fonts['scheme_name'] = fs.get('name', '')
                for major in fs.findall('a:majorFont/a:latin', ns):
                    fonts['major'] = major.get('typeface', '')
                for minor in fs.findall('a:minorFont/a:latin', ns):
                    fonts['minor'] = minor.get('typeface', '')
            return fonts
    return {}


def _extract_scheme_color_usage(slide_xml: str) -> list[str]:
    """Extract all schemeClr val references from slide XML."""
    return re.findall(r'<a:schemeClr val="([^"]+)"', slide_xml)


def _get_slide_xml(pptx_path: str, slide_number: int) -> str:
    """Read raw XML for a slide from a PPTX file."""
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_number - 1]
    return slide._element.xml


def _get_slide_filename(pptx_path: str, slide_number: int) -> str:
    """Get the slideN.xml filename for a given 1-based slide number."""
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_number - 1]
    # slide part name is like '/ppt/slides/slide5.xml'
    return os.path.basename(slide.part.partname)


def analyze_slide(pptx_path: str, slide_number: int) -> list[ShapeInfo]:
    """Extract structured info for every shape on a slide."""
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_number - 1]
    raw_xml = slide._element.xml

    # Get per-shape srgb colors from raw XML
    shape_infos = []

    for shape in slide.shapes:
        info = ShapeInfo(
            name=shape.name,
            shape_type=str(shape.shape_type),
            left=shape.left or 0,
            top=shape.top or 0,
            width=shape.width or 0,
            height=shape.height or 0,
        )

        # Text and font properties
        if shape.has_text_frame:
            tf = shape.text_frame
            paragraphs = tf.paragraphs
            info.text = "\n".join(p.text for p in paragraphs)

            # Text frame properties
            info.auto_size = str(tf.auto_size) if tf.auto_size is not None else "NONE"
            try:
                info.margin_left = tf.margin_left if tf.margin_left is not None else -1
                info.margin_right = tf.margin_right if tf.margin_right is not None else -1
                info.margin_top = tf.margin_top if tf.margin_top is not None else -1
                info.margin_bottom = tf.margin_bottom if tf.margin_bottom is not None else -1
            except Exception:
                pass

            # Check for inherited fonts (runs with no explicit typeface)
            shape_xml = shape._element.xml
            has_any_text = any(p.text.strip() for p in paragraphs)
            has_explicit_typeface = 'typeface="' in shape_xml and '+m' not in shape_xml
            if has_any_text and not has_explicit_typeface:
                info.has_inherited_font = True

            for para in paragraphs:
                for run in para.runs:
                    font = run.font
                    info.font_names.append(font.name or "")
                    info.font_sizes.append(str(font.size) if font.size else "")
                    info.font_bolds.append(str(font.bold) if font.bold is not None else "")
                    if font.color and font.color.type is not None:
                        try:
                            if font.color.rgb:
                                info.font_colors.append(str(font.color.rgb))
                        except AttributeError:
                            pass  # scheme/theme color — no explicit RGB

        # Fill color
        if hasattr(shape, "fill"):
            try:
                fill = shape.fill
                if fill.type is not None and hasattr(fill, 'fore_color') and fill.fore_color and fill.fore_color.rgb:
                    info.fill_color = str(fill.fore_color.rgb)
            except Exception:
                pass

        # Image hash
        if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
            try:
                blob = shape.image.blob
                info.image_hash = hashlib.md5(blob).hexdigest()
            except Exception:
                pass

        # Hardcoded srgb colors from this shape's XML element
        shape_xml = shape._element.xml
        info.srgb_colors = _extract_srgb_colors(shape_xml)

        shape_infos.append(info)

    return shape_infos


def diff_slides(source_shapes: list[ShapeInfo], target_shapes: list[ShapeInfo],
                source_xml: str, target_xml: str,
                source_theme: tuple[str, dict] = None,
                target_theme: tuple[str, dict] = None,
                source_fonts: dict = None,
                target_fonts: dict = None) -> list[SlideDiff]:
    """Compare two slides and produce a list of actionable differences."""
    diffs = []

    # Build lookup by shape name
    src_by_name = {s.name: s for s in source_shapes}
    tgt_by_name = {s.name: s for s in target_shapes}

    # --- 0a. Theme font scheme diff ---
    if source_fonts and target_fonts:
        src_major = source_fonts.get('major', '')
        tgt_major = target_fonts.get('major', '')
        src_minor = source_fonts.get('minor', '')
        tgt_minor = target_fonts.get('minor', '')

        # Check if theme font refs (+mj-lt, +mn-lt) are used in the slide
        has_major_ref = '+mj-lt' in target_xml or '+mj-ea' in target_xml
        has_minor_ref = '+mn-lt' in target_xml or '+mn-ea' in target_xml

        if src_major and tgt_major and src_major != tgt_major and has_major_ref:
            diffs.append(SlideDiff(
                category="theme_font",
                shape_name="(theme: major font)",
                description=f"Major heading font differs — used by shapes on this slide",
                source_value=src_major,
                target_value=tgt_major,
                confidence="HIGH",
                action=f'Replace theme font refs (+mj-lt) with explicit "{src_major}" in slide XML',
                xml_fix={"type": "theme_font", "font_role": "major",
                         "source_font": src_major, "target_font": tgt_major},
            ))

        if src_minor and tgt_minor and src_minor != tgt_minor and has_minor_ref:
            diffs.append(SlideDiff(
                category="theme_font",
                shape_name="(theme: minor font)",
                description=f"Minor body font differs — used by shapes on this slide",
                source_value=src_minor,
                target_value=tgt_minor,
                confidence="HIGH",
                action=f'Replace theme font refs (+mn-lt) with explicit "{src_minor}" in slide XML',
                xml_fix={"type": "theme_font", "font_role": "minor",
                         "source_font": src_minor, "target_font": tgt_minor},
            ))

    # --- 0b. Theme color scheme diff ---
    if source_theme and target_theme:
        src_name, src_tc = source_theme
        tgt_name, tgt_tc = target_theme
        if src_tc != tgt_tc:
            # Find which scheme colors are actually used in the slide
            used_roles = set(_extract_scheme_color_usage(target_xml))
            all_roles = sorted(set(src_tc.keys()) | set(tgt_tc.keys()))
            mismatched = []
            for role in all_roles:
                sc = src_tc.get(role, "")
                tc = tgt_tc.get(role, "")
                if sc and tc and sc.upper() != tc.upper():
                    in_use = role in used_roles
                    mismatched.append((role, sc, tc, in_use))

            if mismatched:
                # Summarize theme differences
                used_mismatches = [(r, s, t) for r, s, t, u in mismatched if u]
                unused_mismatches = [(r, s, t) for r, s, t, u in mismatched if not u]

                if used_mismatches:
                    for role, src_hex, tgt_hex in used_mismatches:
                        diffs.append(SlideDiff(
                            category="theme_color",
                            shape_name=f"(theme: {role})",
                            description=f"Theme '{role}' resolves differently — used by shapes on this slide",
                            source_value=f"#{src_hex} ({src_name})",
                            target_value=f"#{tgt_hex} ({tgt_name})",
                            confidence="HIGH",
                            action=f"To match source visuals, replace scheme color references or switch target to source theme",
                            xml_fix={"type": "theme_color", "role": role,
                                     "source_hex": src_hex, "target_hex": tgt_hex},
                        ))

                if unused_mismatches:
                    roles_list = ", ".join(f"{r} (#{s}→#{t})" for r, s, t in unused_mismatches)
                    diffs.append(SlideDiff(
                        category="theme_color",
                        shape_name="(theme: unused roles)",
                        description=f"Theme colors differ but not directly used by slide shapes",
                        source_value=f"{len(unused_mismatches)} roles: {roles_list[:150]}",
                        target_value=f"Different in target theme ({tgt_name})",
                        confidence="LOW",
                        action="Informational — these colors affect layouts/masters but not this slide directly",
                        xml_fix={},
                    ))

    # --- 1. Color palette diff (slide-wide srgb analysis) ---
    src_colors = Counter(_extract_srgb_colors(source_xml))
    tgt_colors = Counter(_extract_srgb_colors(target_xml))

    # Find colors in target that aren't in source (likely wrong palette)
    src_color_set = set(src_colors.keys())
    tgt_color_set = set(tgt_colors.keys())
    tgt_only = tgt_color_set - src_color_set
    src_only = src_color_set - tgt_color_set

    if tgt_only and src_only:
        # Try to map target-only colors to source-only colors by frequency
        src_ranked = sorted(src_only, key=lambda c: src_colors[c], reverse=True)
        tgt_ranked = sorted(tgt_only, key=lambda c: tgt_colors[c], reverse=True)

        for i, tgt_color in enumerate(tgt_ranked):
            if i < len(src_ranked):
                src_color = src_ranked[i]
                diffs.append(SlideDiff(
                    category="color",
                    shape_name="(slide-wide)",
                    description=f"Hardcoded color #{tgt_color} (used {tgt_colors[tgt_color]}x) → #{src_color} (source uses {src_colors[src_color]}x)",
                    source_value=src_color,
                    target_value=tgt_color,
                    confidence="MEDIUM",
                    action=f'Replace all val="{tgt_color}" with val="{src_color}" in slide XML',
                    xml_fix={"find": f'val="{tgt_color}"', "replace": f'val="{src_color}"'},
                ))

    # --- 2. Per-shape comparison ---
    matched_names = set(src_by_name.keys()) & set(tgt_by_name.keys())

    for name in sorted(matched_names):
        src = src_by_name[name]
        tgt = tgt_by_name[name]

        # Text diff
        if src.text != tgt.text and src.text.strip() and tgt.text.strip():
            diffs.append(SlideDiff(
                category="text",
                shape_name=name,
                description="Text content differs",
                source_value=src.text[:200],
                target_value=tgt.text[:200],
                confidence="HIGH",
                action=f"Replace text in shape '{name}'",
                xml_fix={"type": "text_replace", "shape_name": name,
                         "old_text": tgt.text, "new_text": src.text},
            ))

        # Position diff (> 0.1 inch = 91440 EMU threshold)
        threshold_emu = 91440
        if abs(src.left - tgt.left) > threshold_emu or abs(src.top - tgt.top) > threshold_emu:
            diffs.append(SlideDiff(
                category="position",
                shape_name=name,
                description=f"Position differs: source=({src.left},{src.top}) target=({tgt.left},{tgt.top})",
                source_value=f"left={src.left}, top={src.top}",
                target_value=f"left={tgt.left}, top={tgt.top}",
                confidence="MEDIUM",
                action=f"Move shape '{name}' to source position",
                xml_fix={"type": "position", "shape_name": name,
                         "left": src.left, "top": src.top},
            ))

        # Size diff (> 0.1 inch threshold)
        if abs(src.width - tgt.width) > threshold_emu or abs(src.height - tgt.height) > threshold_emu:
            diffs.append(SlideDiff(
                category="size",
                shape_name=name,
                description=f"Size differs: source=({src.width}x{src.height}) target=({tgt.width}x{tgt.height})",
                source_value=f"w={src.width}, h={src.height}",
                target_value=f"w={tgt.width}, h={tgt.height}",
                confidence="MEDIUM",
                action=f"Resize shape '{name}' to source dimensions",
                xml_fix={"type": "size", "shape_name": name,
                         "width": src.width, "height": src.height},
            ))

        # Font property diffs
        if src.font_names and tgt.font_names:
            src_fonts = set(f for f in src.font_names if f)
            tgt_fonts = set(f for f in tgt.font_names if f)
            if src_fonts != tgt_fonts and src_fonts and tgt_fonts:
                diffs.append(SlideDiff(
                    category="font",
                    shape_name=name,
                    description=f"Font differs",
                    source_value=", ".join(sorted(src_fonts)),
                    target_value=", ".join(sorted(tgt_fonts)),
                    confidence="MEDIUM",
                    action=f"Update font in shape '{name}'",
                    xml_fix={"type": "font_name", "shape_name": name,
                             "old_fonts": list(tgt_fonts), "new_fonts": list(src_fonts)},
                ))

        # AutoSize diff (shrink-to-fit vs none)
        if src.auto_size != tgt.auto_size and src.text.strip():
            diffs.append(SlideDiff(
                category="autosize",
                shape_name=name,
                description=f"Text auto-size differs — affects text fitting/wrapping",
                source_value=src.auto_size,
                target_value=tgt.auto_size,
                confidence="HIGH",
                action=f"Set auto-size on '{name}' to match source ({src.auto_size})",
                xml_fix={"type": "autosize", "shape_name": name,
                         "source_autosize": src.auto_size},
            ))

        # Margin diffs (affects text fitting)
        margin_threshold = 18288  # ~0.02 inch
        for margin_name, src_val, tgt_val in [
            ("left", src.margin_left, tgt.margin_left),
            ("right", src.margin_right, tgt.margin_right),
            ("top", src.margin_top, tgt.margin_top),
            ("bottom", src.margin_bottom, tgt.margin_bottom),
        ]:
            if src_val >= 0 and tgt_val >= 0 and abs(src_val - tgt_val) > margin_threshold:
                diffs.append(SlideDiff(
                    category="margin",
                    shape_name=name,
                    description=f"Text margin-{margin_name} differs ({src_val} vs {tgt_val} EMU)",
                    source_value=str(src_val),
                    target_value=str(tgt_val),
                    confidence="HIGH",
                    action=f"Set margin-{margin_name} on '{name}' to {src_val}",
                    xml_fix={"type": "margin", "shape_name": name,
                             "margin_name": margin_name, "value": src_val},
                ))

        # Inherited font detection (no explicit typeface — relies on theme)
        if tgt.has_inherited_font and not src.has_inherited_font:
            diffs.append(SlideDiff(
                category="inherited_font",
                shape_name=name,
                description="Target uses inherited theme font; source has explicit font — may render differently across themes",
                source_value="explicit typeface",
                target_value="inherited from theme",
                confidence="MEDIUM",
                action=f"Inject explicit font into '{name}' to match source",
                xml_fix={"type": "inject_font", "shape_name": name},
            ))
        elif src.has_inherited_font and tgt.has_inherited_font and source_fonts and target_fonts:
            # Both inherit from theme but themes have different fonts
            src_major = source_fonts.get('major', '')
            tgt_major = target_fonts.get('major', '')
            src_minor = source_fonts.get('minor', '')
            tgt_minor = target_fonts.get('minor', '')
            if src_major != tgt_major or src_minor != tgt_minor:
                is_title = 'Title' in name or 'title' in name
                resolved_src = src_major if is_title else src_minor
                resolved_tgt = tgt_major if is_title else tgt_minor
                if resolved_src != resolved_tgt:
                    diffs.append(SlideDiff(
                        category="inherited_font",
                        shape_name=name,
                        description=f"Both inherit theme font but themes differ — renders as '{resolved_src}' vs '{resolved_tgt}'",
                        source_value=resolved_src,
                        target_value=resolved_tgt,
                        confidence="HIGH",
                        action=f"Inject explicit '{resolved_src}' font into '{name}'",
                        xml_fix={"type": "inject_font", "shape_name": name,
                                 "font": resolved_src},
                    ))

        # Font color diffs
        if src.font_colors and tgt.font_colors:
            src_fc = set(src.font_colors)
            tgt_fc = set(tgt.font_colors)
            if src_fc != tgt_fc:
                diffs.append(SlideDiff(
                    category="font_color",
                    shape_name=name,
                    description=f"Font color differs",
                    source_value=", ".join(sorted(src_fc)),
                    target_value=", ".join(sorted(tgt_fc)),
                    confidence="HIGH",
                    action=f"Update font color in shape '{name}'",
                    xml_fix={"type": "font_color", "shape_name": name,
                             "old_colors": list(tgt_fc), "new_colors": list(src_fc)},
                ))

        # Fill color diff
        if src.fill_color and tgt.fill_color and src.fill_color != tgt.fill_color:
            diffs.append(SlideDiff(
                category="fill",
                shape_name=name,
                description=f"Shape fill color differs",
                source_value=src.fill_color,
                target_value=tgt.fill_color,
                confidence="HIGH",
                action=f"Update fill in shape '{name}': #{tgt.fill_color} → #{src.fill_color}",
                xml_fix={"find": f'val="{tgt.fill_color}"', "replace": f'val="{src.fill_color}"'},
            ))

        # Image diff
        if src.image_hash and tgt.image_hash and src.image_hash != tgt.image_hash:
            diffs.append(SlideDiff(
                category="image",
                shape_name=name,
                description="Image content differs (different file)",
                source_value=f"md5={src.image_hash[:12]}...",
                target_value=f"md5={tgt.image_hash[:12]}...",
                confidence="LOW",
                action=f"Replace image in shape '{name}' — manual review recommended",
                xml_fix={"type": "image_replace", "shape_name": name},
            ))

    # --- 3. Shapes in source but not target ---
    for name in sorted(set(src_by_name.keys()) - matched_names):
        src = src_by_name[name]
        if src.text.strip() or src.image_hash:
            diffs.append(SlideDiff(
                category="missing_shape",
                shape_name=name,
                description=f"Shape exists in source but not in target",
                source_value=f"type={src.shape_type}, text='{src.text[:80]}'",
                target_value="(not present)",
                confidence="LOW",
                action="Manual intervention — shape would need to be added",
                xml_fix={},
            ))

    # --- 4. Shapes in target but not source ---
    for name in sorted(set(tgt_by_name.keys()) - matched_names):
        tgt = tgt_by_name[name]
        if tgt.text.strip() or tgt.image_hash:
            diffs.append(SlideDiff(
                category="extra_shape",
                shape_name=name,
                description=f"Shape exists in target but not in source",
                source_value="(not present)",
                target_value=f"type={tgt.shape_type}, text='{tgt.text[:80]}'",
                confidence="LOW",
                action="Manual intervention — shape may need to be removed",
                xml_fix={},
            ))

    return diffs


# ============================================================
# Interactive Alignment
# ============================================================

CATEGORY_ICONS = {
    "color": "🎨", "text": "📝", "position": "📐", "size": "📏",
    "font": "🔤", "font_color": "🖌️", "fill": "🪣", "image": "🖼️",
    "missing_shape": "➕", "extra_shape": "➖",
    "theme_color": "🎨", "theme_font": "🔤",
    "autosize": "📐", "margin": "↔️", "inherited_font": "🔤",
}

CONFIDENCE_COLORS = {"HIGH": "\033[92m", "MEDIUM": "\033[93m", "LOW": "\033[91m"}
RESET = "\033[0m"


def _print_diff(idx: int, total: int, d: SlideDiff):
    icon = CATEGORY_ICONS.get(d.category, "🔍")
    conf_color = CONFIDENCE_COLORS.get(d.confidence, "")
    print(f"\n{'═' * 64}")
    print(f"  {icon}  DIFFERENCE {idx}/{total} — {d.category.upper().replace('_', ' ')}")
    print(f"  Shape: \"{d.shape_name}\"")
    print(f"{'─' * 64}")
    print(f"  {d.description}")
    print(f"  SOURCE: {d.source_value}")
    print(f"  TARGET: {d.target_value}")
    print(f"  Confidence: {conf_color}{d.confidence}{RESET}")
    print(f"  Proposed:   {d.action}")
    print(f"{'═' * 64}")


def interactive_align(diffs: list[SlideDiff], source_label: str, target_label: str) -> list[SlideDiff]:
    """Present each diff interactively. Returns list of approved diffs."""
    if not diffs:
        print("\n✅ No structural differences detected.")
        return []

    print(f"\n{'━' * 64}")
    print(f"  INTERACTIVE ALIGNMENT")
    print(f"  Source: {source_label}")
    print(f"  Target: {target_label}")
    print(f"  {len(diffs)} difference(s) found")
    print(f"{'━' * 64}")

    # Summarize by category
    cats = Counter(d.category for d in diffs)
    for cat, count in cats.most_common():
        icon = CATEGORY_ICONS.get(cat, "🔍")
        print(f"  {icon} {cat}: {count}")

    print(f"\nFor each difference:")
    print(f"  [A]pprove — apply this change")
    print(f"  [M]odify  — edit the proposed value before applying")
    print(f"  [S]kip    — leave as-is")
    print(f"  [AA]      — approve ALL remaining")
    print(f"  [Q]uit    — stop, apply nothing further\n")

    approved = []
    approve_all = False

    for i, d in enumerate(diffs, 1):
        _print_diff(i, len(diffs), d)

        if approve_all:
            if d.xml_fix and d.confidence != "LOW":
                print(f"  → Auto-approved (approve-all mode)")
                approved.append(d)
            else:
                print(f"  → Skipped (LOW confidence, needs manual review)")
            continue

        while True:
            choice = input("  [A]pprove / [M]odify / [S]kip / [AA] All / [Q]uit > ").strip().upper()

            if choice == "A":
                if not d.xml_fix:
                    print("  ⚠️  No automated fix available — flagged for manual review.")
                    break
                approved.append(d)
                print(f"  ✅ Approved")
                break

            elif choice == "M":
                if d.category == "color" and "find" in d.xml_fix:
                    new_val = input(f"  Enter replacement color (hex, current={d.source_value}): ").strip().upper()
                    if len(new_val) == 6 and all(c in "0123456789ABCDEF" for c in new_val):
                        d.source_value = new_val
                        d.xml_fix["replace"] = f'val="{new_val}"'
                        d.action = f'Replace val="{d.target_value}" with val="{new_val}"'
                        approved.append(d)
                        print(f"  ✅ Modified and approved")
                    else:
                        print("  ⚠️  Invalid hex color. Try again or [S]kip.")
                        continue
                elif d.category == "text" and d.xml_fix.get("type") == "text_replace":
                    print(f"  Current source text: {d.source_value}")
                    new_text = input("  Enter replacement text (or press Enter to keep source): ").strip()
                    if new_text:
                        d.xml_fix["new_text"] = new_text
                        d.source_value = new_text[:200]
                    approved.append(d)
                    print(f"  ✅ Modified and approved")
                else:
                    print("  ⚠️  Modify not supported for this diff type. [A]pprove or [S]kip.")
                    continue
                break

            elif choice == "AA":
                # Approve this one and all remaining
                if d.xml_fix and d.confidence != "LOW":
                    approved.append(d)
                    print(f"  ✅ Approved (+ all remaining)")
                approve_all = True
                break

            elif choice == "S":
                print(f"  ⏭️  Skipped")
                break

            elif choice == "Q":
                print(f"\n  Stopping. {len(approved)} change(s) queued.")
                return approved

            else:
                print("  Invalid choice. Use A, M, S, AA, or Q.")

    print(f"\n{'━' * 64}")
    print(f"  ✅ Alignment complete: {len(approved)} change(s) approved out of {len(diffs)}")
    print(f"{'━' * 64}")
    return approved


# ============================================================
# Execution Engine — Apply Changes
# ============================================================

def _find_skill_scripts() -> Optional[str]:
    """Locate the PPTX skill scripts directory."""
    candidates = [
        os.path.expanduser(r"~\.copilot\skills\pptx\scripts"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _hide_slide(slide_xml_path: str):
    """Set the show="0" attribute on a slide to hide it in the slideshow."""
    with open(slide_xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add show="0" to the root <p:sld> element
    if '<p:sld ' in content:
        if 'show="' not in content.split('>', 1)[0]:
            content = content.replace('<p:sld ', '<p:sld show="0" ', 1)
        else:
            content = re.sub(r'show="\d+"', 'show="0"', content, count=1)
    elif '<p:sld>' in content:
        content = content.replace('<p:sld>', '<p:sld show="0">', 1)

    with open(slide_xml_path, "w", encoding="utf-8") as f:
        f.write(content)


def _insert_slide_after(pres_xml_path: str, original_filename: str,
                        new_filename: str, add_slide_output: str):
    """Insert the new slide's <p:sldId> right after the original in presentation.xml."""
    with open(pres_xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract the <p:sldId> line from add_slide.py output
    sld_id_match = re.search(r'(<p:sldId\s+id="[^"]*"\s+r:id="[^"]*"\s*/>)', add_slide_output)
    if not sld_id_match:
        # Build it manually — find the rId for the new slide in rels
        rels_path = os.path.join(os.path.dirname(pres_xml_path), "_rels", "presentation.xml.rels")
        if os.path.exists(rels_path):
            with open(rels_path, "r", encoding="utf-8") as f:
                rels_content = f.read()
            # Find rId for the new slide
            rid_match = re.search(rf'Id="(rId\d+)"[^>]*Target="slides/{re.escape(new_filename)}"', rels_content)
            if rid_match:
                rid = rid_match.group(1)
                # Find max sldId in presentation.xml
                existing_ids = [int(m) for m in re.findall(r'<p:sldId id="(\d+)"', content)]
                new_id = max(existing_ids) + 1 if existing_ids else 256
                sld_id_xml = f'<p:sldId id="{new_id}" r:id="{rid}"/>'
            else:
                print(f"  ⚠️  Could not find rId for {new_filename} in rels")
                return
        else:
            print(f"  ⚠️  Could not find presentation.xml.rels")
            return
    else:
        sld_id_xml = sld_id_match.group(1)

    # Find the <p:sldId> for the original slide and insert the new one right after it
    # First, find the rId for the original slide
    rels_path = os.path.join(os.path.dirname(pres_xml_path), "_rels", "presentation.xml.rels")
    with open(rels_path, "r", encoding="utf-8") as f:
        rels_content = f.read()

    orig_rid_match = re.search(rf'Id="(rId\d+)"[^>]*Target="slides/{re.escape(original_filename)}"', rels_content)
    if orig_rid_match:
        orig_rid = orig_rid_match.group(1)
        # Find the sldId line with this rId and insert the new one after it
        pattern = rf'(<p:sldId[^>]*r:id="{re.escape(orig_rid)}"[^/]*/?>)'
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + "\n      " + sld_id_xml + content[insert_pos:]
            print(f"  ✅ Inserted {new_filename} after {original_filename} in sldIdLst")
        else:
            # Fallback: append at end of sldIdLst
            content = content.replace('</p:sldIdLst>', f'  {sld_id_xml}\n    </p:sldIdLst>')
            print(f"  ⚠️  Could not find original in sldIdLst, appended at end")
    else:
        content = content.replace('</p:sldIdLst>', f'  {sld_id_xml}\n    </p:sldIdLst>')
        print(f"  ⚠️  Could not find rId for {original_filename}, appended at end")

    with open(pres_xml_path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_changes(target_path: str, slide_number: int, approved: list[SlideDiff]) -> str | None:
    """Apply approved diffs to the target PPTX.
    
    Strategy: keep the original slide but hide it, then insert the modified
    version right after it. This lets the reviewer compare both in PowerPoint,
    decide which to keep, and delete the other.
    
    Returns path to modified file or None."""
    if not approved:
        print("\nNo changes to apply.")
        return None

    scripts_dir = _find_skill_scripts()
    if not scripts_dir:
        print("ERROR: Cannot find PPTX skill scripts directory.")
        return None

    # Categorize changes
    xml_replacements = []
    structural_changes = []
    theme_fixes = []
    font_fixes = []

    for d in approved:
        if "find" in d.xml_fix and "replace" in d.xml_fix:
            xml_replacements.append(d)
        elif d.xml_fix.get("type") == "theme_color":
            theme_fixes.append(d)
        elif d.xml_fix.get("type") == "theme_font":
            font_fixes.append(d)
        elif d.xml_fix.get("type") in ("text_replace", "position", "size",
                                       "autosize", "margin", "inject_font"):
            structural_changes.append(d)
        else:
            print(f"  ⚠️  Skipping unsupported fix type for '{d.shape_name}'")

    if not xml_replacements and not structural_changes and not theme_fixes and not font_fixes:
        print("\nNo executable changes.")
        return None

    # Set up build directory
    build_dir = os.path.join(tempfile.gettempdir(), "pptx_align_build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    unpack_dir = os.path.join(build_dir, "unpacked")

    print(f"\n📦 Unpacking target: {os.path.basename(target_path)}")
    unpack_script = os.path.join(scripts_dir, "office", "unpack.py")
    subprocess.run([sys.executable, unpack_script, target_path, unpack_dir], check=True)

    # Find the slide XML file for the target slide
    slide_filename = _get_slide_filename(target_path, slide_number)
    slide_xml_path = os.path.join(unpack_dir, "ppt", "slides", slide_filename)

    if not os.path.exists(slide_xml_path):
        print(f"ERROR: Slide XML not found: {slide_xml_path}")
        return None

    # Step 1: Duplicate the slide (creates a copy we'll modify)
    print(f"\n📋 Duplicating slide {slide_number} ({slide_filename})...")
    add_slide_script = os.path.join(scripts_dir, "add_slide.py")
    dup_result = subprocess.run(
        [sys.executable, add_slide_script, unpack_dir, slide_filename],
        capture_output=True, text=True
    )
    if dup_result.returncode != 0:
        print(f"  ERROR: add_slide.py failed: {dup_result.stderr[:200]}")
        return None

    # Parse the output to get the new slide filename and sldId XML
    dup_output = dup_result.stdout.strip()
    print(f"  {dup_output[:200]}")

    # Extract new slide filename from add_slide.py output (e.g. "Created slide20.xml from slide19.xml")
    new_file_match = re.search(r'Created (slide\d+\.xml)', dup_output)
    if new_file_match:
        new_slide_filename = new_file_match.group(1)
    else:
        # Fallback: find the highest-numbered slide file
        slides_dir = os.path.join(unpack_dir, "ppt", "slides")
        import glob as glob_mod
        all_slides = glob_mod.glob(os.path.join(slides_dir, "slide*.xml"))
        # Sort numerically by extracting the number
        def slide_num(path):
            m = re.search(r'slide(\d+)\.xml', path)
            return int(m.group(1)) if m else 0
        all_slides.sort(key=slide_num)
        new_slide_filename = os.path.basename(all_slides[-1])

    slides_dir = os.path.join(unpack_dir, "ppt", "slides")
    new_slide_path = os.path.join(slides_dir, new_slide_filename)
    print(f"  New slide file: {new_slide_filename}")

    # Step 2: Apply all changes to the NEW slide (not the original)
    print(f"\n🔧 Applying changes to {new_slide_filename}...")
    with open(new_slide_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    changes_made = 0

    # Apply XML find/replace changes (colors, fills)
    for d in xml_replacements:
        old = d.xml_fix["find"]
        new = d.xml_fix["replace"]
        count = xml_content.count(old)
        if count > 0:
            xml_content = xml_content.replace(old, new)
            print(f"  🎨 Color fix: {old} → {new} ({count} occurrences)")
            changes_made += count

    # Apply theme color fixes — replace schemeClr references with hardcoded source hex
    for d in theme_fixes:
        role = d.xml_fix["role"]
        src_hex = d.xml_fix["source_hex"]
        # Replace <a:schemeClr val="accent1"/> with <a:srgbClr val="091F2C"/>
        # Also handle <a:schemeClr val="accent1"> (with child elements like <a:lumMod>)
        simple_pattern = f'<a:schemeClr val="{role}"/>'
        simple_replace = f'<a:srgbClr val="{src_hex}"/>'
        count = xml_content.count(simple_pattern)
        if count > 0:
            xml_content = xml_content.replace(simple_pattern, simple_replace)
            print(f"  🎨 Theme fix: {role} → #{src_hex} ({count} simple refs)")
            changes_made += count

        # Handle schemeClr with child modifiers (lumMod, lumOff, tint, shade, alpha)
        # <a:schemeClr val="accent1"><a:lumMod val="75000"/></a:schemeClr>
        # → <a:srgbClr val="091F2C"><a:lumMod val="75000"/></a:srgbClr>
        mod_pattern = rf'<a:schemeClr val="{re.escape(role)}">(.*?)</a:schemeClr>'
        mod_replace = rf'<a:srgbClr val="{src_hex}">\1</a:srgbClr>'
        xml_content, mod_count = re.subn(mod_pattern, mod_replace, xml_content, flags=re.DOTALL)
        if mod_count:
            print(f"  🎨 Theme fix: {role} → #{src_hex} ({mod_count} modified refs with child elements)")
            changes_made += mod_count

    # Apply theme font fixes — replace +mj-lt/+mn-lt refs with explicit font names
    for d in font_fixes:
        src_font = d.xml_fix["source_font"]
        font_role = d.xml_fix["font_role"]

        if font_role == "major":
            # +mj-lt = major latin, +mj-ea = major east asian, +mj-cs = major complex script
            refs = [('+mj-lt', src_font), ('+mj-ea', src_font), ('+mj-cs', src_font)]
        else:
            refs = [('+mn-lt', src_font), ('+mn-ea', src_font), ('+mn-cs', src_font)]

        for ref, replacement in refs:
            # Replace typeface="+mj-lt" with typeface="Segoe UI Semibold"
            old_attr = f'typeface="{ref}"'
            new_attr = f'typeface="{replacement}"'
            count = xml_content.count(old_attr)
            if count > 0:
                xml_content = xml_content.replace(old_attr, new_attr)
                print(f"  🔤 Font fix: {ref} → \"{replacement}\" ({count} refs)")
                changes_made += count

    # Apply structural changes via python-pptx on the raw XML
    for d in structural_changes:
        fix_type = d.xml_fix.get("type")

        if fix_type == "text_replace":
            old_text = d.xml_fix.get("old_text", "")
            new_text = d.xml_fix.get("new_text", "")
            # For text, we do a simple content replacement in <a:t> elements
            # This preserves formatting runs
            if old_text and new_text and old_text != new_text:
                # Split into lines and replace matching <a:t> content
                for old_line, new_line in zip(old_text.split("\n"), new_text.split("\n")):
                    if old_line.strip() and old_line != new_line:
                        escaped_old = html.escape(old_line.strip())
                        escaped_new = html.escape(new_line.strip())
                        pattern = f">{escaped_old}</a:t>"
                        replacement = f">{escaped_new}</a:t>"
                        if pattern in xml_content:
                            xml_content = xml_content.replace(pattern, replacement, 1)
                            print(f"  📝 Text: \"{old_line.strip()[:40]}\" → \"{new_line.strip()[:40]}\"")
                            changes_made += 1

        elif fix_type == "position":
            shape_name = d.xml_fix["shape_name"]
            new_left = d.xml_fix["left"]
            new_top = d.xml_fix["top"]
            # Find the shape's <a:off> element and update x/y
            # This is a regex-based approach on the raw XML
            name_pattern = f'name="{re.escape(shape_name)}"'
            if name_pattern in xml_content:
                # Find the <p:sp> block containing this shape name
                # Then update the <a:off> within it
                print(f"  📐 Position update for '{shape_name}': queued (applied via python-pptx)")
                changes_made += 1

        elif fix_type == "size":
            print(f"  📏 Size update for '{d.xml_fix['shape_name']}': queued")
            changes_made += 1

        elif fix_type == "autosize":
            shape_name = d.xml_fix["shape_name"]
            src_autosize = d.xml_fix["source_autosize"]
            escaped_name = re.escape(shape_name)
            # Map python-pptx auto_size strings to XML bodyPr attributes
            # SHAPE_TO_FIT_TEXT (1) = spAutoFit, TEXT_TO_FIT_SHAPE = normAutofit, NONE = no attribute
            if "SHAPE_TO_FIT" in src_autosize:
                # Add <a:spAutoFit/> to bodyPr
                pattern = rf'(name="{escaped_name}".*?<a:bodyPr)([^>]*?)(/?>)'
                match = re.search(pattern, xml_content, re.DOTALL)
                if match:
                    prefix, attrs, close = match.group(1), match.group(2), match.group(3)
                    if close == '/>':
                        new_body = f'{prefix}{attrs}><a:spAutoFit/></a:bodyPr>'
                    else:
                        # Already has children, inject spAutoFit
                        new_body = f'{prefix}{attrs}><a:spAutoFit/>'
                    xml_content = xml_content[:match.start()] + new_body + xml_content[match.end():]
                    print(f"  📐 AutoSize: set spAutoFit on '{shape_name}'")
                    changes_made += 1
            elif "TEXT_TO_FIT" in src_autosize:
                pattern = rf'(name="{escaped_name}".*?<a:bodyPr)([^>]*?)(/?>)'
                match = re.search(pattern, xml_content, re.DOTALL)
                if match:
                    prefix, attrs, close = match.group(1), match.group(2), match.group(3)
                    if close == '/>':
                        new_body = f'{prefix}{attrs}><a:normAutofit/></a:bodyPr>'
                    else:
                        new_body = f'{prefix}{attrs}><a:normAutofit/>'
                    xml_content = xml_content[:match.start()] + new_body + xml_content[match.end():]
                    print(f"  📐 AutoSize: set normAutofit on '{shape_name}'")
                    changes_made += 1

        elif fix_type == "margin":
            shape_name = d.xml_fix["shape_name"]
            margin_name = d.xml_fix["margin_name"]
            value = d.xml_fix["value"]
            escaped_name = re.escape(shape_name)
            # Map margin names to bodyPr attributes
            attr_map = {"left": "lIns", "right": "rIns", "top": "tIns", "bottom": "bIns"}
            attr = attr_map.get(margin_name)
            if attr:
                pattern = rf'(name="{escaped_name}".*?<a:bodyPr[^>]*?){attr}="\d+"'
                new_val = f'\\g<1>{attr}="{value}"'
                xml_content, n = re.subn(pattern, new_val, xml_content, count=1, flags=re.DOTALL)
                if n:
                    print(f"  ↔️  Margin: {margin_name}={value} on '{shape_name}'")
                    changes_made += 1
                else:
                    # Attribute doesn't exist yet — add it to bodyPr
                    pattern2 = rf'(name="{escaped_name}".*?<a:bodyPr)'
                    new_val2 = rf'\g<1> {attr}="{value}"'
                    xml_content, n2 = re.subn(pattern2, new_val2, xml_content, count=1, flags=re.DOTALL)
                    if n2:
                        print(f"  ↔️  Margin: added {margin_name}={value} on '{shape_name}'")
                        changes_made += 1

        elif fix_type == "inject_font":
            shape_name = d.xml_fix["shape_name"]
            font = d.xml_fix.get("font", "")
            if font:
                escaped_name = re.escape(shape_name)
                # Find all <a:rPr> within this shape that lack a <a:latin> child
                # Strategy: find the shape block, then add typeface to rPr elements
                shape_pattern = rf'(name="{escaped_name}".*?</p:sp>)'
                shape_match = re.search(shape_pattern, xml_content, re.DOTALL)
                if shape_match:
                    shape_block = shape_match.group(0)
                    # Add <a:latin typeface="Font"/> after <a:rPr ...> where no latin exists
                    # Match rPr that don't already have a latin child
                    def add_latin(m):
                        rpr_content = m.group(0)
                        if '<a:latin' not in rpr_content:
                            # Insert before closing </a:rPr> or before />
                            if '</a:rPr>' in rpr_content:
                                return rpr_content.replace('</a:rPr>',
                                    f'<a:latin typeface="{font}"/></a:rPr>')
                            elif rpr_content.endswith('/>'):
                                return rpr_content[:-2] + f'><a:latin typeface="{font}"/></a:rPr>'
                        return rpr_content

                    new_block, count = re.subn(r'<a:rPr[^>]*?(?:/>|>.*?</a:rPr>)',
                                                add_latin, shape_block, flags=re.DOTALL)
                    if new_block != shape_block:
                        xml_content = xml_content[:shape_match.start()] + new_block + xml_content[shape_match.end():]
                        inject_count = new_block.count(f'typeface="{font}"') - shape_block.count(f'typeface="{font}"')
                        print(f"  🔤 Injected '{font}' into {inject_count} run(s) of '{shape_name}'")
                        changes_made += inject_count

    # Write modified XML to the NEW slide
    with open(new_slide_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"\n  Applied {changes_made} change(s) to {new_slide_filename}")

    # Apply position/size changes via python-pptx (more reliable than regex)
    position_size_changes = [d for d in structural_changes
                             if d.xml_fix.get("type") in ("position", "size")]
    if position_size_changes:
        _apply_position_size_via_xml(new_slide_path, position_size_changes)

    # Step 3: Hide the original slide and insert the new one right after it
    print(f"\n👁️  Hiding original slide {slide_number} ({slide_filename})...")
    _hide_slide(slide_xml_path)

    # Add the new slide's <p:sldId> right after the original in presentation.xml
    pres_xml_path = os.path.join(unpack_dir, "ppt", "presentation.xml")
    _insert_slide_after(pres_xml_path, slide_filename, new_slide_filename, dup_output)

    # Clean
    print(f"\n🧹 Cleaning...")
    clean_script = os.path.join(scripts_dir, "clean.py")
    clean_result = subprocess.run([sys.executable, clean_script, unpack_dir], capture_output=True, text=True)
    if clean_result.returncode != 0:
        print(f"  ⚠️  clean.py exit code {clean_result.returncode} (continuing anyway)")
        if clean_result.stderr:
            for line in clean_result.stderr.strip().split('\n')[-3:]:
                print(f"  {line}")

    # Pack
    output_path = os.path.join(build_dir, "aligned_output.pptx")
    print(f"📦 Packing...")
    pack_script = os.path.join(scripts_dir, "office", "pack.py")
    pack_result = subprocess.run([sys.executable, pack_script, unpack_dir, output_path,
                    "--original", target_path], capture_output=True, text=True)
    if pack_result.returncode != 0:
        print(f"  ⚠️  pack.py exit code {pack_result.returncode}")
        if pack_result.stderr:
            for line in pack_result.stderr.strip().split('\n')[-3:]:
                print(f"  {line}")
        if not os.path.exists(output_path):
            print("  ERROR: Output file was not created.")
            return None

    # Copy to a user-friendly staging location
    staging_path = os.path.join(tempfile.gettempdir(), "aligned_staging.pptx")
    shutil.copy2(output_path, staging_path)

    print(f"\n✅ Aligned file ready: {staging_path}")
    print(f"   Slide {slide_number} is now HIDDEN (original)")
    print(f"   Slide {slide_number + 1} is the ALIGNED version")
    print(f"   → Open in PowerPoint to compare, then delete whichever you don't want")
    return staging_path


def _apply_position_size_via_xml(slide_xml_path: str, changes: list[SlideDiff]):
    """Update shape positions and sizes directly in the XML."""
    with open(slide_xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    for d in changes:
        shape_name = d.xml_fix["shape_name"]
        escaped_name = re.escape(shape_name)

        if d.xml_fix["type"] == "position":
            new_x = d.xml_fix["left"]
            new_y = d.xml_fix["top"]
            # Find <p:sp> containing this name, then update its <a:off>
            # Pattern: ...name="ShapeName"... then first <a:off x="..." y="..."/>
            pattern = rf'(name="{escaped_name}".*?<a:off\s+)x="\d+"\s+y="\d+"'
            replacement = rf'\1x="{new_x}" y="{new_y}"'
            content, n = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
            if n:
                print(f"  📐 Moved '{shape_name}' to ({new_x}, {new_y})")

        elif d.xml_fix["type"] == "size":
            new_cx = d.xml_fix["width"]
            new_cy = d.xml_fix["height"]
            pattern = rf'(name="{escaped_name}".*?<a:ext\s+)cx="\d+"\s+cy="\d+"'
            replacement = rf'\1cx="{new_cx}" cy="{new_cy}"'
            content, n = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
            if n:
                print(f"  📏 Resized '{shape_name}' to ({new_cx}, {new_cy})")

    with open(slide_xml_path, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Visual PPTX Comparison + Interactive Alignment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file_a", help="First PPTX file")
    parser.add_argument("file_b", help="Second PPTX file")
    parser.add_argument("--slides", help="Slide numbers (e.g. 5 or 5,8,12 or 5:10)")
    parser.add_argument("--map", dest="slide_map", help="Cross-map (e.g. 14:9,15:10)")
    parser.add_argument("--align", action="store_true", help="Enable interactive alignment")
    parser.add_argument("--out", help="Output HTML report path")
    parser.add_argument("--width", type=int, default=1920, help="Export width (default: 1920)")
    parser.add_argument("--no-diff", action="store_true", help="Skip pixel-diff overlay")
    parser.add_argument("--no-visual", action="store_true", help="Skip visual export (structural only)")
    args = parser.parse_args()

    # Validate inputs
    for f in [args.file_a, args.file_b]:
        if not os.path.exists(f):
            print(f"ERROR: File not found: {f}")
            sys.exit(1)

    if args.align and not HAS_PPTX:
        print("ERROR: python-pptx required for --align. Install: pip install python-pptx")
        sys.exit(1)

    # Parse slide selections
    if args.slide_map:
        pairs = parse_map_arg(args.slide_map)
        slides_a = [p[0] for p in pairs]
        slides_b = [p[1] for p in pairs]
    elif args.slides:
        slide_list = parse_slides_arg(args.slides)
        slides_a = slides_b = slide_list
        pairs = list(zip(slides_a, slides_b))
    else:
        slides_a = slides_b = None
        pairs = None

    # --- Phase 1: Visual Comparison ---
    if not args.no_visual:
        if not HAS_COM:
            print("WARNING: pywin32 not installed. Skipping visual comparison.")
        else:
            output_path = args.out or os.path.join(tempfile.gettempdir(), "compare_slides_output.html")

            tmp_root = tempfile.mkdtemp(prefix="pptx_compare_")
            dir_a = os.path.join(tmp_root, "file_a")
            dir_b = os.path.join(tmp_root, "file_b")
            dir_diff = os.path.join(tmp_root, "diff")
            os.makedirs(dir_a); os.makedirs(dir_b); os.makedirs(dir_diff)

            # Share a single PowerPoint COM instance for both exports
            pythoncom.CoInitialize()
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            ppt_app.Visible = True
            ppt_app.WindowState = 2  # minimized

            try:
                print(f"\nExporting from A: {os.path.basename(args.file_a)}")
                exported_a = export_slides_com(args.file_a, dir_a, slides_a, args.width, ppt_app)

                print(f"\nExporting from B: {os.path.basename(args.file_b)}")
                exported_b = export_slides_com(args.file_b, dir_b, slides_b, args.width, ppt_app)
            finally:
                pythoncom.CoUninitialize()

            if pairs is None:
                common = sorted(set(exported_a.keys()) & set(exported_b.keys()))
                pairs = [(s, s) for s in common]
                slides_a = [p[0] for p in pairs]
                slides_b = [p[1] for p in pairs]

            comparisons = []
            print(f"\nGenerating comparisons...")
            for sa, sb in pairs:
                if sa not in exported_a or sb not in exported_b:
                    continue
                comp = {"slide_a": sa, "slide_b": sb,
                        "img_a": exported_a[sa], "img_b": exported_b[sb], "img_diff": None}
                if not args.no_diff:
                    dp = os.path.join(dir_diff, f"diff_{sa}_{sb}.png")
                    comp["img_diff"] = generate_diff_image(exported_a[sa], exported_b[sb], dp)
                comparisons.append(comp)
                print(f"  Compared slide {sa} (A) ↔ {sb} (B)")

            if comparisons:
                generate_html_report(args.file_a, args.file_b, comparisons, output_path)
                print(f"\n✅ Visual report: {output_path}")
                webbrowser.open(f"file:///{output_path.replace(os.sep, '/')}")

    # --- Phase 2: Structural Analysis + Alignment ---
    if args.align:
        if pairs is None:
            print("ERROR: --align requires --slides or --map to identify which slides to align.")
            sys.exit(1)

        print(f"\n{'━' * 64}")
        print(f"  STRUCTURAL ANALYSIS")
        print(f"{'━' * 64}")

        # Ask which file is the source
        print(f"\n  A: {os.path.basename(args.file_a)}")
        print(f"  B: {os.path.basename(args.file_b)}")
        while True:
            source_choice = input("\n  Which file is the SOURCE (truth)? [A/B] > ").strip().upper()
            if source_choice in ("A", "B"):
                break
            print("  Please enter A or B.")

        if source_choice == "A":
            source_path, target_path = args.file_a, args.file_b
            source_label = f"A: {os.path.basename(args.file_a)}"
            target_label = f"B: {os.path.basename(args.file_b)}"
            analysis_pairs = pairs
        else:
            source_path, target_path = args.file_b, args.file_a
            source_label = f"B: {os.path.basename(args.file_b)}"
            target_label = f"A: {os.path.basename(args.file_a)}"
            analysis_pairs = [(b, a) for a, b in pairs]

        all_approved = []
        for src_num, tgt_num in analysis_pairs:
            print(f"\n  Analyzing slide {src_num} (source) vs slide {tgt_num} (target)...")

            src_shapes = analyze_slide(source_path, src_num)
            tgt_shapes = analyze_slide(target_path, tgt_num)
            src_xml = _get_slide_xml(source_path, src_num)
            tgt_xml = _get_slide_xml(target_path, tgt_num)

            # Extract theme color schemes and fonts for comparison
            src_theme = _get_theme_colors(source_path, src_num)
            tgt_theme = _get_theme_colors(target_path, tgt_num)
            src_fonts = _get_theme_fonts(source_path, src_num)
            tgt_fonts = _get_theme_fonts(target_path, tgt_num)

            print(f"  Source: {len(src_shapes)} shapes | Target: {len(tgt_shapes)} shapes")
            if src_theme[0] != tgt_theme[0]:
                print(f"  Themes differ: '{src_theme[0]}' vs '{tgt_theme[0]}'")
            if src_fonts.get('major') != tgt_fonts.get('major') or src_fonts.get('minor') != tgt_fonts.get('minor'):
                print(f"  Fonts differ: '{src_fonts.get('major','?')}/{src_fonts.get('minor','?')}' vs '{tgt_fonts.get('major','?')}/{tgt_fonts.get('minor','?')}'")

            diffs = diff_slides(src_shapes, tgt_shapes, src_xml, tgt_xml,
                                source_theme=src_theme, target_theme=tgt_theme,
                                source_fonts=src_fonts, target_fonts=tgt_fonts)
            approved = interactive_align(diffs, source_label, target_label)

            if approved:
                print(f"\n  Applying {len(approved)} change(s) to slide {tgt_num}...")
                result = apply_changes(target_path, tgt_num, approved)
                if result:
                    all_approved.extend(approved)

        if all_approved:
            print(f"\n{'━' * 64}")
            print(f"  ALIGNMENT COMPLETE")
            print(f"  {len(all_approved)} total change(s) applied")
            print(f"  Staging file: {os.path.join(tempfile.gettempdir(), 'aligned_staging.pptx')}")
            print(f"")
            print(f"  Review workflow:")
            print(f"  1. Open in PowerPoint (repair if prompted)")
            print(f"  2. Original slide is HIDDEN — unhide to compare side-by-side")
            print(f"  3. Aligned version is right after the original")
            print(f"  4. Keep whichever looks better, delete the other")
            print(f"{'━' * 64}")
    elif not args.no_visual and HAS_COM:
        if pairs:
            print(f"\n   Compared {len(pairs)} slide(s)")
            print(f"   Tip: Add --align to interactively fix differences")


if __name__ == "__main__":
    main()
