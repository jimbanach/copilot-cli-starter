---
name: remote-github-repo
description: "Use this skill whenever the workspace is a remote GitHub repository opened via the GitHub Repositories extension (vscode-vfs:// URIs). Triggers include: file-not-found errors on vscode-vfs:// paths, needing to locate uncommitted files, converting or processing binary files (e.g., .docx, .pptx, .xlsx) that require local tools like pandoc, pushing text or binary files back to the repository, terminal commands that need access to repo files, or any file operation that fails because of the virtual filesystem boundary. Also use when agents encounter the change store, need to download files from GitHub for local processing, or need to commit output back to the repo."
---

# Remote GitHub Repository Operations

## Overview

When a repository is opened via the GitHub Repositories extension, VS Code uses a **virtual file system** (`vscode-vfs://github/<org>/<repo>`). Files are not on the local disk — they live on GitHub and are accessed through an abstraction layer.

This creates two critical boundaries:

1. **Terminal ↔ VFS boundary**: Terminal commands run on the local filesystem and cannot access `vscode-vfs://` files. Local tools (pandoc, python, etc.) need files downloaded to a local path first.
2. **VFS ↔ GitHub boundary**: The VFS reflects committed content from GitHub. Uncommitted files (in VS Code's change store) are not discoverable by standard workspace tools.

## Pre-Check (Mandatory First Step)

Before any file operation on a remote GitHub repo, ask the user:

> "Before I proceed, please commit any uncommitted files in the workspace that you want me to work with. In a remote GitHub repository, uncommitted files are not accessible through standard tools — committing them ensures I can find and process them reliably. You can do this from the Source Control panel (Ctrl+Shift+G) → stage your changes → commit."

**Why this matters:** Uncommitted files exist only in a local change store directory that is difficult to discover and unreliable to work with. Committing takes seconds and eliminates the most error-prone phase of the workflow.

## Detecting a Remote GitHub Repository

Check for these indicators:
- Workspace paths use `vscode-vfs://github/` scheme
- `workspace_info` references `vscode-vfs://github/<org>/<repo>`
- The remote indicator in the VS Code status bar shows a GitHub repository

Once detected, all file operations must follow the patterns in this skill.

## Quick Reference: File Operation Decision Tree

### Reading files

```
Is the file committed to the repo?
├── YES → Use read_file with vscode-vfs:// path
│         OR mcp_io_github_git_get_file_contents (works for text + binary)
└── NO  → Ask user to commit first (see Pre-Check above)
```

### Discovering files

```
Use list_dir with vscode-vfs:// paths to browse directories.
Use grep_search or semantic_search for content discovery.
Do NOT rely on file_search glob patterns — they resolve unreliably with vscode-vfs://.
```

### Creating or updating files

```
Is it a text file?
├── YES → Is it small (< ~1000 lines)?
│         ├── YES → Use create_file / replace_string_in_file with vscode-vfs:// path
│         └── NO  → Use GitHub API (see references/github-api-file-operations.md)
└── NO (binary) → Use GitHub API (see references/github-api-file-operations.md)
```

### Processing files with local tools (pandoc, python, etc.)

```
1. Download file to local temp directory
2. Process locally
3. Push results back via create_file (small text) or GitHub API (large/binary)
See references/github-api-file-operations.md for download + upload procedures.
```

## Key Rules

1. **Never prepend `vscode-vfs://` to local filesystem paths.** Local files (e.g., `C:\temp\file.md`, `/home/user/file.md`) use normal absolute paths.
2. **Never use terminal commands to find or modify VFS files.** Terminals run on the local filesystem only.
3. **Never copy files into the change store directory** expecting them to appear in VFS. The extension does not monitor the change store for external additions.
4. **Always use the GitHub API for binary files.** The `create_file` tool is text-only and cannot handle images, PDFs, or other binary content.
5. **Prefer `list_dir` over `file_search`** for browsing directory structures in VFS workspaces.

## Specific Workflows

- **Converting .docx to markdown**: See [references/docx-conversion-workflow.md](references/docx-conversion-workflow.md)
- **GitHub API file operations (download, upload, push)**: See [references/github-api-file-operations.md](references/github-api-file-operations.md)
