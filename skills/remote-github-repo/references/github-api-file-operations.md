# GitHub API File Operations

Detailed procedures for downloading files from and pushing files to a remote GitHub repository when working in a VFS workspace.

## Prerequisites

- **GitHub CLI (`gh`)** — available on the local system (check with `Get-Command gh` in PowerShell)
- **GitHub MCP tools** — `mcp_io_github_git_*` tools available in the agent toolset
- **Repository info** — org/owner and repo name extracted from the VFS path: `vscode-vfs://github/<owner>/<repo>`

## Downloading Files to Local Disk

### Text files

**Option A: GitHub MCP tool** (preferred for small text files)
```
Use mcp_io_github_git_get_file_contents
  owner: "<owner>"
  repo: "<repo>"
  path: "<path-within-repo>"
```
Then write the content to a local temp file using terminal commands.

**Option B: GitHub CLI** (preferred for any size)
```powershell
# Create temp directory
$tempDir = "$env:TEMP\gh-repo-files"
New-Item -ItemType Directory -Path $tempDir -Force

# Download via gh api
gh api "repos/<owner>/<repo>/contents/<path>" --jq '.content' |
  python3 -c "import sys,base64; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))" |
  Set-Content -Path "$tempDir\<filename>" -Encoding UTF8
```

**Option C: WSL + curl** (if gh is unavailable)
```bash
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>" -o /tmp/<filename>
```

### Binary files (images, docx, pptx, etc.)

**Option A: GitHub CLI**
```powershell
gh api "repos/<owner>/<repo>/contents/<path>" --jq '.content' |
  python3 -c "import sys,base64; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))" > "$tempDir\<filename>"
```

**Option B: WSL + wget/curl**
```bash
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>" -o /tmp/<filename>
```

> **Note:** For private repos, use `gh api` which handles authentication automatically. Raw URLs require a token for private repos.

## Pushing Files to the Repository

### Small text files (< ~1000 lines)

Use `create_file` with the full `vscode-vfs://` path:
```
create_file(
  filePath: "vscode-vfs://github/<owner>/<repo>/<path>",
  content: "<file content>"
)
```

This is the simplest method and creates the file as an uncommitted change in the VFS workspace. The user can then commit it from Source Control.

### Large text files

When the file content is too large to pass as a single tool parameter, use the GitHub Contents API:

**Option A: GitHub MCP tool** (preferred)
```
Use mcp_io_github_git_create_or_update_file
  owner: "<owner>"
  repo: "<repo>"
  path: "<path-within-repo>"
  content: "<file content>"
  message: "Add <filename>"
  branch: "main"
```

**Option B: GitHub CLI with base64 encoding**
```powershell
# Encode the local file
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$tempDir\<filename>"))

# Push via GitHub Contents API
$body = @{
  message = "Add <filename>"
  content = $base64
  branch = "main"
} | ConvertTo-Json

gh api --method PUT "repos/<owner>/<repo>/contents/<path>" --input - <<< $body
```

**Option C: WSL with gh CLI** (for very large files)
```bash
cd /tmp
base64 -w 0 <filename> > encoded.txt
cat <<EOF > payload.json
{
  "message": "Add <filename>",
  "content": "$(cat encoded.txt)",
  "branch": "main"
}
EOF
gh api --method PUT "repos/<owner>/<repo>/contents/<path>" --input payload.json
```

### Binary files (images, PDFs, compiled assets)

Binary files **must** use the GitHub API — `create_file` is text-only.

**Option A: GitHub MCP push_files** (preferred for multiple files)
```
Use mcp_io_github_git_push_files
  owner: "<owner>"
  repo: "<repo>"
  branch: "main"
  message: "Add binary files"
  files: [
    { "path": "<path>", "content": "<base64-encoded-content>" }
  ]
```

**Option B: GitHub CLI** (same as large text files above, but with binary source)
```powershell
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$tempDir\image.png"))
# Then use gh api --method PUT as shown above
```

## Updating Existing Files

When updating a file that already exists in the repo, the GitHub Contents API requires the current file's SHA:

```powershell
# Get current SHA
$sha = gh api "repos/<owner>/<repo>/contents/<path>" --jq '.sha'

# Update with SHA
$body = @{
  message = "Update <filename>"
  content = $base64
  sha = $sha
  branch = "main"
} | ConvertTo-Json

gh api --method PUT "repos/<owner>/<repo>/contents/<path>" --input - <<< $body
```

Or use the MCP tool which handles this automatically:
```
Use mcp_io_github_git_create_or_update_file
  owner: "<owner>"
  repo: "<repo>"
  path: "<path>"
  content: "<new content>"
  message: "Update <filename>"
  branch: "main"
  sha: "<current sha>"
```

## Batch Operations

For pushing multiple files in a single commit, use `mcp_io_github_git_push_files`:
```
Use mcp_io_github_git_push_files
  owner: "<owner>"
  repo: "<repo>"
  branch: "main"
  message: "Add converted files and images"
  files: [
    { "path": "docs/guide.md", "content": "<text content or base64>" },
    { "path": "docs/media/image1.png", "content": "<base64>" },
    { "path": "docs/media/image2.png", "content": "<base64>" }
  ]
```

This is the most efficient method when you have multiple files to commit at once (e.g., a converted markdown file plus its extracted images).

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `create_file` fails silently | File too large for tool parameter | Use GitHub API instead |
| File not found after `create_file` | File is uncommitted in VFS | Ask user to check Source Control panel |
| Binary file appears corrupted | Used text mode instead of binary | Ensure base64 encoding for binary push |
| 404 on `gh api` for file contents | File not committed / wrong path | Verify path; ask user to commit |
| 409 conflict on PUT | SHA mismatch (file was updated) | Re-fetch current SHA and retry |
| `file_search` returns no results | Glob patterns unreliable on VFS | Use `list_dir` + `grep_search` instead |
