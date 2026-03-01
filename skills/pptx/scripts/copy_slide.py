"""Copy slides from one unpacked PPTX into another.

Usage: python copy_slide.py <source_dir> <slide1.xml> [slide2.xml ...] <dest_dir> [options]

Options:
  --copy-layout    Copy the source slide's layout and master into the destination
  --remap-layout   Map to the closest matching layout in the destination
  (no flag)        Prompt the user to choose

Examples:
    python copy_slide.py source/ slide3.xml dest/ --copy-layout
    python copy_slide.py source/ slide2.xml slide5.xml dest/ --remap-layout
    python copy_slide.py source/ slide1.xml dest/
"""

import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers – slide numbering & IDs (mirrored from add_slide.py)
# ---------------------------------------------------------------------------

def _get_next_slide_number(slides_dir: Path) -> int:
    existing = [int(m.group(1)) for f in slides_dir.glob("slide*.xml")
                if (m := re.match(r"slide(\d+)\.xml", f.name))]
    return max(existing) + 1 if existing else 1


def _get_next_slide_id(unpacked_dir: Path) -> int:
    """Get the next available slide ID, capping at the OOXML maximum (2147483647).

    If max(existing) + 1 would exceed the limit, searches for a gap in the
    used ID range starting from 256 (the minimum valid slide ID).
    """
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    pres_content = pres_path.read_text(encoding="utf-8")
    slide_ids = [int(m) for m in re.findall(r'<p:sldId[^>]*id="(\d+)"', pres_content)]
    if not slide_ids:
        return 256

    MAX_SLIDE_ID = 2147483647  # OOXML spec: must be < 2147483648
    candidate = max(slide_ids) + 1
    if candidate <= MAX_SLIDE_ID:
        return candidate

    # Max exceeded — find a gap starting from 256
    used = set(slide_ids)
    for i in range(256, MAX_SLIDE_ID + 1):
        if i not in used:
            return i

    raise ValueError("No available slide IDs — all 2B+ IDs are in use (this should never happen)")


def _get_next_rid(rels_path: Path) -> int:
    if not rels_path.exists():
        return 1
    content = rels_path.read_text(encoding="utf-8")
    rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', content)]
    return max(rids) + 1 if rids else 1


def _get_next_global_xml_id(unpacked_dir: Path, start: int = 2147483000) -> int:
    """Return a globally-unique numeric id= value across ppt XML files."""
    ids: set[int] = set()
    ppt_dir = unpacked_dir / "ppt"
    if not ppt_dir.exists():
        return start
    for xml in ppt_dir.rglob("*.xml"):
        try:
            content = xml.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in re.findall(r'\sid="(\d+)"', content):
            try:
                ids.add(int(m))
            except ValueError:
                pass
    candidate = start
    while candidate in ids:
        candidate += 1
    return candidate


# ---------------------------------------------------------------------------
# Content_Types & presentation.xml.rels helpers
# ---------------------------------------------------------------------------

def _add_to_content_types(unpacked_dir: Path, part_name: str, content_type: str) -> None:
    ct_path = unpacked_dir / "[Content_Types].xml"
    ct = ct_path.read_text(encoding="utf-8")
    if part_name in ct:
        return
    override = f'<Override PartName="{part_name}" ContentType="{content_type}"/>'
    ct = ct.replace("</Types>", f"  {override}\n</Types>")
    ct_path.write_text(ct, encoding="utf-8")


def _add_to_presentation_rels(unpacked_dir: Path, target: str, rel_type: str) -> str:
    pres_rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"
    pres_rels = pres_rels_path.read_text(encoding="utf-8")
    if target in pres_rels:
        # Already present – return existing rId
        m = re.search(rf'Id="(rId\d+)"[^>]*Target="{re.escape(target)}"', pres_rels)
        if m:
            return m.group(1)
    next_rid = _get_next_rid(pres_rels_path)
    rid = f"rId{next_rid}"
    new_rel = f'<Relationship Id="{rid}" Type="{rel_type}" Target="{target}"/>'
    pres_rels = pres_rels.replace("</Relationships>", f"  {new_rel}\n</Relationships>")
    pres_rels_path.write_text(pres_rels, encoding="utf-8")
    return rid


# ---------------------------------------------------------------------------
# Layout / master introspection
# ---------------------------------------------------------------------------

def _get_slide_layout_ref(slide_rels_path: Path) -> str | None:
    """Return the layout filename referenced by a slide's .rels (e.g. 'slideLayout3.xml')."""
    if not slide_rels_path.exists():
        return None
    content = slide_rels_path.read_text(encoding="utf-8")
    m = re.search(r'Target="\.\./slideLayouts/([^"]+)"', content)
    return m.group(1) if m else None


def _get_layout_master_ref(layout_rels_path: Path) -> str | None:
    """Return the master filename referenced by a layout's .rels."""
    if not layout_rels_path.exists():
        return None
    content = layout_rels_path.read_text(encoding="utf-8")
    m = re.search(r'Target="\.\./slideMasters/([^"]+)"', content)
    return m.group(1) if m else None


def _get_layout_name(layout_path: Path) -> str | None:
    """Extract the layout name from its XML (cSld name= or type= attribute)."""
    if not layout_path.exists():
        return None
    content = layout_path.read_text(encoding="utf-8")
    # Try type attribute first
    m = re.search(r'<p:cSld[^>]*name="([^"]*)"', content)
    if m:
        return m.group(1)
    # Try the type on the root element
    m = re.search(r'type="([^"]*)"', content)
    return m.group(1) if m else None


def _find_matching_layout(dest_dir: Path, layout_name: str | None) -> str | None:
    """Find a destination layout matching the given name. Returns filename or None."""
    layouts_dir = dest_dir / "ppt" / "slideLayouts"
    if not layouts_dir.exists() or not layout_name:
        return None
    for layout_file in sorted(layouts_dir.glob("slideLayout*.xml")):
        dest_name = _get_layout_name(layout_file)
        if dest_name and dest_name.lower() == layout_name.lower():
            return layout_file.name
    return None


def _get_first_layout(dest_dir: Path) -> str | None:
    """Return the first available layout in the destination."""
    layouts_dir = dest_dir / "ppt" / "slideLayouts"
    if not layouts_dir.exists():
        return None
    layouts = sorted(layouts_dir.glob("slideLayout*.xml"))
    return layouts[0].name if layouts else None


def _get_next_layout_number(dest_dir: Path) -> int:
    layouts_dir = dest_dir / "ppt" / "slideLayouts"
    existing = [int(m.group(1)) for f in layouts_dir.glob("slideLayout*.xml")
                if (m := re.match(r"slideLayout(\d+)\.xml", f.name))]
    return max(existing) + 1 if existing else 1


def _get_next_master_number(dest_dir: Path) -> int:
    masters_dir = dest_dir / "ppt" / "slideMasters"
    existing = [int(m.group(1)) for f in masters_dir.glob("slideMaster*.xml")
                if (m := re.match(r"slideMaster(\d+)\.xml", f.name))]
    return max(existing) + 1 if existing else 1


# ---------------------------------------------------------------------------
# Media / resource copying
# ---------------------------------------------------------------------------

def _copy_media_files(source_dir: Path, dest_dir: Path, rels_path: Path,
                      rels_content: str) -> str:
    """Copy media referenced by a rels file into the destination.

    Returns the updated rels_content with remapped Target paths where needed.
    """
    media_dirs = ["media", "embeddings", "charts", "diagrams", "drawings", "ink", "tags"]

    for m in re.finditer(r'Target="(\.\./([^/]+)/([^"]+))"', rels_content):
        full_target, dir_name, filename = m.group(1), m.group(2), m.group(3)
        if dir_name not in media_dirs:
            continue

        src_file = source_dir / "ppt" / dir_name / filename
        dest_media_dir = dest_dir / "ppt" / dir_name
        dest_file = dest_media_dir / filename

        if not src_file.exists():
            continue

        dest_media_dir.mkdir(parents=True, exist_ok=True)

        # Handle filename conflicts
        if dest_file.exists() and not _files_are_identical(src_file, dest_file):
            base, ext = _split_filename(filename)
            counter = 1
            while dest_file.exists():
                new_name = f"{base}_{counter}{ext}"
                dest_file = dest_media_dir / new_name
                counter += 1
            new_target = f"../{dir_name}/{dest_file.name}"
            rels_content = rels_content.replace(full_target, new_target)

        if not dest_file.exists():
            shutil.copy2(src_file, dest_file)

        # Add content type if needed
        ext = dest_file.suffix.lower()
        _ensure_extension_content_type(dest_dir, ext)

    return rels_content


def _files_are_identical(a: Path, b: Path) -> bool:
    return a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def _split_filename(filename: str) -> tuple[str, str]:
    dot = filename.rfind(".")
    if dot == -1:
        return filename, ""
    return filename[:dot], filename[dot:]


_CONTENT_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".emf": "image/x-emf",
    ".wmf": "image/x-wmf",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".bmp": "image/bmp",
    ".wdp": "image/vnd.ms-photo",
    ".jxr": "image/vnd.ms-photo",
    ".hdp": "image/vnd.ms-photo",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".wma": "audio/x-ms-wma",
    ".m4a": "audio/mp4",
    ".bin": "application/vnd.openxmlformats-officedocument.oleObject",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xml": "application/xml",
    ".fntdata": "application/x-fontdata",
}


def _ensure_extension_content_type(unpacked_dir: Path, ext: str) -> None:
    ct_path = unpacked_dir / "[Content_Types].xml"
    ct = ct_path.read_text(encoding="utf-8")
    ext_no_dot = ext.lstrip(".")
    if f'Extension="{ext_no_dot}"' in ct:
        return
    content_type = _CONTENT_TYPE_MAP.get(ext)
    if not content_type:
        print(f"  WARNING: No content type mapping for '{ext}' — add to _CONTENT_TYPE_MAP in copy_slide.py")
        return
    default = f'<Default Extension="{ext_no_dot}" ContentType="{content_type}"/>'
    ct = ct.replace("</Types>", f"  {default}\n</Types>")
    ct_path.write_text(ct, encoding="utf-8")


def _ensure_all_default_extensions(unpacked_dir: Path) -> None:
    """Scan all files in the destination and ensure Default extension entries
    exist in Content_Types.xml for every file type present in media/embeddings/tags."""
    ct_path = unpacked_dir / "[Content_Types].xml"
    ct = ct_path.read_text(encoding="utf-8")
    changed = False

    resource_dirs = ["media", "embeddings", "charts", "diagrams", "drawings", "ink", "tags"]
    extensions_found = set()

    for dir_name in resource_dirs:
        dir_path = unpacked_dir / "ppt" / dir_name
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if f.is_file():
                extensions_found.add(f.suffix.lower())

    for ext in sorted(extensions_found):
        ext_no_dot = ext.lstrip(".")
        if not ext_no_dot:
            continue
        if f'Extension="{ext_no_dot}"' in ct:
            continue
        content_type = _CONTENT_TYPE_MAP.get(ext)
        if not content_type:
            print(f"  WARNING: Unknown file extension '{ext_no_dot}' in {dir_name}/ — add to _CONTENT_TYPE_MAP")
            continue
        default = f'<Default Extension="{ext_no_dot}" ContentType="{content_type}"/>'
        ct = ct.replace("</Types>", f"  {default}\n</Types>")
        changed = True
        print(f"  Added Default extension: {ext_no_dot} → {content_type}")

    if changed:
        ct_path.write_text(ct, encoding="utf-8")


# ---------------------------------------------------------------------------
# Remap rIds in a .rels file to avoid conflicts with destination
# ---------------------------------------------------------------------------

def _remap_rels_rids(rels_content: str, slide_xml: str, start_rid: int) -> tuple[str, str]:
    """Remap all rIds in the rels content and corresponding slide XML.

    Uses a two-pass approach with temporary placeholders to avoid collisions
    when remapping (e.g., rId8→rId1 then rId1→rId8 would collide).

    Returns (updated_rels, updated_slide_xml).
    """
    old_rids = re.findall(r'Id="(rId\d+)"', rels_content)
    if not old_rids:
        return rels_content, slide_xml

    rid_map = {}
    next_rid = start_rid
    for old_rid in old_rids:
        new_rid = f"rId{next_rid}"
        rid_map[old_rid] = new_rid
        next_rid += 1

    # Pass 1: replace old rIds with unique temporary placeholders
    for old_rid in rid_map:
        placeholder = f"__TEMP__{old_rid}__"
        rels_content = rels_content.replace(f'"{old_rid}"', f'"{placeholder}"')
        slide_xml = slide_xml.replace(f'"{old_rid}"', f'"{placeholder}"')

    # Pass 2: replace placeholders with final rIds
    for old_rid, new_rid in rid_map.items():
        placeholder = f"__TEMP__{old_rid}__"
        rels_content = rels_content.replace(f'"{placeholder}"', f'"{new_rid}"')
        slide_xml = slide_xml.replace(f'"{placeholder}"', f'"{new_rid}"')

    return rels_content, slide_xml


# ---------------------------------------------------------------------------
# Layout strategies
# ---------------------------------------------------------------------------

def _get_theme_for_layout(unpacked_dir: Path, layout_name: str) -> str | None:
    """Trace layout → master → theme and return the theme filename."""
    layout_rels = unpacked_dir / "ppt" / "slideLayouts" / "_rels" / f"{layout_name}.rels"
    master = _get_layout_master_ref(layout_rels)
    if not master:
        return None
    master_rels = unpacked_dir / "ppt" / "slideMasters" / "_rels" / f"{master}.rels"
    if not master_rels.exists():
        return None
    content = master_rels.read_text(encoding="utf-8")
    m = re.search(r'Target="\.\./theme/([^"]+)"', content)
    return m.group(1) if m else None


def _get_theme_color_scheme(unpacked_dir: Path, theme_name: str) -> dict[str, str]:
    """Extract the color scheme from a theme file as {slot: hex_color}."""
    theme_path = unpacked_dir / "ppt" / "theme" / theme_name
    if not theme_path.exists():
        return {}
    content = theme_path.read_text(encoding="utf-8")
    colors = {}
    slots = ['dk1', 'dk2', 'lt1', 'lt2', 'accent1', 'accent2', 'accent3',
             'accent4', 'accent5', 'accent6', 'hlink', 'folHlink']
    for slot in slots:
        # Try srgbClr first
        m = re.search(rf'<a:{slot}>\s*<a:srgbClr val="([^"]+)"', content)
        if m:
            colors[slot] = m.group(1)
        else:
            # Try sysClr with lastClr
            m = re.search(rf'<a:{slot}>\s*<a:sysClr[^>]*lastClr="([^"]+)"', content)
            if m:
                colors[slot] = m.group(1)
    return colors


def _themes_match(colors_a: dict[str, str], colors_b: dict[str, str]) -> bool:
    """Return True if two theme color schemes are identical."""
    if not colors_a or not colors_b:
        return False
    for slot in ['accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6']:
        if colors_a.get(slot, '').upper() != colors_b.get(slot, '').upper():
            return False
    return True


def _handle_copy_layout(source_dir: Path, dest_dir: Path,
                        source_layout: str, rels_content: str) -> str:
    """Copy source layout (and master) into dest. Returns updated rels_content.

    If a layout with the same name exists in dest but uses a different theme
    color scheme, the source layout is copied as a NEW layout with its own
    master and theme to preserve the original colors.
    """
    src_layouts_dir = source_dir / "ppt" / "slideLayouts"
    src_layout_path = src_layouts_dir / source_layout

    # Check if destination already has a layout with the same name
    src_layout_name = _get_layout_name(src_layout_path)
    existing_match = _find_matching_layout(dest_dir, src_layout_name)
    if existing_match:
        # Check if the theme colors actually match
        src_theme = _get_theme_for_layout(source_dir, source_layout)
        dest_theme = _get_theme_for_layout(dest_dir, existing_match)
        src_colors = _get_theme_color_scheme(source_dir, src_theme) if src_theme else {}
        dest_colors = _get_theme_color_scheme(dest_dir, dest_theme) if dest_theme else {}

        if _themes_match(src_colors, dest_colors):
            print(f"  Layout '{src_layout_name}' exists in dest as {existing_match} (theme colors match)")
            return rels_content.replace(
                f"../slideLayouts/{source_layout}",
                f"../slideLayouts/{existing_match}"
            )
        else:
            print(f"  Layout '{src_layout_name}' exists as {existing_match} but theme colors DIFFER")
            print(f"    Source theme: {src_theme} — accent1={src_colors.get('accent1','?')}, accent2={src_colors.get('accent2','?')}")
            print(f"    Dest theme:   {dest_theme} — accent1={dest_colors.get('accent1','?')}, accent2={dest_colors.get('accent2','?')}")
            print(f"  → Copying as new layout to preserve source colors")

    # Copy the layout file
    dest_layouts_dir = dest_dir / "ppt" / "slideLayouts"
    dest_layouts_dir.mkdir(parents=True, exist_ok=True)
    next_layout_num = _get_next_layout_number(dest_dir)
    dest_layout_name = f"slideLayout{next_layout_num}.xml"
    dest_layout_path = dest_layouts_dir / dest_layout_name

    shutil.copy2(src_layout_path, dest_layout_path)
    print(f"  Copied layout {source_layout} → {dest_layout_name}")

    # Copy layout .rels
    src_layout_rels = src_layouts_dir / "_rels" / f"{source_layout}.rels"
    if src_layout_rels.exists():
        dest_layout_rels_dir = dest_layouts_dir / "_rels"
        dest_layout_rels_dir.mkdir(exist_ok=True)
        dest_layout_rels_path = dest_layout_rels_dir / f"{dest_layout_name}.rels"

        layout_rels = src_layout_rels.read_text(encoding="utf-8")

        # Handle the master reference
        src_master = _get_layout_master_ref(src_layout_rels)
        if src_master:
            dest_master = _copy_master_if_needed(source_dir, dest_dir, src_master,
                                                  dest_layout_name=dest_layout_name)
            if dest_master != src_master:
                layout_rels = layout_rels.replace(
                    f"../slideMasters/{src_master}",
                    f"../slideMasters/{dest_master}"
                )

        # Copy media referenced by the layout
        layout_rels = _copy_media_files(source_dir, dest_dir, src_layout_rels, layout_rels)

        dest_layout_rels_path.write_text(layout_rels, encoding="utf-8")

    # Add content type for the new layout
    _add_to_content_types(
        dest_dir,
        f"/ppt/slideLayouts/{dest_layout_name}",
        "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
    )

    # Update the slide rels to point to the new layout name
    rels_content = rels_content.replace(
        f"../slideLayouts/{source_layout}",
        f"../slideLayouts/{dest_layout_name}"
    )

    return rels_content


def _copy_master_if_needed(source_dir: Path, dest_dir: Path, src_master: str,
                          dest_layout_name: str | None = None) -> str:
    """Copy a slide master if its theme doesn't already exist in dest.

    Compares the source master's theme colors against all dest masters' themes.
    If a matching theme is found, reuses that dest master. Otherwise copies
    the master and its theme as new files.

    When copying a new master, its rels and sldLayoutIdLst are rewritten to
    only reference the specific dest_layout_name being copied (not all source layouts).

    Returns dest master filename.
    """
    src_masters_dir = source_dir / "ppt" / "slideMasters"
    dest_masters_dir = dest_dir / "ppt" / "slideMasters"

    # Get the source master's theme and colors
    src_master_rels = src_masters_dir / "_rels" / f"{src_master}.rels"
    src_theme_name = None
    if src_master_rels.exists():
        content = src_master_rels.read_text(encoding="utf-8")
        m = re.search(r'Target="\.\./theme/([^"]+)"', content)
        if m:
            src_theme_name = m.group(1)
    src_colors = _get_theme_color_scheme(source_dir, src_theme_name) if src_theme_name else {}

    # Check all dest masters for a theme color match
    if dest_masters_dir.exists():
        for dest_master_file in sorted(dest_masters_dir.glob("slideMaster*.xml")):
            dest_m_rels = dest_masters_dir / "_rels" / f"{dest_master_file.name}.rels"
            if dest_m_rels.exists():
                d_content = dest_m_rels.read_text(encoding="utf-8")
                d_theme_match = re.search(r'Target="\.\./theme/([^"]+)"', d_content)
                if d_theme_match:
                    dest_colors = _get_theme_color_scheme(dest_dir, d_theme_match.group(1))
                    if _themes_match(src_colors, dest_colors):
                        print(f"  Found matching theme in dest master {dest_master_file.name}")
                        return dest_master_file.name

    # No match found — copy the master and its theme
    dest_masters_dir.mkdir(parents=True, exist_ok=True)
    next_num = _get_next_master_number(dest_dir)
    dest_master_name = f"slideMaster{next_num}.xml"

    src_master_path = src_masters_dir / src_master
    dest_master_path = dest_masters_dir / dest_master_name

    shutil.copy2(src_master_path, dest_master_path)
    print(f"  Copied master {src_master} → {dest_master_name}")

    # Copy master .rels
    if src_master_rels.exists():
        dest_master_rels_dir = dest_masters_dir / "_rels"
        dest_master_rels_dir.mkdir(exist_ok=True)
        dest_master_rels_path = dest_master_rels_dir / f"{dest_master_name}.rels"

        master_rels = src_master_rels.read_text(encoding="utf-8")
        master_rels = _copy_media_files(source_dir, dest_dir, src_master_rels, master_rels)

        # Copy theme — always as a new file to avoid overwriting dest themes
        if src_theme_name:
            src_theme_path = source_dir / "ppt" / "theme" / src_theme_name
            if src_theme_path.exists():
                dest_theme_dir = dest_dir / "ppt" / "theme"
                dest_theme_dir.mkdir(parents=True, exist_ok=True)
                # Find next available theme number
                existing_themes = [int(m.group(1)) for f in dest_theme_dir.glob("theme*.xml")
                                   if (m := re.match(r"theme(\d+)\.xml", f.name))]
                next_theme_num = max(existing_themes) + 1 if existing_themes else 1
                dest_theme_name = f"theme{next_theme_num}.xml"
                dest_theme_path = dest_theme_dir / dest_theme_name
                shutil.copy2(src_theme_path, dest_theme_path)
                print(f"  Copied theme {src_theme_name} → {dest_theme_name}")
                master_rels = master_rels.replace(
                    f"../theme/{src_theme_name}",
                    f"../theme/{dest_theme_name}"
                )
                _add_to_content_types(
                    dest_dir,
                    f"/ppt/theme/{dest_theme_name}",
                    "application/vnd.openxmlformats-officedocument.theme+xml"
                )

        dest_master_rels_path.write_text(master_rels, encoding="utf-8")

    # Rewrite the master's rels to remove source layout references and only keep
    # non-layout relationships (theme, media, tags, embeddings) + the specific layout
    if dest_layout_name:
        master_rels_path = dest_masters_dir / "_rels" / f"{dest_master_name}.rels"
        if master_rels_path.exists():
            mr = master_rels_path.read_text(encoding="utf-8")
            # Extract all non-layout relationships
            non_layout_rels = re.findall(
                r'<Relationship[^>]*Target="(?!\.\./slideLayouts/)[^"]*"[^/]*/>', mr
            )
            # Build new rels with sequential rIds
            new_entries = []
            rid_remap = {}
            next_rid = 1
            # Add the specific layout first
            new_entries.append(
                f'<Relationship Id="rId{next_rid}" '
                f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                f'Target="../slideLayouts/{dest_layout_name}"/>'
            )
            layout_rid = f"rId{next_rid}"
            next_rid += 1
            # Add non-layout rels with remapped IDs
            for rel_xml in non_layout_rels:
                # Skip think-cell OLE/tag payload relationships when copying masters.
                if "relationships/oleObject" in rel_xml or "relationships/tags" in rel_xml:
                    continue
                old_rid = re.search(r'Id="(rId\d+)"', rel_xml).group(1)
                new_rid = f"rId{next_rid}"
                rid_remap[old_rid] = new_rid
                new_rel = re.sub(r'Id="rId\d+"', f'Id="{new_rid}"', rel_xml)
                new_entries.append(new_rel)
                next_rid += 1
            new_mr = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                + "\n".join(f"  {e}" for e in new_entries)
                + "\n</Relationships>"
            )
            master_rels_path.write_text(new_mr, encoding="utf-8")

            # Remap rIds in the master XML itself
            master_xml = dest_master_path.read_text(encoding="utf-8")
            # Remove think-cell hidden OLE data blocks; these frequently carry
            # duplicate cNvPr IDs and can trigger PowerPoint repair dialogs.
            master_xml, tc_removed = re.subn(
                r'<p:graphicFrame>[\s\S]*?think-cell Slide[\s\S]*?</p:graphicFrame>',
                "",
                master_xml,
                count=1,
                flags=re.IGNORECASE,
            )
            # Replace sldLayoutIdLst with single entry
            layout_id = _get_next_global_xml_id(dest_dir)
            master_xml = re.sub(
                r'<p:sldLayoutIdLst>.*?</p:sldLayoutIdLst>',
                f'<p:sldLayoutIdLst><p:sldLayoutId id="{layout_id}" r:id="{layout_rid}"/></p:sldLayoutIdLst>',
                master_xml,
                flags=re.DOTALL
            )
            # Remap rIds used in the master body (media, theme refs)
            for old_rid, new_rid in rid_remap.items():
                master_xml = master_xml.replace(f'"{old_rid}"', f'"__TMP_{old_rid}__"')
            for old_rid, new_rid in rid_remap.items():
                master_xml = master_xml.replace(f'"__TMP_{old_rid}__"', f'"{new_rid}"')
            dest_master_path.write_text(master_xml, encoding="utf-8")
            print(f"  Cleaned master rels: {len(new_entries)} relationships (was {mr.count('<Relationship')})")
            if tc_removed:
                print("  Removed think-cell OLE payload from copied master")

    _add_to_content_types(
        dest_dir,
        f"/ppt/slideMasters/{dest_master_name}",
        "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"
    )

    # Add master to presentation.xml.rels
    _add_to_presentation_rels(
        dest_dir,
        f"slideMasters/{dest_master_name}",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster"
    )

    # Add master to sldMasterIdLst in presentation.xml
    pres_path = dest_dir / "ppt" / "presentation.xml"
    pres_content = pres_path.read_text(encoding="utf-8")
    master_ids = [int(m) for m in re.findall(r'<p:sldMasterId[^>]*id="(\d+)"', pres_content)]
    next_master_id = max(master_ids) + 1 if master_ids else 2147483648
    # Get the rId we just added
    pres_rels_path = dest_dir / "ppt" / "_rels" / "presentation.xml.rels"
    pres_rels = pres_rels_path.read_text(encoding="utf-8")
    m = re.search(rf'Id="(rId\d+)"[^>]*Target="slideMasters/{re.escape(dest_master_name)}"', pres_rels)
    if m:
        master_rid = m.group(1)
        new_master_entry = f'<p:sldMasterId id="{next_master_id}" r:id="{master_rid}"/>'
        pres_content = pres_content.replace(
            "</p:sldMasterIdLst>",
            f"  {new_master_entry}\n  </p:sldMasterIdLst>"
        )
        pres_path.write_text(pres_content, encoding="utf-8")
        print(f"  Added master to sldMasterIdLst: id={next_master_id}, r:id={master_rid}")

    return dest_master_name


def _handle_remap_layout(source_dir: Path, dest_dir: Path,
                         source_layout: str, rels_content: str) -> str:
    """Map to a matching layout in the destination. Returns updated rels_content."""
    src_layout_path = source_dir / "ppt" / "slideLayouts" / source_layout
    src_layout_name = _get_layout_name(src_layout_path)

    # Try to find a matching layout by name
    match = _find_matching_layout(dest_dir, src_layout_name)
    if match:
        print(f"  Remapped layout '{src_layout_name}' → {match}")
    else:
        match = _get_first_layout(dest_dir)
        if match:
            print(f"  WARNING: No matching layout for '{src_layout_name}', using {match}")
        else:
            print("  ERROR: No layouts found in destination", file=sys.stderr)
            sys.exit(1)

    rels_content = rels_content.replace(
        f"../slideLayouts/{source_layout}",
        f"../slideLayouts/{match}"
    )
    return rels_content


# ---------------------------------------------------------------------------
# Notes slide copying
# ---------------------------------------------------------------------------

def _get_next_notes_number(dest_dir: Path) -> int:
    notes_dir = dest_dir / "ppt" / "notesSlides"
    if not notes_dir.exists():
        return 1
    existing = [int(m.group(1)) for f in notes_dir.glob("notesSlide*.xml")
                if (m := re.match(r"notesSlide(\d+)\.xml", f.name))]
    return max(existing) + 1 if existing else 1


def _copy_notes_slide(source_dir: Path, dest_dir: Path, src_notes_name: str,
                      dest_slide_name: str, rels_content: str) -> str:
    """Copy a notes slide from source to dest, updating its slide reference.

    Returns updated rels_content with the new notes target.
    """
    src_notes_path = source_dir / "ppt" / "notesSlides" / src_notes_name
    if not src_notes_path.exists():
        # Notes file missing — strip the reference
        rels_content = re.sub(
            r'\s*<Relationship[^>]*Type="[^"]*notesSlide"[^>]*/>\s*',
            "\n", rels_content)
        return rels_content

    dest_notes_dir = dest_dir / "ppt" / "notesSlides"
    dest_notes_dir.mkdir(parents=True, exist_ok=True)

    next_num = _get_next_notes_number(dest_dir)
    dest_notes_name = f"notesSlide{next_num}.xml"
    dest_notes_path = dest_notes_dir / dest_notes_name

    # Read and update the notes XML — change the slide reference to point
    # to the new destination slide
    notes_xml = src_notes_path.read_text(encoding="utf-8")
    dest_notes_path.write_text(notes_xml, encoding="utf-8")

    # Copy notes .rels, updating the slide target
    src_notes_rels = source_dir / "ppt" / "notesSlides" / "_rels" / f"{src_notes_name}.rels"
    dest_notes_rels_dir = dest_notes_dir / "_rels"
    dest_notes_rels_dir.mkdir(exist_ok=True)
    dest_notes_rels_path = dest_notes_rels_dir / f"{dest_notes_name}.rels"

    if src_notes_rels.exists():
        notes_rels = src_notes_rels.read_text(encoding="utf-8")
        # Update the slide reference to point to the new dest slide
        notes_rels = re.sub(
            r'Target="\.\./slides/[^"]+"',
            f'Target="../slides/{dest_slide_name}"',
            notes_rels
        )
        # Copy any media referenced by the notes
        notes_rels = _copy_media_files(source_dir, dest_dir, src_notes_rels, notes_rels)
        dest_notes_rels_path.write_text(notes_rels, encoding="utf-8")
    else:
        # Create minimal rels pointing to the slide and notesMaster
        # Find a notesMaster in the destination
        notes_master_ref = ""
        masters_dir = dest_dir / "ppt" / "notesMasters"
        if masters_dir.exists():
            masters = sorted(masters_dir.glob("notesMaster*.xml"))
            if masters:
                notes_master_ref = f'\n  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="../notesMasters/{masters[0].name}"/>'
        notes_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="../slides/{dest_slide_name}"/>{notes_master_ref}
</Relationships>'''
        dest_notes_rels_path.write_text(notes_rels, encoding="utf-8")

    # Add content type for the notes slide
    _add_to_content_types(
        dest_dir,
        f"/ppt/notesSlides/{dest_notes_name}",
        "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"
    )

    # Update the slide's rels to point to the new notes file
    rels_content = rels_content.replace(
        f"../notesSlides/{src_notes_name}",
        f"../notesSlides/{dest_notes_name}"
    )

    print(f"  Copied notes {src_notes_name} → {dest_notes_name}")
    return rels_content


# ---------------------------------------------------------------------------
# Main copy logic
# ---------------------------------------------------------------------------

def copy_slide(source_dir: Path, slide_name: str, dest_dir: Path,
               layout_strategy: str, force_slide_id: int | None = None) -> tuple[str, int]:
    """Copy a single slide. Returns (dest_slide_filename, slide_id_used)."""
    src_slides_dir = source_dir / "ppt" / "slides"
    src_slide_path = src_slides_dir / slide_name
    src_rels_dir = src_slides_dir / "_rels"
    src_rels_path = src_rels_dir / f"{slide_name}.rels"

    dest_slides_dir = dest_dir / "ppt" / "slides"
    dest_rels_dir = dest_slides_dir / "_rels"

    if not src_slide_path.exists():
        print(f"Error: {src_slide_path} not found", file=sys.stderr)
        sys.exit(1)

    # Determine destination slide number
    next_num = _get_next_slide_number(dest_slides_dir)
    dest_slide_name = f"slide{next_num}.xml"
    dest_slide_path = dest_slides_dir / dest_slide_name

    print(f"\nCopying {slide_name} → {dest_slide_name}")

    # Read source slide XML
    slide_xml = src_slide_path.read_text(encoding="utf-8")

    # Handle relationships
    if src_rels_path.exists():
        rels_content = src_rels_path.read_text(encoding="utf-8")

        # Copy notes slide if present
        notes_match = re.search(
            r'Target="\.\./notesSlides/([^"]+)"', rels_content
        )
        if notes_match:
            rels_content = _copy_notes_slide(
                source_dir, dest_dir, notes_match.group(1),
                dest_slide_name, rels_content
            )

        # Get source layout reference before remapping
        source_layout = _get_slide_layout_ref(src_rels_path)

        # Copy media files and remap targets if needed
        rels_content = _copy_media_files(source_dir, dest_dir, src_rels_path, rels_content)

        # Handle layout strategy
        if source_layout:
            if layout_strategy == "copy":
                rels_content = _handle_copy_layout(
                    source_dir, dest_dir, source_layout, rels_content
                )
            else:  # remap
                rels_content = _handle_remap_layout(
                    source_dir, dest_dir, source_layout, rels_content
                )

        # Remap rIds — since this is a new rels file, start from 1
        rels_content, slide_xml = _remap_rels_rids(rels_content, slide_xml, 1)

        # Write the rels file
        dest_rels_dir.mkdir(exist_ok=True)
        dest_rels_path = dest_rels_dir / f"{dest_slide_name}.rels"
        dest_rels_path.write_text(rels_content, encoding="utf-8")
    else:
        print("  No relationships file found for source slide")

    # Write the slide XML
    dest_slide_path.write_text(slide_xml, encoding="utf-8")

    # Add to Content_Types.xml
    _add_to_content_types(
        dest_dir,
        f"/ppt/slides/{dest_slide_name}",
        "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
    )

    # Add to presentation.xml.rels
    rid = _add_to_presentation_rels(
        dest_dir,
        f"slides/{dest_slide_name}",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
    )

    # Get next slide ID
    next_slide_id = force_slide_id if force_slide_id is not None else _get_next_slide_id(dest_dir)

    print(f'  Add to presentation.xml <p:sldIdLst>: <p:sldId id="{next_slide_id}" r:id="{rid}"/>')

    return dest_slide_name, next_slide_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _prompt_layout_strategy() -> str:
    print("\nLayout strategy:")
    print("  1. Copy layout and master from source (preserves exact look)")
    print("  2. Remap to closest matching layout in destination (simpler)")
    while True:
        choice = input("Choose [1/2]: ").strip()
        if choice == "1":
            return "copy"
        if choice == "2":
            return "remap"
        print("  Please enter 1 or 2")


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]

    # Parse flags
    layout_strategy = None
    if "--copy-layout" in args:
        layout_strategy = "copy"
        args.remove("--copy-layout")
    elif "--remap-layout" in args:
        layout_strategy = "remap"
        args.remove("--remap-layout")

    if len(args) < 3:
        print("Error: Need source_dir, at least one slide, and dest_dir", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    source_dir = Path(args[0])
    dest_dir = Path(args[-1])
    slide_names = args[1:-1]

    # Validate
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} not found", file=sys.stderr)
        sys.exit(1)
    if not dest_dir.exists():
        print(f"Error: Destination directory {dest_dir} not found", file=sys.stderr)
        sys.exit(1)

    # Prompt if no strategy specified
    if layout_strategy is None:
        layout_strategy = _prompt_layout_strategy()

    print(f"Layout strategy: {layout_strategy}")
    print(f"Source: {source_dir}")
    print(f"Destination: {dest_dir}")
    print(f"Slides to copy: {', '.join(slide_names)}")

    next_slide_id = _get_next_slide_id(dest_dir)
    for slide_name in slide_names:
        _, used_id = copy_slide(source_dir, slide_name, dest_dir, layout_strategy,
                                force_slide_id=next_slide_id)
        next_slide_id = used_id + 1

    # Ensure Default extension entries exist for all file types used in the dest
    _ensure_all_default_extensions(dest_dir)

    print("\nDone! Next steps:")
    print("  1. Add the <p:sldId> elements shown above to presentation.xml <p:sldIdLst>")
    print(f"  2. Run: python scripts/clean.py {dest_dir}")
    print(f"  3. Run: python scripts/office/pack.py {dest_dir} output.pptx --original dest.pptx")


if __name__ == "__main__":
    main()
