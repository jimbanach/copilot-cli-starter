---
name: pptx
description: "Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; copying slides between different presentations; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill."
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | Read [editing.md](editing.md) |
| Copy slides between files | Read [editing.md](editing.md#cross-file-slide-copying) |
| Compare & align slides | Read [editing.md](editing.md#visual-comparison--alignment) |
| Create from scratch | Read [pptxgenjs.md](pptxgenjs.md) |

---

## Reading Content

```bash
# Text extraction
python -m markitdown presentation.pptx

# Visual overview
python scripts/thumbnail.py presentation.pptx

# Raw XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Visual Comparison & Alignment

**Read [editing.md](editing.md#visual-comparison--alignment) for full details.**

Compare slides between two presentations visually (PowerPoint COM rendering) and structurally (python-pptx XML analysis). Optionally run interactive alignment to fix color, text, position, and size differences.

```bash
# Visual comparison — opens HTML report in browser
python scripts/compare_slides.py deck_a.pptx deck_b.pptx --map 8:19

# Interactive alignment — compare, analyze, then approve/modify/skip each fix
python scripts/compare_slides.py deck_a.pptx deck_b.pptx --map 8:19 --align
```

---

## Cross-File Slide Copying

**Read [editing.md](editing.md#cross-file-slide-copying) for full details.**

Copy slides between two different presentations while preserving media, videos, speaker notes, hyperlinks, and animations. Automatically handles theme color mismatches, think-cell artifacts, and ID overflow.

```bash
# Use a local temp dir for all build operations (not OneDrive)
python scripts/office/unpack.py source.pptx C:\Temp\build\source_unpacked\
python scripts/office/unpack.py dest.pptx C:\Temp\build\dest_unpacked\
python scripts/copy_slide.py C:\Temp\build\source_unpacked\ slide3.xml C:\Temp\build\dest_unpacked\ --copy-layout
# Add <p:sldId> to presentation.xml, then:
python scripts/clean.py C:\Temp\build\dest_unpacked\
python scripts/office/pack.py C:\Temp\build\dest_unpacked\ C:\Temp\output-staging.pptx --original dest.pptx
# User validates staging file in PowerPoint, then copy to final location
```

**⚠️ Corporate template decks** may show a "repair" prompt due to orphaned media in layouts/masters. This is cosmetic — no data loss. **Always pack to a local temp path first** (not OneDrive) — repair on OneDrive-synced files can take 5–10× longer. See [Known Issues](editing.md#known-issues--workarounds) in editing.md for the recommended workflow.

---

## Creating from Scratch

**Read [pptxgenjs.md](pptxgenjs.md) for full details.**

Use when no template or reference presentation is available.

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles, thick single-side borders. Carry it across every slide.
- **Determine the brand context first**: If the presentation is about Microsoft Security, use the Security brand palette and typography below. For other topics, use the generic palettes.

### Microsoft Security Brand (Feb 2026)

> **Source**: Microsoft Security brand expression 2602 + official PowerPoint template 2602. Always use the official `.potx` template when available — it has 118 pre-designed layouts across light/dark modes.

#### Security Color Palette

Use primary colors for text and backgrounds. **Reserve accent colors for minimal use** — imagery provides most of the color in Security presentations.

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| **Primary** | Black | `000000` | Primary text, dark backgrounds |
| **Primary** | Navy | `00222E` | Dark backgrounds, secondary text |
| **Primary** | White | `FFFFFF` | Light backgrounds, text on dark |
| **Primary** | Light Gray | `F2F2F2` | Light backgrounds |
| **Primary** | Dark Gray | `3D3D3D` | Secondary text |
| **Accent 1** | Blue | `1860C5` | Primary accent, buttons, links, charts |
| **Accent 2** | Light Blue | `A0E3FD` | Secondary accent, highlights, hyperlinks |
| **Accent 3** | Green | `85E89F` | Positive states, success, data viz |
| **Accent 4** | Light Green | `DFF8AD` | Light accent, data viz |
| **Accent 5** | Pink | `F2CAF7` | Accent, scan effects, emphasis |
| **Accent 6** | Yellow | `F6E162` | Accent, warnings, highlights |
| Warm | Cream | `FEFAE9` | Warm backgrounds (use with photography) |
| Warm | Sand | `D3CFBE` | Neutral backgrounds |

**Recommended color pairings** (for backgrounds + text/accents):
- Navy + Cream (`00222E` + `FEFAE9`) — warm, editorial feel
- Pink + Blue (`F2CAF7` + `1860C5`) — vibrant, modern
- Black + Light Blue (`000000` + `A0E3FD`) — high contrast, technical

#### Security Typography

| Element | Font | Size | Notes |
|---------|------|------|-------|
| Headlines | Segoe Sans Display Semilight | 36-44pt | Always set leading to 100% |
| Subheads | Segoe Sans Display Semibold | 20-24pt | |
| Body text | Segoe Sans Display Semilight | 20pt (main), 16pt (third level) | |
| Captions | Segoe Sans Display Semilight | 10-12pt | |

> ⚠️ The Feb 2026 brand uses **Segoe Sans Display** (not the older Segoe UI family). If `Segoe Sans Display` is not available, fall back to `Segoe UI` with the same weights.

#### Security Visual Identity

- **Scan treatment**: Unique to Microsoft Security — modular scans and device scans represent ambient, always-on security. Square overlays on images that can contain text describing protection capabilities.
- **Scan details**: Translucent boxes with exaggerated inner glow on 2 edges + 1px baseline stroke. Used to show detected threats, stats, or status text over images.
- **Photography**: Prioritize authenticity — diverse people interacting with technology in real settings. Avoid generic stock imagery.
- **Abstract backgrounds**: Scan texture backgrounds available in multiple color combinations (blues/pink, green/yellow, yellows/light blue). Ensure text contrast meets accessibility requirements across the entire message area.

#### Security Template Layouts (official .potx, 118 layouts)

The official template provides layouts in both **light and dark** modes:

| Category | Layouts | Examples |
|----------|---------|---------|
| **Title** | 7 variants | Full photo (×2), Half photo (×2), Tech scan (×3) |
| **Content** | 10 variants | 1–5 column text, bulleted & non-bulleted, with subheads |
| **Photos** | 12 variants | Square (×3), Full bleed (×3), Filmstrip (×4), Round (×3) |
| **Special** | 10 variants | Agenda (3 color variants), Quote (4 variants), Demo, Code (×4) |
| **Section** | 4 variants | Tech scan (×3), flat color |
| **Utility** | 3 variants | Blank, Notes, Closing logo |

Use `Home > Layout` to switch between them. Prefer built-in layouts over manual placement.

### Generic Color Palettes (Non-Security Topics)

For presentations that aren't Microsoft Security branded, use these palettes as inspiration:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography (Generic)

**Choose an interesting font pairing** — don't default to Arial. Pick a header font with personality and pair it with a clean body font.

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Accessibility (Required)

- **Contrast**: Minimum 4.5:1 ratio for text. Use [Color Contrast Analyzer](https://developer.paciellogroup.com/color-contrast-checker/) to verify.
- **Alt text**: Required on all meaningful shapes, images, charts, tables. Mark purely decorative items as decorative (no alt text).
- **Layouts**: Use built-in slide layouts — they ensure correct reading order for screen readers. Avoid blank layouts with manually placed text boxes.
- **Reading order**: Screen readers read content in creation order. Check and arrange objects in the Selection Pane (`Home > Arrange > Selection Pane`).
- **Color + shape**: Use different shapes (not just color) to indicate statuses — accommodates color blindness.
- **Videos**: Must be captioned and audio described if appropriate.
- **Run the Accessibility Checker**: `File > Check for Issues > Check Accessibility` before finalizing.

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic (or use the Security palette if applicable)
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead
- **Don't overuse accent colors** — in Security decks, accents 2–6 should be minimal; let photography carry the color

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Visual QA

**⚠️ USE SUBAGENTS** — even for 2-3 slides. You've been staring at the code and will see what you expect, not what's there. Subagents have fresh eyes.

Convert slides to images (see [Converting to Images](#converting-to-images)), then use this prompt:

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /path/to/slide-01.jpg (Expected: [brief description])
2. /path/to/slide-02.jpg (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### Verification Loop

1. Generate slides → Convert to images → Inspect
2. **List issues found** (if none found, look again more critically)
3. Fix issues
4. **Re-verify affected slides** — one fix often creates another problem
5. Repeat until a full pass reveals no new issues

**Do not declare success until you've completed at least one fix-and-verify cycle.**

---

## Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

This creates `slide-01.jpg`, `slide-02.jpg`, etc.

To re-render specific slides after fixes:

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

---

## Dependencies

- `pip install "markitdown[pptx]"` - text extraction
- `pip install Pillow` - thumbnail grids
- `npm install -g pptxgenjs` - creating from scratch
- LibreOffice (`soffice`) - PDF conversion (auto-configured for sandboxed environments via `scripts/office/soffice.py`)
- Poppler (`pdftoppm`) - PDF to images
