# Editing Presentations

## Template-Based Workflow

When using an existing presentation as a template:

1. **Analyze existing slides**:
   ```bash
   python scripts/thumbnail.py template.pptx
   python -m markitdown template.pptx
   ```
   Review `thumbnails.jpg` to see layouts, and markitdown output to see placeholder text.

2. **Plan slide mapping**: For each content section, choose a template slide.

   ⚠️ **USE VARIED LAYOUTS** — monotonous presentations are a common failure mode. Don't default to basic title + bullet slides. Actively seek out:
   - Multi-column layouts (2-column, 3-column)
   - Image + text combinations
   - Full-bleed images with text overlay
   - Quote or callout slides
   - Section dividers
   - Stat/number callouts
   - Icon grids or icon + text rows

   **Avoid:** Repeating the same text-heavy layout for every slide.

   Match content type to layout style (e.g., key points → bullet slide, team info → multi-column, testimonials → quote slide).

3. **Unpack**: `python scripts/office/unpack.py template.pptx unpacked/`

4. **Build presentation** (do this yourself, not with subagents):
   - Delete unwanted slides (remove from `<p:sldIdLst>`)
   - Duplicate slides you want to reuse (`add_slide.py`)
   - Reorder slides in `<p:sldIdLst>`
   - **Complete all structural changes before step 5**

5. **Edit content**: Update text in each `slide{N}.xml`.
   **Use subagents here if available** — slides are separate XML files, so subagents can edit in parallel.

6. **Clean**: `python scripts/clean.py unpacked/`

7. **Pack**: `python scripts/office/pack.py unpacked/ output.pptx --original template.pptx`

---

## Scripts

| Script | Purpose |
|--------|---------|
| `unpack.py` | Extract and pretty-print PPTX |
| `add_slide.py` | Duplicate slide or create from layout |
| `copy_slide.py` | Copy slides between different presentations |
| `compare_slides.py` | Visual comparison + interactive alignment |
| `clean.py` | Remove orphaned files |
| `pack.py` | Repack with validation |
| `thumbnail.py` | Create visual grid of slides |

### unpack.py

```bash
python scripts/office/unpack.py input.pptx unpacked/
```

Extracts PPTX, pretty-prints XML, escapes smart quotes.

### add_slide.py

```bash
python scripts/add_slide.py unpacked/ slide2.xml      # Duplicate slide
python scripts/add_slide.py unpacked/ slideLayout2.xml # From layout
```

Prints `<p:sldId>` to add to `<p:sldIdLst>` at desired position.

### clean.py

```bash
python scripts/clean.py unpacked/
```

Removes slides not in `<p:sldIdLst>`, unreferenced media, orphaned rels.

### pack.py

```bash
python scripts/office/pack.py unpacked/ output.pptx --original input.pptx
```

Validates, repairs, condenses XML, re-encodes smart quotes.

### thumbnail.py

```bash
python scripts/thumbnail.py input.pptx [output_prefix] [--cols N]
```

Creates `thumbnails.jpg` with slide filenames as labels. Default 3 columns, max 12 per grid.

**Use for template analysis only** (choosing layouts). For visual QA, use `soffice` + `pdftoppm` to create full-resolution individual slide images—see SKILL.md.

### copy_slide.py

```bash
python scripts/copy_slide.py <source_dir> <slide1.xml> [slide2.xml ...] <dest_dir> [options]
```

Copies slides from one unpacked PPTX into another. Handles media, videos, OLE objects, tags, hyperlinks, speaker notes, and slide layout resolution.

**Options:**
- `--copy-layout` — Copy the source layout/master into the destination (preserves exact look). Auto-detects theme color mismatches and creates new layout+master+theme when needed.
- `--remap-layout` — Map to the closest matching layout in the destination (simpler, uses dest theme colors)
- *(no flag)* — Prompts interactively

**Automatic protections:**
- Compares theme color schemes when layout names match to prevent wrong-color slides
- Strips think-cell OLE payloads from copied masters (prevents duplicate ID corruption)
- Rewrites copied master's rels and `sldLayoutIdLst` to only reference the specific layout being copied (prevents dangling layout references that cause PowerPoint hangs)
- Caps slide IDs at OOXML maximum (2147483647) with gap-filling fallback
- Warns on unknown media file extensions (`.wdp`, `.webp`, etc. are included)
- Generates globally-unique XML IDs by scanning all existing IDs in the destination

Prints `<p:sldId>` elements to add to `presentation.xml`.

### clean.py

```bash
python scripts/clean.py unpacked/
```

Removes slides not in `<p:sldIdLst>`, unreferenced media, orphaned rels, and stale `Content_Types.xml` overrides.

**Key behaviors:**
- Always strips `<Override>` entries for files that don't exist (fixes repair prompts)
- Reports orphaned media referenced only by layouts/masters (cosmetic repair prompt warning)
- Removes orphaned `.rels` files for deleted slides and notes

---

## Slide Operations

Slide order is in `ppt/presentation.xml` → `<p:sldIdLst>`.

**Reorder**: Rearrange `<p:sldId>` elements.

**Delete**: Remove `<p:sldId>`, then run `clean.py`.

**Add**: Use `add_slide.py`. Never manually copy slide files—the script handles notes references, Content_Types.xml, and relationship IDs that manual copying misses.

---

## Cross-File Slide Copying

Copy slides from one presentation into another while preserving all content.

### What Gets Copied

- Slide XML (all shapes, text, animations)
- Speaker notes
- Media (images, videos, EMF, SVG)
- OLE embedded objects
- Tags
- Hyperlinks (external targets preserved as-is)
- Slide layout reference (matched or copied per strategy)

### Workflow

1. **Unpack both files**:
   ```bash
   python scripts/office/unpack.py source.pptx source_unpacked/
   python scripts/office/unpack.py dest.pptx dest_unpacked/
   ```

2. **Identify which slide files to copy**. Slide order is in `ppt/presentation.xml` → `<p:sldIdLst>`. The Nth `<p:sldId>` entry is slide N. Map its `r:id` to a filename via `ppt/_rels/presentation.xml.rels`.

3. **Copy slides**:
   ```bash
   python scripts/copy_slide.py source_unpacked/ slide24.xml dest_unpacked/ --copy-layout
   # Or multiple slides at once:
   python scripts/copy_slide.py source_unpacked/ slide24.xml slide25.xml dest_unpacked/ --remap-layout
   ```

4. **Add `<p:sldId>` entries** printed by the script to `ppt/presentation.xml` → `<p:sldIdLst>` at the desired position.

5. **Clean and pack** (to a local temp path for validation):
   ```bash
   python scripts/clean.py dest_unpacked/
   python scripts/office/pack.py dest_unpacked/ C:\Temp\output-staging.pptx --original dest.pptx
   ```

6. **User validates** the staging file in PowerPoint (repair if prompted, check visuals), then copy to final location.

### Layout Strategies

| Strategy | Flag | When to Use |
|----------|------|-------------|
| **Copy layout** | `--copy-layout` | Source and dest use different templates. Preserves exact appearance. If a layout with the same name already exists in dest, reuses it (but warns if the master/theme differs). |
| **Remap layout** | `--remap-layout` | Source and dest share the same template (or you want dest theme colors). Maps to the closest matching layout by name. Falls back to first available layout if no match. |
| **Interactive** | *(no flag)* | Prompts you to choose. |

**Theme/color considerations:**
- `--copy-layout` compares the source and destination theme color schemes automatically. If colors match, it reuses the existing destination layout. If colors differ, it creates a **new layout + master + theme** in the destination to preserve the source's exact colors.
- `--remap-layout` always uses the destination's theme/colors. Use this when you want copied slides to match the destination deck's visual identity.
- **Rule of thumb:** Use `--remap-layout` first as it will result in slide slide repair errors. After bringing over one or two slides, do a visual compare using image files to see if there is a differnce.  If there is highlight the differences to the user and let them determine if we want to start using the template files from the source or stick with the destination. 
**When to use Copy layout vs remap layout** Use `--copy-layout` when bringing in slides from a different deck and you want them to look exactly like the source. Use `--remap-layout` when both decks share similar branding.

### Hardcoded Colors After Cross-Deck Copy

When copying slides with `--copy-layout`, the theme colors resolve correctly, but many slides also contain **hardcoded `srgbClr` values** baked into shape fills, outlines, and custom geometry. These won't change when the layout/theme changes — the slide will look "off" compared to slides that use the destination's color palette.

**How to diagnose:** Compare hardcoded colors between the copied slide and a reference slide:
```python
import re
from collections import Counter
content = open('ppt/slides/slideN.xml', 'r').read()
srgb = re.findall(r'<a:srgbClr val="([A-Fa-f0-9]{6})"', content)
print(Counter(srgb).most_common(10))
```

Common color mappings to watch for:
| Source Color | Typical Use | Likely Destination Equivalent |
|---|---|---|
| Dark navy (`091F2C`, `1B2A4A`) | Shape fills, backgrounds | `000000` (black) or dest theme's `dk1` |
| Red (`FF0000`, `E74856`) | Accent arrows, connectors | `0078D4` (MS blue) or dest theme's `accent1` |
| Gold (`FFB900`) | Highlights | Check dest theme's `accent2` |

**When to expect this:** Any time `--copy-layout` reports "theme colors DIFFER → Copying as new layout." The layout/master/theme will be correct, but hardcoded colors in the slide XML itself won't change.

### Batch Copy — sldId Overlap

When running `copy_slide.py` multiple times against the same destination (e.g., once for v25.12 slides, once for FY26 Pitch slides), the second run will assign **overlapping `sldId` values** because the first batch's IDs weren't committed to `presentation.xml` yet.

**Fix:** When adding `<p:sldId>` entries to `presentation.xml`, manually assign unique IDs to the second batch. Continue from `max(all_assigned_ids) + 1`:
```xml
<!-- First batch (from copy_slide output): ids 2147482928–2147482931 -->
<!-- Second batch: manually use 2147482932–2147482933 instead of the script's output -->
```

---

## Visual Comparison & Alignment

Compare slides between two PPTX files visually and structurally, then interactively align a target slide to match a source.

### compare_slides.py

```bash
python scripts/compare_slides.py <file_a> <file_b> [options]
```

**Modes:**

| Mode | Flag | What It Does |
|------|------|-------------|
| **Compare** | *(default)* | Exports slides via PowerPoint COM, generates HTML side-by-side report with pixel diff overlay |
| **Align** | `--align` | Compare + structural analysis + interactive alignment (approve/modify/skip each change) |

**Slide selection:**

```bash
# Compare all slides (matching slide numbers)
python scripts/compare_slides.py a.pptx b.pptx

# Specific slides
python scripts/compare_slides.py a.pptx b.pptx --slides 5,8,12

# Slide range
python scripts/compare_slides.py a.pptx b.pptx --slides 5:10

# Cross-map different slide numbers (A's slide 8 vs B's slide 19)
python scripts/compare_slides.py a.pptx b.pptx --map 8:19,14:20
```

**Other options:**

| Flag | Default | Purpose |
|------|---------|---------|
| `--out` | `%TEMP%\compare_slides_output.html` | HTML report path |
| `--width` | 1920 | Export width in pixels |
| `--no-diff` | off | Skip pixel-diff overlay (faster) |
| `--no-visual` | off | Skip PowerPoint COM export (structural only) |

### Alignment Workflow

When using `--align`:

1. **Visual comparison** runs first — HTML report opens in browser
2. **Source selection** — you choose which file is the source of truth (A or B)
3. **Structural analysis** — python-pptx extracts shapes, text, colors, positions, fonts, images
4. **Interactive review** — each difference is presented with:
   - Category (color, text, position, size, font, fill, image)
   - Source vs target values
   - Confidence level (HIGH / MEDIUM / LOW)
   - Proposed action
5. **User decision** for each diff:
   - `[A]pprove` — apply this change
   - `[M]odify` — edit the proposed value before applying
   - `[S]kip` — leave as-is
   - `[AA]` — approve all remaining (skips LOW confidence)
   - `[Q]uit` — stop, apply only what's been approved so far
6. **Execution** — approved changes applied to a **duplicate** of the target slide via unpack → XML edit → clean → pack
7. **Review-friendly output** — staging file where:
   - The **original slide is hidden** (preserved for comparison)
   - The **aligned version is inserted right after it**
   - Open in PowerPoint → unhide original → compare side-by-side → delete whichever you don't want

### What Gets Compared

| Category | Confidence | How It's Fixed |
|----------|-----------|---------------|
| Theme colors (schemeClr) | HIGH | Replace scheme refs with hardcoded source hex |
| Theme fonts (+mj-lt/+mn-lt) | HIGH | Replace theme font refs with explicit typeface |
| Inherited fonts (no typeface) | HIGH | Inject explicit font into runs inheriting from theme |
| Text auto-size (shrink-to-fit) | HIGH | Set spAutoFit/normAutofit in bodyPr |
| Text margins | HIGH | Update lIns/rIns/tIns/bIns in bodyPr |
| Hardcoded colors (srgbClr) | MEDIUM | Find/replace in slide XML |
| Text content | HIGH | Replace `<a:t>` element content |
| Shape position | MEDIUM | Update `<a:off>` x/y attributes |
| Shape size | MEDIUM | Update `<a:ext>` cx/cy attributes |
| Font name | MEDIUM | Flagged for review |
| Font color | HIGH | Color value replacement |
| Fill color | HIGH | Color value replacement |
| Images | LOW | Flagged for manual replacement |
| Missing shapes | LOW | Flagged — needs manual intervention |
| Extra shapes | LOW | Flagged — needs manual intervention |

### Dependencies

- `pywin32` — PowerPoint COM for visual export
- `Pillow` — pixel diff overlay
- `python-pptx` — structural analysis

---

### Known Issues & Workarounds

#### Repair Prompt on Open (Cosmetic)
Large corporate template decks often contain dozens of layouts and masters with media files (images, EMFs) that aren't referenced by any visible slide. When slides are deleted or copied between such decks, PowerPoint may detect these orphaned media files and show a "repair" prompt. **This is cosmetic — no data loss occurs.** The `clean.py` script reports these orphaned media files so you know to expect the prompt.

**Recommended workflow for corporate decks:**
You should only follow this process IF the `--copy-layout` was used or the final destination is Sharepoint/OneDrive.  If you created slides from scratch or used the destination template, create the new presentation right in the working folder.
1. **Use a local temp directory for all build operations** (e.g., `C:\Temp\build_name\`). Unpack, copy, edit, clean, and pack all happen here — not on OneDrive/SharePoint paths. This avoids sync locks and dramatically improves I/O speed for large files.
2. Build the deck using the normal unpack → copy → clean → pack pipeline
3. **Pack to a local temp path** (e.g., `C:\Temp\output-staging.pptx`) — NOT the final OneDrive/SharePoint location. OneDrive sync dramatically slows PowerPoint's repair process on large files.
   ```bash
   python scripts/office/pack.py C:\Temp\build\dest_unpacked\ C:\Temp\output-staging.pptx --original source.pptx
   ```
4. **Ask the user to open and validate** the staging file in PowerPoint. If it asks to repair, allow it and save the repaired file. Provide the staging path and a summary of changes so the user knows what to check.
5. Once the user confirms the file looks good, **copy the validated file to its final location**:
   ```powershell
   Copy-Item "C:\Temp\output-staging.pptx" "final\destination\output.pptx"
   Remove-Item "C:\Temp\output-staging.pptx"
   ```
6. **Clean up the build directory:**
   ```powershell
   Remove-Item "C:\Temp\build_name\" -Recurse -Force
   ```
7. Use the **repaired/validated file** as your baseline for any further python-pptx modifications (notes, markers, etc.)
8. The repaired file will open cleanly going forward

#### Think-cell OLE Objects
Decks that use think-cell (a popular charting add-in) embed hidden OLE objects in slide masters with duplicate `cNvPr` IDs. The `copy_slide.py` script automatically strips these when copying masters to prevent PowerPoint corruption. If you see think-cell-related shapes in copied masters, they are safe to remove.

#### Slide ID Overflow
OOXML requires slide IDs to be < 2147483648. The `copy_slide.py` script automatically detects when `max(existing_ids) + 1` would overflow and searches for gaps in the used ID range instead.

#### Pre-existing ID Collisions in Base Decks
Some corporate decks have pre-existing `sldLayoutId` values in masters that collide with `sldMasterId` values in `presentation.xml`. The `pack.py` validator will flag these. Fix by scanning all XML files for used IDs and replacing the conflicting value with an unused one.

#### Adding `<p:sldId>` Entries with PowerShell
When using PowerShell to modify `presentation.xml`, **do not use backtick-n** for newlines in string replacements — it inserts literal text, not a newline. Use Python for XML modifications instead.

### Important Notes

- The script handles rId remapping automatically (avoids collisions between source and dest relationship IDs).
- Media filename conflicts are resolved by appending `_1`, `_2`, etc.
- Missing `Default Extension` entries in Content_Types.xml are added automatically for all file types present in the destination.

---

## Editing Content

**Subagents:** If available, use them here (after completing step 4). Each slide is a separate XML file, so subagents can edit in parallel. In your prompt to subagents, include:
- The slide file path(s) to edit
- **"Use the Edit tool for all changes"**
- The formatting rules and common pitfalls below

For each slide:
1. Read the slide's XML
2. Identify ALL placeholder content—text, images, charts, icons, captions
3. Replace each placeholder with final content

**Use the Edit tool, not sed or Python scripts.** The Edit tool forces specificity about what to replace and where, yielding better reliability.

### Formatting Rules

- **Bold all headers, subheadings, and inline labels**: Use `b="1"` on `<a:rPr>`. This includes:
  - Slide titles
  - Section headers within a slide
  - Inline labels like (e.g.: "Status:", "Description:") at the start of a line
- **Never use unicode bullets (•)**: Use proper list formatting with `<a:buChar>` or `<a:buAutoNum>`
- **Bullet consistency**: Let bullets inherit from the layout. Only specify `<a:buChar>` or `<a:buNone>`.

---

## Common Pitfalls

### Template Adaptation

When source content has fewer items than the template:
- **Remove excess elements entirely** (images, shapes, text boxes), don't just clear text
- Check for orphaned visuals after clearing text content
- Run visual QA to catch mismatched counts

When replacing text with different length content:
- **Shorter replacements**: Usually safe
- **Longer replacements**: May overflow or wrap unexpectedly
- Test with visual QA after text changes
- Consider truncating or splitting content to fit the template's design constraints

**Template slots ≠ Source items**: If template has 4 team members but source has 3 users, delete the 4th member's entire group (image + text boxes), not just the text.

### Multi-Item Content

If source has multiple items (numbered lists, multiple sections), create separate `<a:p>` elements for each — **never concatenate into one string**.

**❌ WRONG** — all items in one paragraph:
```xml
<a:p>
  <a:r><a:rPr .../><a:t>Step 1: Do the first thing. Step 2: Do the second thing.</a:t></a:r>
</a:p>
```

**✅ CORRECT** — separate paragraphs with bold headers:
```xml
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 1</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" .../><a:t>Do the first thing.</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 2</a:t></a:r>
</a:p>
<!-- continue pattern -->
```

Copy `<a:pPr>` from the original paragraph to preserve line spacing. Use `b="1"` on headers.

### Smart Quotes

Handled automatically by unpack/pack. But the Edit tool converts smart quotes to ASCII.

**When adding new text with quotes, use XML entities:**

```xml
<a:t>the &#x201C;Agreement&#x201D;</a:t>
```

| Character | Name | Unicode | XML Entity |
|-----------|------|---------|------------|
| `“` | Left double quote | U+201C | `&#x201C;` |
| `”` | Right double quote | U+201D | `&#x201D;` |
| `‘` | Left single quote | U+2018 | `&#x2018;` |
| `’` | Right single quote | U+2019 | `&#x2019;` |

### Other

- **Whitespace**: Use `xml:space="preserve"` on `<a:t>` with leading/trailing spaces
- **XML parsing**: Use `defusedxml.minidom`, not `xml.etree.ElementTree` (corrupts namespaces)
- **Media orphans & repair prompts**: When working with decks that have many layouts/masters (common in corporate templates), PowerPoint may show a "repair" prompt on open due to media files referenced by layouts/masters but not by any visible slide. This is **cosmetic — no data loss occurs**. The `clean.py` script reports these orphaned media files so you know to expect the prompt. If a hang occurs during repair, the issue is likely dangling master→layout references, not orphaned media.
