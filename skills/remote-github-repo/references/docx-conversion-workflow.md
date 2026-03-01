# DOCX-to-Markdown Conversion Workflow

Step-by-step procedure for converting Microsoft Word (.docx) files to clean Markdown in a remote GitHub repository workspace.

## Overview

Converting .docx files in a VFS workspace requires crossing the terminal/VFS boundary twice:
1. **Download** the .docx from GitHub to local disk
2. **Convert** locally using pandoc
3. **Clean up** the generated Markdown
4. **Push** the result back to the repository

## Prerequisites

- **Pandoc** installed locally (check: `pandoc --version` in terminal or `wsl pandoc --version`)
- **GitHub CLI** (`gh`) for authenticated downloads from private repos
- **WSL** (recommended on Windows for pandoc and shell tools)

## Step-by-Step Procedure

### Step 1: Pre-Check — Ensure the File is Committed

Ask the user to commit the .docx file if it hasn't been committed yet. Verify by checking with `mcp_io_github_git_get_file_contents` or `list_dir`.

### Step 2: Download the .docx to Local Disk

```bash
# In WSL
mkdir -p /tmp/docx-convert
cd /tmp/docx-convert

# Download via GitHub API (handles private repos)
gh api "repos/<owner>/<repo>/contents/<path-to-file.docx>" \
  --jq '.content' | base64 -d > input.docx
```

Or via PowerShell:
```powershell
$tempDir = "$env:TEMP\docx-convert"
New-Item -ItemType Directory -Path $tempDir -Force
gh api "repos/<owner>/<repo>/contents/<path-to-file.docx>" --jq '.content' |
  python3 -c "import sys,base64; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))" > "$tempDir\input.docx"
```

### Step 3: Convert with Pandoc

```bash
# In WSL — recommended settings
cd /tmp/docx-convert
pandoc input.docx \
  -t markdown \
  --wrap=none \
  --extract-media=./media \
  -o output.md
```

Key pandoc options:
- `--wrap=none` — prevents hard line wraps that break markdown readability
- `--extract-media=./media` — extracts embedded images to a `media/` subdirectory
- `-t markdown` — standard markdown output (alternatives: `gfm` for GitHub-flavored)

### Step 4: Clean Up the Markdown

Pandoc output typically needs these fixes:

#### 4a. Convert grid tables to pipe tables
Pandoc generates grid tables by default. Convert to GFM pipe tables:
```
Grid table (pandoc default):
+-------+-------+
| Col A | Col B |
+=======+=======+
| val1  | val2  |
+-------+-------+

Pipe table (preferred):
| Col A | Col B |
|-------|-------|
| val1  | val2  |
```

#### 4b. Remove `{=html}` artifacts
Pandoc sometimes inserts `{=html}` after HTML blocks. Remove these.

#### 4c. Fix image paths
Update image references to use the correct relative path within the repository:
```markdown
<!-- Pandoc output -->
![](./media/image1.png)

<!-- Fixed for repo structure -->
![Description](media/image1.png)
```

#### 4d. Clean up heading styles
- Ensure consistent heading levels (H1 for title, H2 for sections, etc.)
- Remove any trailing `{#heading-id .class}` attributes if not needed

#### 4e. Fix escaped characters
Pandoc may over-escape characters. Common fixes:
- `\[` → `[` (when not part of a link)
- `\>` → `>` (when not part of a blockquote)
- `\_` → `_` (when not in italic context)

#### 4f. Add YAML front matter (if required by repo conventions)
```yaml
---
title: "Document Title"
description: "Brief description"
ms.date: MM/DD/YYYY
---
```

### Step 5: Push the Markdown Back to the Repo

**For small files (< ~1000 lines):**
Read the local file content and use `create_file` with the `vscode-vfs://` path.

**For large files:**
Use the GitHub Contents API. See [github-api-file-operations.md](github-api-file-operations.md) for detailed procedures.

```bash
# Example: Push via WSL + gh CLI
cd /tmp/docx-convert
base64 -w 0 output.md > encoded.txt
cat <<EOF > payload.json
{
  "message": "Add converted markdown: <filename>",
  "content": "$(cat encoded.txt)",
  "branch": "main"
}
EOF
gh api --method PUT "repos/<owner>/<repo>/contents/<target-path>.md" \
  --input payload.json
```

### Step 6: Push Extracted Images

If pandoc extracted images, push them as binary files:

```bash
# Push each image via GitHub API
for img in /tmp/docx-convert/media/*; do
  filename=$(basename "$img")
  base64 -w 0 "$img" > /tmp/encoded_img.txt
  cat <<EOF > /tmp/img_payload.json
{
  "message": "Add image: $filename",
  "content": "$(cat /tmp/encoded_img.txt)",
  "branch": "main"
}
EOF
  gh api --method PUT \
    "repos/<owner>/<repo>/contents/<target-dir>/media/$filename" \
    --input /tmp/img_payload.json
done
```

Or use `mcp_io_github_git_push_files` to batch all images in a single commit (preferred).

## Quality Checklist

After conversion, verify:

- [ ] All headings render correctly (no stray `#` or broken hierarchy)
- [ ] Tables are valid pipe tables with headers and separator rows
- [ ] Images render (paths correct, files pushed)
- [ ] No `{=html}` or other pandoc artifacts remain
- [ ] No broken links or cross-references
- [ ] Code blocks use correct language identifiers
- [ ] YAML front matter present (if required by repo)
- [ ] Document reads naturally without pandoc formatting quirks

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Pandoc not found | Not installed in terminal env | Install via `sudo apt install pandoc` (WSL) or `winget install pandoc` |
| Empty output.md | Corrupted download | Re-download with binary mode; verify file size |
| Missing images | `--extract-media` not specified | Re-run pandoc with `--extract-media=./media` |
| Tables garbled | Complex/nested tables in source | Manually reformat; grid→pipe conversion may need hand-editing |
| Large file push fails | GitHub Contents API 100MB limit | Split into smaller commits or use Git LFS |
| Image paths broken | Relative path mismatch | Ensure media/ directory is at the correct level relative to the .md file |
